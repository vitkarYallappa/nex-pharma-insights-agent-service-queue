from typing import Dict, Any
from datetime import datetime
import asyncio

from app.queues.base_worker import BaseWorker
from app.database.s3_client import s3_client
from app.utils.logger import get_logger
from .processor import RelevanceCheckProcessor
from .db_operations_service import relevance_check_db_operations_service

logger = get_logger(__name__)


class RelevanceCheckWorker(BaseWorker):
    """Worker for processing relevance checks after Perplexity summary fetch"""
    
    def __init__(self):
        super().__init__("relevance_check")
        self.processor = RelevanceCheckProcessor()
    
    async def process_item(self, item: Dict[str, Any]) -> bool:
        """Process relevance check item - analyze content relevance from Perplexity response"""
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
            
            logger.info(f"🔍 RELEVANCE CHECK - Content ID: {content_id} | URL {url_index}/{total_urls}: {url[:50]}...")
            logger.info(f"Processing relevance check for content ID: {content_id}")
            
            # Extract project and request IDs
            project_id, request_id = self._extract_ids_from_pk(item.get('PK', ''))
            
            if not project_id or not request_id:
                logger.error(f"Could not extract project/request IDs from PK: {item.get('PK')} for content ID: {content_id}")
                return False
            
            # Process relevance check using the processor (async)
            relevance_result = await self.processor.check_relevance(
                perplexity_response=perplexity_response,
                url_data=url_data,
                user_prompt=payload.get('user_prompt', ''),
                content_id=content_id,
                project_id=project_id,
                request_id=request_id
            )
            
            if not relevance_result or not relevance_result.get('success', False):
                logger.error(f"Failed to check relevance for content ID: {content_id}")
                return False
            
            # Store relevance check results in S3
            s3_key = s3_client.store_insights(project_id, request_id, {
                'content_id': content_id,
                'relevance_analysis': relevance_result.get('relevance_analysis', ''),
                'url_data': url_data,
                'processing_metadata': relevance_result.get('processing_metadata', {}),
                'processed_at': datetime.utcnow().isoformat(),
                'url_index': url_index,
                'total_urls': total_urls
            })
            
            if not s3_key:
                logger.error(f"Failed to store relevance analysis in S3 for content ID: {content_id}")
                return False
            
            # Update payload with relevance check result
            updated_payload = payload.copy()
            updated_payload.update({
                'relevance_response': relevance_result.get('relevance_analysis', ''),
                'relevance_success': relevance_result.get('success', False),
                's3_relevance_key': s3_key,
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
                logger.info(f"✅ RELEVANCE CHECK COMPLETED - Content ID: {content_id} | Successfully processed relevance check for URL {url_index}/{total_urls}")
                
                # Process additional DB operations for content_relevance table
                try:
                    db_data = {
                        'content_id': content_id,
                        'project_id': project_id,
                        'request_id': request_id,
                        'relevance_response': relevance_result.get('relevance_analysis', ''),
                        'relevance_success': relevance_result.get('success', False),
                        's3_relevance_key': s3_key,
                        'url_data': url_data,
                        'processing_metadata': relevance_result.get('processing_metadata', {}),
                        'url_index': url_index,
                        'total_urls': total_urls
                    }
                    
                    # Call DB operations service for content_relevance table
                    db_results = relevance_check_db_operations_service.process_relevance_completion(db_data)
                    
                    if db_results.get('content_relevance_result', {}).get('success'):
                        logger.info(f"✅ RELEVANCE DB SUCCESS - Content ID: {content_id} | Stored in content_relevance table")
                    else:
                        logger.error(f"❌ RELEVANCE DB FAILED - Content ID: {content_id} | Failed to store in content_relevance table")
                    
                except Exception as db_error:
                    logger.error(f"❌ RELEVANCE DB ERROR - Content ID: {content_id} | DB operations failed: {str(db_error)}")
                    # Don't fail the main process if DB operations fail
                
                return True
            else:
                logger.error(f"❌ RELEVANCE CHECK FAILED - Content ID: {content_id} | Failed to update relevance payload for URL {url_index}/{total_urls}")
                return False
                
        except Exception as e:
            content_id = item.get('payload', {}).get('content_id', 'Unknown')
            logger.error(f"❌ RELEVANCE CHECK ERROR - Content ID: {content_id} | Error processing relevance check item: {str(e)}")
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
                logger.info(f"Successfully processed relevance check item: {pk}")
            else:
                # Handle failure
                self._handle_processing_failure(item)
                
        except Exception as e:
            logger.error(f"Error processing relevance check item {pk}: {str(e)}")
            self._handle_processing_error(item, str(e))
    
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for next queue (if any)"""
        # Relevance checks can trigger further processing based on relevance score
        return {} 