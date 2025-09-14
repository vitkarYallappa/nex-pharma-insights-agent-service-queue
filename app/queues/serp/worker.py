from typing import Dict, Any, List
from datetime import datetime
import asyncio

from app.queues.base_worker import BaseWorker
from app.database.s3_client import s3_client
from app.utils.logger import get_logger
from .processor import SerpProcessor

logger = get_logger(__name__)


class SerpWorker(BaseWorker):
    """Worker for processing SERP (Search Engine Results Page) queue"""
    
    def __init__(self):
        super().__init__("serp")
        self.processor = SerpProcessor()
    
    def process_item(self, item: Dict[str, Any]) -> bool:
        """Process a SERP item - simplified workflow without API calls"""
        try:

            payload = item.get('payload', {})
            
            # Extract basic information from payload
            keywords = payload.get('keywords', [])
            source = payload.get('source', {})
            search_queries = payload.get('search_queries', [])
            
            if not keywords or not source:
                logger.error("No keywords or source found in payload")
                return False
            
            source_name = source.get('name', 'Unknown')
            logger.info(f" ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::"
                        f"Processing SERP for source: {source_name} with {len(keywords)} keywords"
                        f"::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
            logger.info(f"Processing SERP for source: {source_name} with {len(keywords)} keywords")
            
            # Use real SERP API to get search results
            search_results = self._get_real_search_results(keywords, source)
            
            # Skip entire flow if no search results found
            if not search_results:
                logger.warning(f"No search results found for source: {source_name}, skipping processing")
                return True  # Return True to mark as completed (not failed)
            
            # Extract project and request IDs
            project_id, request_id = self._extract_ids_from_pk(item.get('PK', ''))
            
            if not project_id or not request_id:
                logger.error(f"Could not extract project/request IDs from PK: {item.get('PK')}")
                return False
            
            # Store search results in S3
            s3_key = s3_client.store_serp_data(project_id, request_id, {
                'source': source,
                'search_results': search_results,
                'keywords': keywords,
                'search_queries': search_queries,
                'processed_at': datetime.utcnow().isoformat(),
                'total_results': len(search_results)
            })
            
            if not s3_key:
                logger.error(f"Failed to store SERP data in S3 for source: {source_name}")
                return False
            
            # Update payload with results
            updated_payload = payload.copy()
            updated_payload.update({
                'search_results': search_results,
                's3_data_key': s3_key,
                'processed_at': datetime.utcnow().isoformat(),
                'total_results': len(search_results),
                'urls_found': [result.get('url') for result in search_results if result.get('url')]
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
                logger.info(f"Successfully processed SERP for {source_name}, found {len(search_results)} results")
                
                # Create updated item for _trigger_next_queues with the new payload
                updated_item = item.copy()
                updated_item['payload'] = updated_payload
                
                # Manually trigger next queues with updated item
                self._trigger_next_queues(updated_item)
                
                return True
            else:
                logger.error(f"Failed to update SERP payload for {source_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing SERP item: {str(e)}")
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
            else:
                # Handle failure
                self._handle_processing_failure(item)
                
        except Exception as e:
            logger.error(f"Error processing item {pk}: {str(e)}")
            self._handle_processing_error(item, str(e))
    
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for next queue - NOT USED since we override _trigger_next_queues"""
        # This method won't be used since we override _trigger_next_queues
        return {}
    
    def _trigger_next_queues(self, completed_item: Dict[str, Any]):
        """Override to create multiple Perplexity items - one for each URL (with limit)"""
        from app.models.queue_models import QueueItemFactory
        from app.database.dynamodb_client import dynamodb_client
        from config import QUEUE_TABLES, QUEUE_WORKFLOW, QUEUE_PROCESSING_LIMITS
        
        logger.info(f"DEBUG: _trigger_next_queues called with item keys: {list(completed_item.keys())}")
        
        next_queues = QUEUE_WORKFLOW.get(self.queue_name, [])
        
        if not next_queues or 'perplexity' not in next_queues:
            logger.debug(f"No perplexity queue for {self.queue_name}")
            return
        
        project_id, request_id = self._extract_ids_from_pk(completed_item.get('PK', ''))
        
        if not project_id or not request_id:
            logger.error(f"Could not extract project/request IDs from PK: {completed_item.get('PK')}")
            return
        
        payload = completed_item.get('payload', {})
        logger.info(f"DEBUG: Payload keys: {list(payload.keys())}")
        
        search_results = payload.get('search_results', [])
        source = payload.get('source', {})
        keywords = payload.get('keywords', [])
        
        logger.info(f"DEBUG: Found {len(search_results)} search results, source: {source.get('name', 'Unknown')}, keywords: {len(keywords)}")

        # Get URLs from search results
        urls_with_data = []
        for result in search_results:
            url = result.get('url')
            if url:
                urls_with_data.append({
                    'url': url,
                    'title': result.get('title', ''),
                    'snippet': result.get('snippet', ''),
                    'source': result.get('source', source.get('name', '')),
                    'relevance_score': result.get('relevance_score', 0.5),
                    'position': result.get('position', 999)  # Lower position = better ranking
                })
        
        if not urls_with_data:
            logger.warning("No URLs found in search results, skipping Perplexity queue creation")
            logger.info(f"DEBUG: Search results structure: {search_results[:2] if search_results else 'Empty'}")
            return
        
        # Apply URL limit from configuration
        max_urls = 3
        
        if len(urls_with_data) > max_urls:
            logger.info(f"Found {len(urls_with_data)} URLs, limiting to top {max_urls} for Perplexity processing")
            # Select best URLs using smart selection logic
            selected_urls = self._select_best_urls(urls_with_data, max_urls)
        else:
            selected_urls = urls_with_data
        
        logger.info(f"Creating {len(selected_urls)} Perplexity queue items (limit: {max_urls})")
        
        # Create one Perplexity queue item for each selected URL
        for i, url_data in enumerate(selected_urls):
            try:
                # Create user prompt for this specific URL
                user_prompt = self._create_url_analysis_prompt(url_data, keywords, source)
                
                # Create payload for this URL
                perplexity_payload = {
                    'user_prompt': user_prompt,
                    'analysis_prompt': user_prompt,  # Backward compatibility
                    'url_data': url_data,
                    'source_info': {
                        'name': source.get('name', ''),
                        'type': source.get('type', ''),
                        'keywords': keywords
                    },
                    'url_index': i + 1,
                    'total_urls': len(selected_urls),
                    'total_found_urls': len(urls_with_data),  # Track how many were originally found
                    'url_limit_applied': len(urls_with_data) > max_urls
                }
                
                # Create queue item
                queue_item = QueueItemFactory.create_queue_item(
                    queue_name="perplexity",
                    project_id=project_id,
                    project_request_id=request_id,
                    priority=completed_item.get('priority', 'medium'),
                    processing_strategy=completed_item.get('processing_strategy', 'table'),
                    payload=perplexity_payload,
                    metadata={
                        **completed_item.get('metadata', {}),
                        'source_name': source.get('name', ''),
                        'url': url_data['url'],
                        'url_index': i + 1,
                        'total_urls': len(selected_urls),
                        'total_found_urls': len(urls_with_data),
                        'relevance_score': url_data.get('relevance_score', 0.5),
                        'created_from': 'serp'
                    }
                )
                
                # Store in DynamoDB
                table_name = QUEUE_TABLES["perplexity"]
                success = dynamodb_client.put_item(table_name, queue_item.dict())
                
                if success:
                    logger.info(f"Created Perplexity queue item {i+1}/{len(selected_urls)} for URL: {url_data['url'][:50]}... (score: {url_data.get('relevance_score', 0.5):.2f})")
                else:
                    logger.error(f"Failed to create Perplexity queue item {i+1}/{len(selected_urls)}")

            except Exception as e:
                logger.error(f"Failed to create Perplexity item {i+1}/{len(selected_urls)}: {str(e)}")
        
        logger.info(f"Completed creating {len(selected_urls)} Perplexity queue items (found {len(urls_with_data)} total URLs)")
    
    def _create_url_analysis_prompt(self, url_data: Dict[str, Any], keywords: List[str], source: Dict[str, Any]) -> str:
        """Create analysis prompt for a specific URL using simplified prompt system"""
        from app.queues.perplexity.prompt_config import PromptManager
        
        # Use the simplified prompt manager
        return PromptManager.get_prompt(url_data, keywords)
    
    def _get_real_search_results(self, keywords: List[str], source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get real search results using SERP API"""
        try:
            # Run async processor in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self.processor.process_search_data(keywords, source)
            )
            
            loop.close()
            
            if result['status'] == 'success':
                return result['search_results']
            else:
                logger.error(f"SERP API processing failed: {result.get('processing_metadata', {}).get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting real search results: {str(e)}")
            return []

    def _select_best_urls(self, urls_with_data: List[Dict[str, Any]], max_urls: int) -> List[Dict[str, Any]]:
        """Select the best URLs for Perplexity processing - simple relevance-based selection"""
        
        # Sort by relevance score (highest first) and take top URLs
        sorted_urls = sorted(urls_with_data, key=lambda x: x.get('relevance_score', 0.0), reverse=True)
        selected = sorted_urls[:max_urls]
        
        logger.info(f"URL Selection Summary:")
        for i, url in enumerate(selected):
            logger.info(f"  {i+1}. Relevance: {url.get('relevance_score', 0.0):.2f} - {url['url'][:60]}...")
        
        if len(urls_with_data) > max_urls:
            logger.info(f"Skipped {len(urls_with_data) - max_urls} lower-relevance URLs")
        
        return selected
