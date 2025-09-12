from typing import Dict, Any
from datetime import datetime
import asyncio

from app.queues.base_worker import BaseWorker
from app.database.s3_client import s3_client
from app.utils.logger import get_logger
from .processor import InsightProcessor
from .db_operations_service import insight_db_operations_service

logger = get_logger(__name__)


class InsightWorker(BaseWorker):
    """Worker for processing insight generation from Perplexity data"""
    
    def __init__(self):
        super().__init__("insight")
        self.processor = InsightProcessor()
    
    async def process_item(self, item: Dict[str, Any]) -> bool:
        """Process insight item - generate market insights from Perplexity response"""
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
            
            logger.info(f"🔍 INSIGHT PROCESSING - Content ID: {content_id} | URL {url_index}/{total_urls}: {url[:50]}...")
            logger.info(f"Processing market insights for content ID: {content_id}")
            
            # Extract project and request IDs
            project_id, request_id = self._extract_ids_from_pk(item.get('PK', ''))
            
            if not project_id or not request_id:
                logger.error(f"Could not extract project/request IDs from PK: {item.get('PK')} for content ID: {content_id}")
                return False
            
            # Process insights using the processor (async)
            insight_result = await self.processor.generate_insights(
                perplexity_response=perplexity_response,
                url_data=url_data,
                user_prompt=payload.get('user_prompt', ''),
                content_id=content_id
            )
            
            if not insight_result or not insight_result.get('success', False):
                logger.error(f"Failed to generate insights for content ID: {content_id}")
                return False
            
            # Store insights in S3
            s3_key = s3_client.store_insights(project_id, request_id, {
                'content_id': content_id,
                'insights': insight_result.get('insights', ''),
                'url_data': url_data,
                'processing_metadata': insight_result.get('processing_metadata', {}),
                'processed_at': datetime.utcnow().isoformat(),
                'url_index': url_index,
                'total_urls': total_urls
            })
            
            if not s3_key:
                logger.error(f"Failed to store insights in S3 for content ID: {content_id}")
                return False
            
            # Update payload with insights result
            updated_payload = payload.copy()
            updated_payload.update({
                'insights_response': insight_result.get('insights', ''),
                'insights_success': insight_result.get('success', False),
                's3_insights_key': s3_key,
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
                logger.info(f"✅ INSIGHT COMPLETED - Content ID: {content_id} | Successfully processed insights for URL {url_index}/{total_urls}")
                
                # Process additional DB operations for content_insight table
                try:
                    db_data = {
                        'content_id': content_id,
                        'project_id': project_id,
                        'request_id': request_id,
                        'insights_response': insight_result.get('insights', ''),
                        'insights_success': insight_result.get('success', False),
                        's3_insights_key': s3_key,
                        'url_data': url_data,
                        'processing_metadata': insight_result.get('processing_metadata', {}),
                        'url_index': url_index,
                        'total_urls': total_urls
                    }
                    
                    # Call DB operations service for content_insight table
                    db_results = insight_db_operations_service.process_insight_completion(db_data)
                    
                    if db_results.get('content_insight_result', {}).get('success'):
                        logger.info(f"✅ INSIGHT DB SUCCESS - Content ID: {content_id} | Stored in content_insight table")
                    else:
                        logger.error(f"❌ INSIGHT DB FAILED - Content ID: {content_id} | Failed to store in content_insight table")
                    
                except Exception as db_error:
                    logger.error(f"❌ INSIGHT DB ERROR - Content ID: {content_id} | DB operations failed: {str(db_error)}")
                    # Don't fail the main process if DB operations fail
                
                return True
            else:
                logger.error(f"❌ INSIGHT FAILED - Content ID: {content_id} | Failed to update insights payload for URL {url_index}/{total_urls}")
                return False
                
        except Exception as e:
            content_id = item.get('payload', {}).get('content_id', 'Unknown')
            logger.error(f"❌ INSIGHT ERROR - Content ID: {content_id} | Error processing insight item: {str(e)}")
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
                logger.info(f"Successfully processed insight item: {pk}")
            else:
                # Handle failure
                self._handle_processing_failure(item)
                
        except Exception as e:
            logger.error(f"Error processing insight item {pk}: {str(e)}")
            self._handle_processing_error(item, str(e))
    
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for next queue (if any)"""
        # Insights are typically final, but can be extended if needed
        return {}
