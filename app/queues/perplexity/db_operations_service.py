"""
Database Operations Service for Perplexity Queue
Handles DynamoDB operations for content_repository-local, content_summary-local, and related tables
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from app.database.dynamodb_client import dynamodb_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PerplexityDBOperationsService:
    """Service to handle DynamoDB operations for Perplexity results"""
    
    def __init__(self):
        self.service_name = "Perplexity DB Operations Service"
        # DynamoDB table names
        self.content_repository_table = "content_repository-local"
        self.content_summary_table = "content_summary-local"
        self.content_url_mapping_table = "content_url_mapping-local"
    
    def process_perplexity_completion(self, perplexity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Perplexity completion and store data in DynamoDB tables
        
        Args:
            perplexity_data: Complete Perplexity processing result
            
        Returns:
            Dict with operation results for all 3 tables
        """
        try:
            logger.info(f"Processing Perplexity completion for DynamoDB operations")
            
            # Extract key information
            project_id = perplexity_data.get('project_id')
            request_id = perplexity_data.get('request_id')
            url_data = perplexity_data.get('url_data', {})
            perplexity_response = perplexity_data.get('perplexity_response', '')
            
            if not project_id or not request_id:
                raise ValueError("Missing project_id or request_id")
            
            # Process each DynamoDB table
            results = {
                'content_repository_result': self._store_content_repository(perplexity_data),
                'content_summary_result': self._store_content_summary(perplexity_data),
                'content_url_mapping_result': self._store_content_url_mapping(perplexity_data),
                'processing_metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'service': self.service_name,
                    'project_id': project_id,
                    'request_id': request_id,
                    'tables_processed': 3
                }
            }
            
            logger.info(f"Successfully processed Perplexity data for DynamoDB: {project_id}/{request_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error processing Perplexity completion: {str(e)}")
            return {
                'error': str(e),
                'processing_metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'service': self.service_name,
                    'status': 'error'
                }
            }
    
    def _store_content_repository(self, perplexity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store data in content_repository-local table
        
        Args:
            perplexity_data: Perplexity processing result
            
        Returns:
            Dict with operation result
        """
        try:
            project_id = perplexity_data.get('project_id')
            request_id = perplexity_data.get('request_id')
            url_data = perplexity_data.get('url_data', {})
            
            # Create content repository item
            content_item = {
                'PK': f"CONTENT#{project_id}#{request_id}",
                'SK': f"URL#{url_data.get('url', 'unknown')}#{int(datetime.utcnow().timestamp())}",
                'project_id': project_id,
                'request_id': request_id,
                'url': url_data.get('url', ''),
                'title': url_data.get('title', ''),
                'snippet': url_data.get('snippet', ''),
                'source': url_data.get('source', ''),
                'relevance_score': url_data.get('relevance_score', 0.0),
                'perplexity_response': perplexity_data.get('perplexity_response', ''),
                'response_length': len(perplexity_data.get('perplexity_response', '')),
                'processing_success': perplexity_data.get('processing_metadata', {}).get('status') != 'error',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'processed'
            }
            
            # Store in DynamoDB
            success = dynamodb_client.put_item(self.content_repository_table, content_item)
            
            if success:
                logger.info(f"Stored content repository item: {content_item['PK']}")
                return {
                    'success': True,
                    'table_name': self.content_repository_table,
                    'item_key': content_item['PK'],
                    'message': 'Content repository data stored successfully'
                }
            else:
                raise Exception("Failed to store item in DynamoDB")
                
        except Exception as e:
            logger.error(f"Error storing content repository: {str(e)}")
            return {
                'success': False,
                'table_name': self.content_repository_table,
                'error': str(e)
            }
    
    def _store_content_summary(self, perplexity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store data in content_summary-local table
        
        Args:
            perplexity_data: Perplexity processing result
            
        Returns:
            Dict with operation result
        """
        try:
            project_id = perplexity_data.get('project_id')
            request_id = perplexity_data.get('request_id')
            perplexity_response = perplexity_data.get('perplexity_response', '')
            
            # Create content summary item
            summary_item = {
                'PK': f"SUMMARY#{project_id}#{request_id}",
                'SK': f"PERPLEXITY#{int(datetime.utcnow().timestamp())}",
                'project_id': project_id,
                'request_id': request_id,
                'summary_text': self._extract_summary(perplexity_response),
                'full_response': perplexity_response,
                'word_count': len(perplexity_response.split()) if perplexity_response else 0,
                'key_points': self._extract_key_points(perplexity_response),
                'market_relevance': self._assess_market_relevance(perplexity_response),
                'quality_score': self._calculate_quality_score(perplexity_data),
                'source_url': perplexity_data.get('url_data', {}).get('url', ''),
                'keywords': perplexity_data.get('source_info', {}).get('keywords', []),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'processed'
            }
            
            # Store in DynamoDB
            success = dynamodb_client.put_item(self.content_summary_table, summary_item)
            
            if success:
                logger.info(f"Stored content summary item: {summary_item['PK']}")
                return {
                    'success': True,
                    'table_name': self.content_summary_table,
                    'item_key': summary_item['PK'],
                    'message': 'Content summary data stored successfully'
                }
            else:
                raise Exception("Failed to store item in DynamoDB")
                
        except Exception as e:
            logger.error(f"Error storing content summary: {str(e)}")
            return {
                'success': False,
                'table_name': self.content_summary_table,
                'error': str(e)
            }
    
    def _store_content_url_mapping(self, perplexity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store data in content_url_mapping-local table
        
        Args:
            perplexity_data: Perplexity processing result
            
        Returns:
            Dict with operation result
        """
        try:
            project_id = perplexity_data.get('project_id')
            request_id = perplexity_data.get('request_id')
            url_data = perplexity_data.get('url_data', {})
            
            # Create content URL mapping item
            mapping_item = {
                'PK': f"MAPPING#{project_id}#{request_id}",
                'SK': f"URL#{url_data.get('url', 'unknown')}#{int(datetime.utcnow().timestamp())}",
                'project_id': project_id,
                'request_id': request_id,
                'original_url': url_data.get('url', ''),
                'url_hash': hash(url_data.get('url', '')) if url_data.get('url') else 0,
                'url_title': url_data.get('title', ''),
                'url_source': url_data.get('source', ''),
                'url_position': url_data.get('position', 0),
                'relevance_score': url_data.get('relevance_score', 0.0),
                'content_repository_key': f"CONTENT#{project_id}#{request_id}",
                'content_summary_key': f"SUMMARY#{project_id}#{request_id}",
                'processing_order': perplexity_data.get('url_index', 1),
                'total_urls_in_batch': perplexity_data.get('total_urls', 1),
                'serp_query': perplexity_data.get('source_info', {}).get('query', ''),
                'keywords': perplexity_data.get('source_info', {}).get('keywords', []),
                'processing_success': perplexity_data.get('processing_metadata', {}).get('status') != 'error',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'mapped'
            }
            
            # Store in DynamoDB
            success = dynamodb_client.put_item(self.content_url_mapping_table, mapping_item)
            
            if success:
                logger.info(f"Stored content URL mapping item: {mapping_item['PK']}")
                return {
                    'success': True,
                    'table_name': self.content_url_mapping_table,
                    'item_key': mapping_item['PK'],
                    'message': 'Content URL mapping stored successfully'
                }
            else:
                raise Exception("Failed to store item in DynamoDB")
                
        except Exception as e:
            logger.error(f"Error storing content URL mapping: {str(e)}")
            return {
                'success': False,
                'table_name': self.content_url_mapping_table,
                'error': str(e)
            }
    
    def _extract_summary(self, perplexity_response: str) -> str:
        """Extract summary from Perplexity response"""
        try:
            if not perplexity_response:
                return "No summary available"
            
            # Take first 300 characters as summary
            summary = perplexity_response[:300]
            if len(perplexity_response) > 300:
                summary += "..."
            
            return summary.strip()
        except Exception:
            return "Error extracting summary"
    
    def _extract_key_points(self, perplexity_response: str) -> List[str]:
        """Extract key points from Perplexity response"""
        try:
            if not perplexity_response:
                return []
            
            # Simple extraction - look for numbered points or bullet points
            key_points = []
            lines = perplexity_response.split('\n')
            
            for line in lines:
                line = line.strip()
                # Look for numbered points (1., 2., etc.) or bullet points (-, *, •)
                if (line.startswith(('1.', '2.', '3.', '4.', '5.')) or 
                    line.startswith(('- ', '* ', '• '))):
                    key_points.append(line)
            
            return key_points[:5]  # Return top 5 key points
        except Exception:
            return []
    
    def _assess_market_relevance(self, perplexity_response: str) -> str:
        """Assess market relevance of the content"""
        try:
            if not perplexity_response:
                return "unknown"
            
            response_lower = perplexity_response.lower()
            market_terms = ['market', 'competitive', 'regulatory', 'fda', 'approval', 'drug', 'pharmaceutical']
            
            term_count = sum(1 for term in market_terms if term in response_lower)
            
            if term_count >= 3:
                return "high"
            elif term_count >= 1:
                return "medium"
            else:
                return "low"
        except Exception:
            return "unknown"
    
    def _calculate_processing_duration(self, perplexity_data: Dict[str, Any]) -> float:
        """Calculate processing duration if available"""
        try:
            metadata = perplexity_data.get('processing_metadata', {})
            # This would need to be calculated based on your actual processing timestamps
            return metadata.get('processing_duration', 0.0)
        except Exception:
            return 0.0
    
    def _calculate_quality_score(self, perplexity_data: Dict[str, Any]) -> float:
        """Calculate quality score for the processed data"""
        try:
            score = 0.0
            
            # Base score for having a response
            if perplexity_data.get('perplexity_response'):
                score += 0.3
            
            # URL data quality
            url_data = perplexity_data.get('url_data', {})
            if url_data.get('title'):
                score += 0.2
            if url_data.get('snippet'):
                score += 0.2
            
            # Processing success
            if perplexity_data.get('processing_metadata', {}).get('status') != 'error':
                score += 0.3
            
            return min(1.0, score)
        except Exception:
            return 0.0


# Global service instance
db_operations_service = PerplexityDBOperationsService() 