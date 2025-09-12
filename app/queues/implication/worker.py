from typing import Dict, Any
from datetime import datetime
import asyncio

from app.queues.base_worker import BaseWorker
from app.database.s3_client import s3_client
from app.utils.logger import get_logger
from .processor import ImplicationProcessor
from .db_operations_service import ImplicationDBOperationsService

logger = get_logger(__name__)


class ImplicationWorker(BaseWorker):
    """Worker for processing implication generation from Perplexity data"""
    
    def __init__(self):
        super().__init__("implication")
        self.processor = ImplicationProcessor()
        self.implication_db_operations_service = ImplicationDBOperationsService()
    
    async def process_item(self, item: Dict[str, Any]) -> bool:
        """Process implication item - generate strategic implications from Perplexity response"""
        try:
            payload = item.get('payload', {})
            
            # Extract key information
            content_id = payload.get('content_id', 'Unknown')
            perplexity_response = payload.get('perplexity_response', '')
            url_data = payload.get('url_data', {})
            url_index = payload.get('url_index', 1)
            total_urls = payload.get('total_urls', 1)
            
            if not perplexity_response:
                logger.error(f"No Perplexity response found in payload for content ID: {content_id}")
                return False
            
            url = url_data.get('url', 'Unknown URL')
            
            logger.info(f"🔍 IMPLICATION PROCESSING - Content ID: {content_id} | URL {url_index}/{total_urls}: {url[:50]}...")
            logger.info(f"Processing strategic implications for content ID: {content_id}")
            
            # Extract project and request IDs
            project_id, request_id = self._extract_ids_from_pk(item.get('PK', ''))
            
            if not project_id or not request_id:
                logger.error(f"Could not extract project/request IDs from PK: {item.get('PK')} for content ID: {content_id}")
                return False
            
            # Process implications using the processor (async)
            implication_result = await self.processor.generate_implications(
                content=perplexity_response,
                content_id=content_id,
                metadata={
                    'url_data': url_data,
                    'user_prompt': payload.get('user_prompt', ''),
                    'url_index': url_index,
                    'total_urls': total_urls
                }
            )
            
            if not implication_result or not implication_result.get('success', False):
                logger.error(f"Failed to generate implications for content ID: {content_id}")
                return False
            
            # Store implications in S3
            s3_key = s3_client.store_implications(project_id, request_id, {
                'content_id': content_id,
                'implications': implication_result.get('content', ''),
                'url_data': url_data,
                'processing_metadata': implication_result.get('processing_metadata', {}),
                'processed_at': datetime.utcnow().isoformat(),
                'url_index': url_index,
                'total_urls': total_urls
            })
            
            if not s3_key:
                logger.error(f"Failed to store implications in S3 for content ID: {content_id}")
                return False
            
            # Update payload with implications result
            updated_payload = payload.copy()
            updated_payload.update({
                'implications_response': implication_result.get('content', ''),
                'implications_success': implication_result.get('success', False),
                's3_implications_key': s3_key,
                'processed_at': datetime.utcnow().isoformat()
            })
            
            # Update the item in DynamoDB
            from app.database.dynamodb_client import dynamodb_client
            
            success = dynamodb_client.update_item(
                table_name=self.table_name,
                key={'PK': item['PK'], 'SK': item['SK']},
                update_expression="SET payload = :payload, updated_at = :updated_at",
                expression_attribute_values={
                    ':payload': updated_payload,
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
            
            if success:
                logger.info(f"✅ IMPLICATION COMPLETED - Content ID: {content_id} | Successfully processed implications for URL {url_index}/{total_urls}")
                
                # Process additional DB operations for content_implication table
                try:
                    db_result = await self.implication_db_operations_service.process_implication_completion(
                        content_id=content_id,
                        implication_result=implication_result,
                        original_metadata={
                            'project_id': project_id,
                            'request_id': request_id,
                            'url_data': url_data,
                            'url_index': url_index,
                            'total_urls': total_urls
                        }
                    )
                    
                    if db_result.get('success'):
                        logger.info(f"✅ IMPLICATION DB SUCCESS - Content ID: {content_id} | Stored in content_implication table")
                    else:
                        logger.error(f"❌ IMPLICATION DB FAILED - Content ID: {content_id} | Failed to store in content_implication table")
                    
                except Exception as db_error:
                    logger.error(f"❌ IMPLICATION DB ERROR - Content ID: {content_id} | DB operations failed: {str(db_error)}")
                    # Don't fail the main process if DB operations fail
                
                return True
            else:
                logger.error(f"❌ IMPLICATION FAILED - Content ID: {content_id} | Failed to update implications payload for URL {url_index}/{total_urls}")
                return False
                
        except Exception as e:
            content_id = item.get('payload', {}).get('content_id', 'Unknown')
            logger.error(f"❌ IMPLICATION ERROR - Content ID: {content_id} | Error processing implication item: {str(e)}")
            return False
    
    def _process_item(self, item: Dict[str, Any]):
        """Override base worker's _process_item to handle async processing"""
        pk = item.get('PK')
        sk = item.get('SK')
        
        if not pk or not sk:
            logger.error(f"Invalid item keys: PK={pk}, SK={sk}")
            return
        
        try:
            # Update status to processing
            from app.models.queue_models import QueueStatus
            self._update_item_status(pk, sk, QueueStatus.PROCESSING)
            
            # Process the item asynchronously
            success = asyncio.run(self.process_item(item))
            
            if success:
                # Update status to completed
                self._update_item_status(pk, sk, QueueStatus.COMPLETED)
                logger.info(f"Successfully processed implication item: {pk}")
            else:
                # Handle failure
                self._handle_processing_failure(item)
                
        except Exception as e:
            logger.error(f"Error processing implication item {pk}: {str(e)}")
            self._handle_processing_error(item, str(e))
    
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for next queue (if any)"""
        # Implications are typically final, but can be extended if needed
        return {}
