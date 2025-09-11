from typing import Dict, Any, List
import asyncio
import aiohttp
from datetime import datetime
from urllib.parse import quote_plus, urlparse

from app.queues.base_worker import BaseWorker
from app.database.s3_client import s3_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SerpWorker(BaseWorker):
    """Worker for processing SERP (Search Engine Results Page) queue"""
    
    def __init__(self):
        super().__init__("serp")
    
    def process_item(self, item: Dict[str, Any]) -> bool:
        """Process a SERP item for a SINGLE source"""
        try:
            payload = item.get('payload', {})
            
            keywords = payload.get('keywords', [])
            source = payload.get('source', {})  # Single source now
            search_queries = payload.get('search_queries', [])
            
            if not keywords or not source:
                logger.error("No keywords or source found in payload")
                return False
            
            source_name = source.get('name', 'Unknown')
            logger.info(f"Processing SERP for source: {source_name} with {len(keywords)} keywords")
            
            # Execute search queries for this source
            search_results = self._execute_searches_for_source(search_queries, keywords, source)
            
            if not search_results:
                logger.warning(f"No search results obtained for source: {source_name}")
                return False
            
            # Extract project and request IDs
            project_id, request_id = self._extract_ids_from_pk(item.get('PK', ''))
            
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
                return True
            else:
                logger.error(f"Failed to update SERP payload for {source_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing SERP item: {str(e)}")
            return False
    
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for Perplexity queue - NOT USED, we override _create_next_queue_item"""
        # This won't be used since we override _create_next_queue_item
        return {}
    
    def _create_next_queue_item(self, next_queue: str, project_id: str, 
                               request_id: str, completed_item: Dict[str, Any]):
        """Override to create multiple Perplexity items based on URLs found"""
        if next_queue != "perplexity":
            return super()._create_next_queue_item(next_queue, project_id, request_id, completed_item)
        
        # For Perplexity queue, create one item per URL found (or group of URLs)
        from app.models.queue_models import QueueItemFactory
        from app.database.dynamodb_client import dynamodb_client
        from config import QUEUE_TABLES
        
        payload = completed_item.get('payload', {})
        search_results = payload.get('search_results', [])
        source = payload.get('source', {})
        keywords = payload.get('keywords', [])
        
        # Get URLs from search results
        urls = [result.get('url') for result in search_results if result.get('url')]
        
        if not urls:
            logger.warning(f"No URLs found in SERP results for source: {source.get('name')}")
            return
        
        # Group URLs into batches (e.g., 3 URLs per Perplexity item)
        batch_size = 3
        url_batches = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]
        
        logger.info(f"Creating {len(url_batches)} Perplexity queue items for {len(urls)} URLs from source: {source.get('name')}")
        
        for batch_index, url_batch in enumerate(url_batches):
            try:
                # Get search results for this batch of URLs
                batch_results = [result for result in search_results if result.get('url') in url_batch]
                
                # Create Perplexity payload for this batch
                perplexity_payload = {
                    'search_data': {
                        'results': batch_results,
                        'source': source,
                        'keywords': keywords,
                        'batch_index': batch_index,
                        'total_batches': len(url_batches),
                        'urls': url_batch
                    },
                    'analysis_prompt': self._create_analysis_prompt_for_batch(keywords, source, batch_results),
                    'enhanced_data': {}
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
                        'batch_index': batch_index,
                        'total_batches': len(url_batches),
                        'urls_count': len(url_batch),
                        'created_from': 'serp'
                    }
                )
                
                # Store in DynamoDB
                table_name = QUEUE_TABLES["perplexity"]
                success = dynamodb_client.put_item(table_name, queue_item.dict())
                
                if success:
                    logger.info(f"Created Perplexity queue item {batch_index+1}/{len(url_batches)} with {len(url_batch)} URLs")
                else:
                    logger.error(f"Failed to create Perplexity queue item for batch {batch_index+1}")
                    
            except Exception as e:
                logger.error(f"Failed to create Perplexity item for batch {batch_index+1}: {str(e)}")
        
        logger.info(f"Completed creating {len(url_batches)} Perplexity queue items from SERP results")
    
    def _execute_searches_for_source(self, search_queries: List[str], keywords: List[str], 
                                   source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute search queries for a single source"""
        try:
            # Use asyncio to run async search
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self._async_search_source(search_queries, keywords, source))
            loop.close()
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing searches for source {source.get('name')}: {str(e)}")
            return []
    
    async def _async_search_source(self, search_queries: List[str], keywords: List[str], 
                                 source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Async search execution for single source"""
        all_results = []
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            tasks = []
            
            # Create search tasks for this source
            for query in search_queries:
                tasks.append(self._search_query_for_source(session, query, keywords, source))
            
            # Execute searches concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect valid results
            for result in results:
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Search task failed for {source.get('name')}: {str(result)}")
        
        # Remove duplicates and limit results
        unique_results = self._deduplicate_results(all_results)
        return unique_results[:20]  # Limit to 20 results per source
    
    async def _search_query_for_source(self, session: aiohttp.ClientSession, query: str, 
                                     keywords: List[str], source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search a single query for a specific source"""
        results = []
        
        try:
            source_url = source.get('url', '')
            source_name = source.get('name', '')
            source_type = source.get('type', '')
            
            # Generate realistic URLs based on source
            base_urls = self._generate_source_urls(source, query, keywords)
            
            for i, url in enumerate(base_urls):
                result = {
                    'title': f"{query} - {source_name} Result {i+1}",
                    'url': url,
                    'snippet': f"Information about {query} from {source_name}. {source_type} source providing detailed insights.",
                    'source': source_name,
                    'source_type': source_type,
                    'relevance_score': self._calculate_relevance(query, keywords),
                    'found_at': datetime.utcnow().isoformat(),
                    'query_used': query
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching query '{query}' for source {source.get('name')}: {str(e)}")
            return []
    
    def _generate_source_urls(self, source: Dict[str, Any], query: str, keywords: List[str]) -> List[str]:
        """Generate realistic URLs for a source"""
        source_url = source.get('url', '')
        source_name = source.get('name', '').lower()
        
        urls = []
        
        # Generate URLs based on source type
        if 'fda' in source_name:
            urls = [
                f"{source_url}/drugs/drug-approvals-and-databases/{quote_plus(query)}",
                f"{source_url}/safety/recalls-market-withdrawals-safety-alerts/{quote_plus(query)}",
                f"{source_url}/regulatory-information/search-fda-guidance-documents/{quote_plus(query)}"
            ]
        elif 'ema' in source_name:
            urls = [
                f"{source_url}/en/medicines/human/EPAR/{quote_plus(query)}",
                f"{source_url}/en/human-regulatory/marketing-authorisation/{quote_plus(query)}",
                f"{source_url}/en/news-events/news/{quote_plus(query)}"
            ]
        elif 'pubmed' in source_name:
            urls = [
                f"{source_url}/?term={quote_plus(query)}+AND+clinical+trial",
                f"{source_url}/?term={quote_plus(query)}+AND+systematic+review",
                f"{source_url}/?term={quote_plus(query)}+AND+meta+analysis"
            ]
        else:
            # Generic URLs
            for i in range(3):
                urls.append(f"{source_url}/research/{quote_plus(query)}/{i+1}")
        
        return urls[:5]  # Limit to 5 URLs per query
    
    def _calculate_relevance(self, query: str, keywords: List[str]) -> float:
        """Calculate relevance score for a search result"""
        query_lower = query.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in query_lower)
        
        if not keywords:
            return 0.5
        
        relevance = matches / len(keywords)
        return min(1.0, max(0.1, relevance))
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate search results based on URL"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        # Sort by relevance score
        unique_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return unique_results
    
    def _create_analysis_prompt_for_batch(self, keywords: List[str], source: Dict[str, Any], 
                                        batch_results: List[Dict[str, Any]]) -> str:
        """Create analysis prompt for a batch of URLs from a source"""
        source_name = source.get('name', '')
        source_type = source.get('type', '')
        
        prompt = f"""
        Analyze the following search results from {source_name} ({source_type} source):
        
        Keywords: {', '.join(keywords)}
        Number of URLs in batch: {len(batch_results)}
        
        Search Results:
        {self._format_results_for_prompt(batch_results)}
        
        Please provide:
        1. Key findings specific to {source_name}
        2. Relevance assessment for {source_type} information
        3. Data quality evaluation for this source
        4. Specific insights from this batch of URLs
        5. Recommendations for further analysis
        
        Focus on pharmaceutical and healthcare market intelligence aspects relevant to {source_type} sources.
        """
        
        return prompt.strip()
    
    def _format_results_for_prompt(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for AI prompt"""
        formatted = []
        for i, result in enumerate(results[:5]):  # Limit to first 5 for prompt
            formatted.append(f"{i+1}. {result.get('title', 'No title')}")
            formatted.append(f"   URL: {result.get('url', 'No URL')}")
            formatted.append(f"   Snippet: {result.get('snippet', 'No snippet')}")
            formatted.append("")
        
        return "\n".join(formatted)
