from typing import Dict, Any, List
from datetime import datetime
import asyncio

from .serp_api import SerpAPI
from .serp_query_builder import build_query, build_date_range_query
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SerpProcessor:
    """SERP processor with real API calls"""
    
    def __init__(self):
        self.name = "SERP Processor"
    
    async def process_search_data(self, keywords: List[str], source: Dict[str, Any], 
                                 start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Process search data using real SERP API calls"""
        try:
            logger.info(f"Processing search data for {len(keywords)} keywords from {source.get('name', 'Unknown')}")
            
            # Use SERP API to get real search results
            async with SerpAPI() as serp_api:
                if start_date and end_date:
                    # Use date range search
                    response = await serp_api.search_with_date_range(
                        keywords=keywords,
                        source=source,
                        start_date=start_date,
                        end_date=end_date
                    )
                else:
                    # Use regular search with query builder
                    response = await serp_api.search_with_query_builder(
                        keywords=keywords,
                        source=source,
                        date_filter="m"  # Default to past month
                    )
            
            # Convert SERP results to our format
            search_results = []
            for result in response.results:
                search_results.append({
                    'title': result.title,
                    'url': result.url,
                    'snippet': result.snippet,
                    'source': source.get('name', ''),
                    'source_type': source.get('type', ''),
                    'relevance_score': 0.8,  # Default relevance
                    'found_at': datetime.utcnow().isoformat(),
                    'position': result.position,
                    'domain': result.domain
                })
            
            # Create processing metadata
            processing_metadata = {
                'processed_at': datetime.utcnow().isoformat(),
                'processor': self.name,
                'keywords_count': len(keywords),
                'results_found': len(search_results),
                'total_results': response.total_results,
                'request_id': response.request_id,
                'source_info': {
                    'name': source.get('name', ''),
                    'type': source.get('type', ''),
                    'url': source.get('url', '')
                }
            }
            
            return {
                'search_results': search_results,
                'processing_metadata': processing_metadata,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error processing search data: {str(e)}")
            return {
                'search_results': [],
                'processing_metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'processor': self.name,
                    'error': str(e)
                },
                'status': 'error'
            }
    
    def validate_search_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate search results structure"""
        valid_results = []
        validation_errors = []
        
        required_fields = ['title', 'url', 'snippet', 'source']
        
        for i, result in enumerate(results):
            missing_fields = [field for field in required_fields if not result.get(field)]
            
            if missing_fields:
                validation_errors.append(f"Result {i+1}: Missing fields {missing_fields}")
            else:
                valid_results.append(result)
        
        return {
            'valid_results': valid_results,
            'validation_errors': validation_errors,
            'total_results': len(results),
            'valid_count': len(valid_results),
            'error_count': len(validation_errors)
        }
