import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from config import settings, QUEUE_TABLES, QUEUE_WORKFLOW, QUEUE_PROCESSING_LIMITS
from app.database.dynamodb_client import dynamodb_client
from app.database.s3_client import s3_client
from app.models.queue_models import QueueStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseWorker(ABC):
    """Base class for all queue workers"""
    
    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.table_name = QUEUE_TABLES.get(queue_name)
        self.is_running = False
        self.thread = None
        self.poll_interval = settings.queue_poll_interval
        self.batch_size = settings.queue_batch_size
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay
        self.last_heartbeat = datetime.utcnow()
        self.heartbeat_interval = 60  # Log heartbeat every 60 seconds
        
        if not self.table_name:
            raise ValueError(f"Unknown queue name: {queue_name}")
        
        logger.info(f"🔧 INITIALIZED {self.__class__.__name__} for queue: {queue_name.upper()} | Table: {self.table_name}")
    
    def start_polling(self):
        """Start the worker polling loop"""
        self.is_running = True
        logger.info(f"🔄 STARTING POLLING LOOP for {self.queue_name.upper()} queue | Poll interval: {self.poll_interval}s | Batch size: {self.batch_size}")
        
        while self.is_running:
            try:
                # Get pending items from queue
                pending_items = self._get_pending_items()
                
                if pending_items:
                    logger.info(f"📦 PROCESSING {len(pending_items)} items from {self.queue_name.upper()} queue")
                    
                    for item in pending_items:
                        if not self.is_running:
                            break
                        
                        try:
                            # Add configurable delay before processing each task
                            task_delay = QUEUE_PROCESSING_LIMITS.get('task_delay_seconds', 3)
                            if task_delay > 0:
                                logger.info(f"⏳ Waiting {task_delay} seconds before processing item {item.get('PK', 'unknown')}")
                                time.sleep(task_delay)
                            
                            self._process_item(item)
                        except Exception as e:
                            logger.error(f"Error processing item {item.get('PK', 'unknown')}: {str(e)}")
                            self._handle_processing_error(item, str(e))
                else:
                    # Log heartbeat periodically when no items to process
                    now = datetime.utcnow()
                    if (now - self.last_heartbeat).total_seconds() >= self.heartbeat_interval:
                        logger.info(f"💓 {self.queue_name.upper()} QUEUE HEARTBEAT - Worker running, no pending tasks")
                        self.last_heartbeat = now
                
                # Sleep before next poll
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in worker polling loop for {self.queue_name}: {str(e)}")
                time.sleep(self.poll_interval)
    
    def stop_polling(self):
        """Stop the worker polling loop"""
        logger.info(f"Stopping worker for queue: {self.queue_name}")
        self.is_running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
    
    def start_worker_thread(self):
        """Start worker in a separate thread"""
        if self.thread and self.thread.is_alive():
            logger.warning(f"Worker thread for {self.queue_name} is already running")
            return
        
        self.thread = threading.Thread(target=self.start_polling, daemon=True)
        self.thread.start()
        logger.info(f"🧵 WORKER THREAD STARTED for {self.queue_name.upper()} queue - Thread ID: {self.thread.ident}")
    
    def _get_pending_items(self) -> List[Dict[str, Any]]:
        """Get pending items from the queue"""
        try:
            items = dynamodb_client.scan_items(
                table_name=self.table_name,
                filter_expression='#status = :status',
                expression_attribute_values={':status': QueueStatus.PENDING.value},
                expression_attribute_names={'#status': 'status'},
                limit=self.batch_size
            )
            return items
        except Exception as e:
            logger.error(f"Failed to get pending items from {self.queue_name}: {str(e)}")
            return []
    
    def _process_item(self, item: Dict[str, Any]):
        """Process a single queue item"""
        pk = item.get('PK')
        sk = item.get('SK')
        
        if not pk or not sk:
            logger.error(f"Invalid item keys: PK={pk}, SK={sk}")
            return
        
        try:
            # Update status to processing
            self._update_item_status(pk, sk, QueueStatus.PROCESSING)
            
            # Process the item
            success = self.process_item(item)
            
            if success:
                # Update status to completed
                self._update_item_status(pk, sk, QueueStatus.COMPLETED)
                
                # Trigger next queues in workflow
                self._trigger_next_queues(item)
                
                logger.info(f"Successfully processed item: {pk}")
            else:
                # Handle failure
                self._handle_processing_failure(item)
                
        except Exception as e:
            logger.error(f"Error processing item {pk}: {str(e)}")
            self._handle_processing_error(item, str(e))
    
    def _update_item_status(self, pk: str, sk: str, status: QueueStatus, 
                           error_message: Optional[str] = None):
        """Update the status of a queue item"""
        try:
            dynamodb_client.update_item_status(
                table_name=self.table_name,
                pk=pk,
                sk=sk,
                new_status=status.value,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to update item status: {str(e)}")
    
    def _handle_processing_failure(self, item: Dict[str, Any]):
        """Handle processing failure with retry logic"""
        pk = item.get('PK')
        sk = item.get('SK')
        retry_count = item.get('retry_count', 0)
        
        if retry_count < self.max_retries:
            # Increment retry count and set to retry status
            new_retry_count = retry_count + 1
            
            try:
                dynamodb_client.update_item(
                    table_name=self.table_name,
                    key={'PK': pk, 'SK': sk},
                    update_expression="SET retry_count = :retry_count, #status = :status, updated_at = :updated_at",
                    expression_attribute_values={
                        ':retry_count': new_retry_count,
                        ':status': QueueStatus.RETRY.value,
                        ':updated_at': datetime.utcnow().isoformat()
                    }
                )
                
                logger.warning(f"Item {pk} failed, scheduled for retry ({new_retry_count}/{self.max_retries})")
                
            except Exception as e:
                logger.error(f"Failed to update retry count for {pk}: {str(e)}")
        else:
            # Max retries reached, mark as failed
            self._update_item_status(pk, sk, QueueStatus.FAILED, "Max retries exceeded")
            logger.error(f"Item {pk} failed permanently after {self.max_retries} retries")
    
    def _handle_processing_error(self, item: Dict[str, Any], error_message: str):
        """Handle processing error"""
        pk = item.get('PK')
        sk = item.get('SK')
        
        self._update_item_status(pk, sk, QueueStatus.FAILED, error_message)
        logger.error(f"Item {pk} failed with error: {error_message}")
    
    def _trigger_next_queues(self, completed_item: Dict[str, Any]):
        """Trigger next queues in the workflow"""
        next_queues = QUEUE_WORKFLOW.get(self.queue_name, [])
        
        if not next_queues:
            logger.debug(f"No next queues for {self.queue_name}")
            return
        
        project_id, request_id = self._extract_ids_from_pk(completed_item.get('PK', ''))
        
        if not project_id or not request_id:
            logger.error(f"Could not extract project/request IDs from PK: {completed_item.get('PK')}")
            return
        
        for next_queue in next_queues:
            try:
                self._create_next_queue_item(next_queue, project_id, request_id, completed_item)
                logger.info(f"Triggered next queue: {next_queue}")
            except Exception as e:
                logger.error(f"Failed to trigger next queue {next_queue}: {str(e)}")
    
    def _extract_ids_from_pk(self, pk: str) -> tuple:
        """Extract project_id and request_id from partition key"""
        try:
            parts = pk.split('#')
            if len(parts) == 2:
                return parts[0], parts[1]
        except Exception:
            pass
        return None, None
    
    def _create_next_queue_item(self, next_queue: str, project_id: str, 
                               request_id: str, completed_item: Dict[str, Any]):
        """Create item in next queue"""
        from app.models.queue_models import QueueItemFactory
        
        # Create payload for next queue based on completed item
        next_payload = self.prepare_next_queue_payload(next_queue, completed_item)
        
        # Create queue item
        queue_item = QueueItemFactory.create_queue_item(
            queue_name=next_queue,
            project_id=project_id,
            project_request_id=request_id,
            priority=completed_item.get('priority', 'medium'),
            processing_strategy=completed_item.get('processing_strategy', 'table'),
            payload=next_payload,
            metadata=completed_item.get('metadata', {})
        )
        
        # Convert to dict and store in DynamoDB
        item_dict = queue_item.dict()
        next_table_name = QUEUE_TABLES[next_queue]
        
        success = dynamodb_client.put_item(next_table_name, item_dict)
        
        if not success:
            raise Exception(f"Failed to create item in {next_queue}")
    
    @abstractmethod
    def process_item(self, item: Dict[str, Any]) -> bool:
        """
        Process a single queue item.
        
        Args:
            item: The queue item to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare payload for the next queue based on completed item.
        
        Args:
            next_queue: Name of the next queue
            completed_item: The completed queue item
            
        Returns:
            Dict[str, Any]: Payload for the next queue
        """
        pass
    
    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get metrics for this queue"""
        try:
            # Count items by status
            pending = len(dynamodb_client.get_queue_items_by_status(self.table_name, QueueStatus.PENDING.value))
            processing = len(dynamodb_client.get_queue_items_by_status(self.table_name, QueueStatus.PROCESSING.value))
            completed = len(dynamodb_client.get_queue_items_by_status(self.table_name, QueueStatus.COMPLETED.value))
            failed = len(dynamodb_client.get_queue_items_by_status(self.table_name, QueueStatus.FAILED.value))
            retry = len(dynamodb_client.get_queue_items_by_status(self.table_name, QueueStatus.RETRY.value))
            
            total = pending + processing + completed + failed + retry
            success_rate = (completed / total * 100) if total > 0 else 0
            
            return {
                'queue_name': self.queue_name,
                'pending': pending,
                'processing': processing,
                'completed': completed,
                'failed': failed,
                'retry': retry,
                'total': total,
                'success_rate': round(success_rate, 2),
                'is_running': self.is_running
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics for {self.queue_name}: {str(e)}")
            return {
                'queue_name': self.queue_name,
                'error': str(e),
                'is_running': self.is_running
            }
