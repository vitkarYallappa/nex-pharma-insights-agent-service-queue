from typing import Dict, Any
from datetime import datetime
import asyncio

from app.queues.base_worker import BaseWorker
from app.database.s3_client import s3_client
from app.utils.logger import get_logger
from .processor import PerplexityProcessor
from .db_operations_service import db_operations_service

logger = get_logger(__name__)


class PerplexityWorker(BaseWorker):
    """Simple Perplexity worker - processes one URL with user prompt"""
    
    def __init__(self):
        super().__init__("perplexity")
        self.processor = PerplexityProcessor()
    
    def process_item(self, item: Dict[str, Any]) -> bool:
        """Process Perplexity item - simple call with user prompt for one URL"""
        try:
            payload = item.get('payload', {})
            
            # Get user prompt from payload
            user_prompt = payload.get('analysis_prompt', '') or payload.get('user_prompt', '')
            url_data = payload.get('url_data', {})
            
            if not user_prompt:
                logger.error("No user prompt found in payload")
                return False
            
            url = url_data.get('url', 'Unknown URL')
            url_index = payload.get('url_index', 1)
            total_urls = payload.get('total_urls', 1)
            
            logger.info(f"Processing Perplexity request {url_index}/{total_urls} for URL: {url[:50]}...")
            
            # Call Perplexity with user prompt
            perplexity_result = self._call_perplexity(user_prompt, payload)
            
            if not perplexity_result:
                logger.error(f"Failed to get response from Perplexity for URL {url_index}/{total_urls}")
                return False
            
            # Extract project and request IDs
            project_id, request_id = self._extract_ids_from_pk(item.get('PK', ''))
            
            if not project_id or not request_id:
                logger.error(f"Could not extract project/request IDs from PK: {item.get('PK')}")
                return False
            
            # Store Perplexity response in S3
            s3_key = s3_client.store_content_data(project_id, request_id, {
                'user_prompt': user_prompt,
                'url_data': url_data,
                'perplexity_response': perplexity_result.get('perplexity_response', ''),
                'success': perplexity_result.get('success', False),
                'processed_at': datetime.utcnow().isoformat(),
                'processing_metadata': perplexity_result.get('processing_metadata', {}),
                'parsed_data': perplexity_result.get('parsed_data', {}),
                'formatted_data': perplexity_result.get('formatted_data', {}),
                'url_index': url_index,
                'total_urls': total_urls
            })
            
            if not s3_key:
                logger.error(f"Failed to store Perplexity response in S3 for URL {url_index}/{total_urls}")
                return False
            
            # Update payload with Perplexity response
            updated_payload = payload.copy()
            formatted_data = perplexity_result.get('formatted_data', {})
            updated_payload.update({
                'perplexity_response': perplexity_result.get('perplexity_response', ''),
                'perplexity_success': perplexity_result.get('success', False),
                's3_perplexity_key': s3_key,
                'processed_at': datetime.utcnow().isoformat(),
                'main_content': formatted_data.get('main_content', ''),
                'publish_date': formatted_data.get('publish_date'),
                'source_category': formatted_data.get('source_category')
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
                logger.info(f"Successfully processed Perplexity request {url_index}/{total_urls}")
                
                # Process additional table operations
                try:
                    db_data = {
                        'project_id': project_id,
                        'request_id': request_id,
                        'url_data': url_data,
                        'perplexity_response': perplexity_result.get('perplexity_response', ''),
                        'source_info': payload.get('source_info', {}),
                        'processing_metadata': perplexity_result.get('processing_metadata', {}),
                        'url_index': url_index,
                        'total_urls': total_urls,
                        'publish_date': formatted_data.get('publish_date'),
                        'source_category': formatted_data.get('source_category')
                    }
                    
                    # Call DB operations service for additional tables
                    db_results = db_operations_service.process_perplexity_completion(db_data)
                    logger.info(f"DB operations completed for {url_index}/{total_urls}: {db_results.get('processing_metadata', {}).get('status', 'unknown')}")
                    
                    # Extract content_id from DB operations result
                    content_id = db_results.get('content_id')
                    if content_id:
                        updated_payload['content_id'] = content_id
                        updated_payload['source_category'] = formatted_data.get('source_category')
                        updated_payload['publish_date'] = formatted_data.get('publish_date')
                        logger.info(f"Content ID {content_id} assigned for URL {url_index}/{total_urls}")
                    
                except Exception as db_error:
                    logger.error(f"DB operations failed for {url_index}/{total_urls}: {str(db_error)}")
                    # Don't fail the main process if DB operations fail
                
                # Create updated item for _trigger_next_queues with the new payload
                updated_item = item.copy()
                updated_item['payload'] = updated_payload
                
                # Trigger next queues manually (don't use base worker to avoid duplicates)
                self._trigger_next_queues(updated_item)
                
                return True
            else:
                logger.error(f"Failed to update Perplexity payload for URL {url_index}/{total_urls}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing Perplexity item: {str(e)}")
            return False
    
    def _process_item(self, item: Dict[str, Any]):
        """Override base worker's _process_item to handle our custom flow"""
        pk = item.get('PK')
        sk = item.get('SK')
        
        if not pk or not sk:
            logger.error(f"Invalid item keys: PK={pk}, SK={sk}")
            return
        
        try:
            # Update status to processing
            from app.models.queue_models import QueueStatus
            self._update_item_status(pk, sk, QueueStatus.PROCESSING)
            
            # Process the item (this calls our overridden process_item method)
            success = self.process_item(item)
            
            if success:
                # Update status to completed
                self._update_item_status(pk, sk, QueueStatus.COMPLETED)
                logger.info(f"Successfully processed item: {pk}")
                # Note: _trigger_next_queues is called inside process_item with updated data
                # We don't call _trigger_next_queues here to avoid duplicates
            else:
                # Handle failure
                self._handle_processing_failure(item)
                
        except Exception as e:
            logger.error(f"Error processing item {pk}: {str(e)}")
            self._handle_processing_error(item, str(e))
    
    def _trigger_next_queues(self, completed_item: Dict[str, Any]):
        """Override to create BOTH insight and implication queue items for this URL"""
        from app.models.queue_models import QueueItemFactory
        from app.database.dynamodb_client import dynamodb_client
        from config import QUEUE_TABLES
        
        logger.info(f"DEBUG: Perplexity _trigger_next_queues called with item keys: {list(completed_item.keys())}")
        
        project_id, request_id = self._extract_ids_from_pk(completed_item.get('PK', ''))
        
        if not project_id or not request_id:
            logger.error(f"Could not extract project/request IDs from PK: {completed_item.get('PK')}")
            return
        
        payload = completed_item.get('payload', {})
        logger.info(f"DEBUG: Perplexity payload keys: {list(payload.keys())}")
        
        url_data = payload.get('url_data', {})
        url_index = payload.get('url_index', 1)
        total_urls = payload.get('total_urls', 1)
        perplexity_response = payload.get('perplexity_response', '')
        
        # Create relevance_check, insight and implication queue items for this URL
        next_queues = ['relevance_check', 'insight', 'implication']
        logger.info(f"Creating relevance_check + insight + implication queue items for URL {url_index}/{total_urls}")
        
        for queue_name in next_queues:
            try:
                # Create payload for next queue
                next_payload = {
                    'perplexity_response': payload.get('perplexity_response', ''),
                    'perplexity_success': payload.get('perplexity_success', False),
                    's3_perplexity_key': payload.get('s3_perplexity_key', ''),
                    'url_data': url_data,
                    'analysis_type': 'market_insights' if queue_name == 'insight' else 'business_implications' if queue_name == 'implication' else 'relevance_check',
                    'user_prompt': payload.get('user_prompt', ''),
                    'source_info': payload.get('source_info', {}),
                    'url_index': url_index,
                    'total_urls': total_urls,
                    'content_id': payload.get('content_id', ''),  # Pass content ID to next queues
                    'main_content': payload.get('main_content', ''),
                    'publish_date': payload.get('publish_date'),
                    'source_category': payload.get('source_category')
                }

                logger.info(f"DEBUG: Creating {queue_name} item with payload keys: {list(next_payload.keys())}")

                # Create queue item
                queue_item = QueueItemFactory.create_queue_item(
                    queue_name=queue_name,
                    project_id=project_id,
                    project_request_id=request_id,
                    priority=completed_item.get('priority', 'medium'),
                    processing_strategy=completed_item.get('processing_strategy', 'table'),
                    payload=next_payload,
                    metadata={
                        **completed_item.get('metadata', {}),
                        'url': url_data.get('url', ''),
                        'url_index': url_index,
                        'total_urls': total_urls,
                        'analysis_type': next_payload['analysis_type'],
                        'created_from': 'perplexity'
                    }
                )

                # Store in DynamoDB
                table_name = QUEUE_TABLES[queue_name]
                success = dynamodb_client.put_item(table_name, queue_item.dict())

                if success:
                    logger.info(f"✅ Created {queue_name} queue item for URL {url_index}/{total_urls}")
                else:
                    logger.error(f"❌ Failed to create {queue_name} queue item for URL {url_index}/{total_urls}")

            except Exception as e:
                logger.error(f"❌ Failed to create {queue_name} item for URL {url_index}/{total_urls}: {str(e)}")

        logger.info(f"Completed creating relevance_check + insight + implication queue items for URL {url_index}/{total_urls}")
    
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare simple payload for next queue - NOT USED since we override _trigger_next_queues"""
        # This method won't be used since we override _trigger_next_queues
        return {}
    
    def _call_perplexity(self, user_prompt: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call Perplexity with user prompt"""
        try:
            # Run async processor in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self.processor.process_user_prompt(user_prompt, context_data)
            )
            
            loop.close()
            
            return result
                
        except Exception as e:
            logger.error(f"Error calling Perplexity: {str(e)}")
            return {
                'perplexity_response': f"<div><p>Error: {str(e)}</p></div>",
                'success': False,
                'status': 'error',
                'formatted_data': {
                    'main_content': f"<div><p>Error: {str(e)}</p></div>",
                    'publish_date': None,
                    'source_category': None
                },
                'parsed_data': {},
                'processing_metadata': {
                    'error': str(e),
                    'processed_at': datetime.utcnow().isoformat()
                }
            }
