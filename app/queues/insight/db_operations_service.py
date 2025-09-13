"""
Database Operations Service for Insight Queue
Handles DynamoDB operations for content_insight-local table
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid

from app.database.dynamodb_client import dynamodb_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InsightDBOperationsService:
    """Service to handle DynamoDB operations for Insight results"""
    
    def __init__(self):
        self.service_name = "Insight DB Operations Service"
        # DynamoDB table name
        self.content_insight_table = "content_insight-local"
    
    def process_insight_completion(self, insight_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Insight completion and store data in content_insight-local table
        
        Args:
            insight_data: Complete Insight processing result
            
        Returns:
            Dict with operation results
        """
        try:
            logger.info(f"Processing Insight completion for DynamoDB operations")
            
            # Extract key information
            content_id = insight_data.get('content_id')
            project_id = insight_data.get('project_id')
            request_id = insight_data.get('request_id')
            insights_response = insight_data.get('insights_response', '')
            url_data = insight_data.get('url_data', {})
            
            if not content_id:
                raise ValueError("Missing content_id")
            if not project_id or not request_id:
                raise ValueError("Missing project_id or request_id")

            logger.info(f"🔍 INSIGHT DB OPERATIONS - Content ID: {content_id} | Storing insight data")
            
            # Store in content_insight table
            result = self._store_content_insight(insight_data, content_id)
            
            processing_result = {
                'content_insight_result': result,
                'processing_metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'service': self.service_name,
                    'content_id': content_id,
                    'project_id': project_id,
                    'request_id': request_id,
                    'table_processed': self.content_insight_table
                }
            }
            
            if result.get('success'):
                logger.info(f"✅ INSIGHT DB SUCCESS - Content ID: {content_id} | Successfully stored insight data")
            else:
                logger.error(f"❌ INSIGHT DB FAILED - Content ID: {content_id} | Failed to store insight data")
            
            return processing_result
            
        except Exception as e:
            logger.error(f"❌ INSIGHT DB ERROR - Content ID: {insight_data.get('content_id', 'Unknown')} | Error processing insight completion: {str(e)}")
            return {
                'error': str(e),
                'processing_metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'service': self.service_name,
                    'content_id': insight_data.get('content_id', 'Unknown'),
                    'status': 'error'
                }
            }
    
    def _store_content_insight(self, insight_data: Dict[str, Any], content_id: str) -> Dict[str, Any]:
        """
        Store data in content_insight-local table
        
        Args:
            insight_data: Insight processing result
            content_id: Content ID from perplexity processing
            
        Returns:
            Dict with operation result
        """
        try:
            project_id = insight_data.get('project_id')
            request_id = insight_data.get('request_id')
            insights_response = insight_data.get('insights_response', '')
            url_data = insight_data.get('url_data', {})
            s3_insights_key = insight_data.get('s3_insights_key', '')
            processing_metadata = insight_data.get('processing_metadata', {})
            
            # Create content insight item matching the provided structure
            now = datetime.utcnow().isoformat()
            insight_pk = str(uuid.uuid4())
            
            # Generate insight content file path
            insight_content_file_path = f"insights/{project_id}/{request_id}/{content_id}/insight.json"
            
            # Determine insight category based on content analysis
            insight_category = self._determine_insight_category(insights_response, url_data)
            
            # Calculate confidence score based on processing quality
            confidence_score = self._calculate_confidence_score(insight_data)
            
            content_insight_item = {
                'pk': insight_pk,
                'url_id': content_id,  # Using content_id as url_id for linking
                'content_id': content_id,
                'insight_text': insights_response,
                'insight_content_file_path': insight_content_file_path,
                'insight_category': insight_category,
                'confidence_score': "saved",
                'version': 1,
                'is_canonical': True,
                'preferred_choice': True,
                'created_at': now,
                'created_by': 'insight_service'
            }
            
            # Store in DynamoDB
            success = dynamodb_client.put_item(self.content_insight_table, content_insight_item)
            
            if success:
                logger.info(f"✅ INSIGHT DB STORED - Content ID: {content_id} | Stored insight item: {insight_pk}")
                return {
                    'success': True,
                    'table_name': self.content_insight_table,
                    'item_key': insight_pk,
                    'content_id': content_id,
                    'insight_category': insight_category,
                    'confidence_score': confidence_score,
                    'message': 'Content insight data stored successfully'
                }
            else:
                raise Exception("Failed to store item in DynamoDB")
                
        except Exception as e:
            logger.error(f"❌ INSIGHT DB ERROR - Content ID: {content_id} | Error storing content insight: {str(e)}")
            return {
                'success': False,
                'table_name': self.content_insight_table,
                'content_id': content_id,
                'error': str(e)
            }
    
    def _determine_insight_category(self, insights_response: str, url_data: Dict[str, Any]) -> str:
        """Determine insight category based on content analysis"""
        try:
            if not insights_response:
                return "general"
            
            response_lower = insights_response.lower()
            
            # Market-related insights
            market_terms = ['market', 'competitive', 'competition', 'market share', 'market size']
            if any(term in response_lower for term in market_terms):
                return "market_analysis"
            
            # Regulatory insights
            regulatory_terms = ['regulatory', 'fda', 'approval', 'compliance', 'regulation']
            if any(term in response_lower for term in regulatory_terms):
                return "regulatory"
            
            # Financial insights
            financial_terms = ['revenue', 'cost', 'financial', 'roi', 'investment', 'budget']
            if any(term in response_lower for term in financial_terms):
                return "financial"
            
            # Technology/Innovation insights
            tech_terms = ['technology', 'innovation', 'research', 'development', 'pipeline']
            if any(term in response_lower for term in tech_terms):
                return "technology"
            
            # Strategic insights
            strategic_terms = ['strategy', 'strategic', 'opportunity', 'growth', 'expansion']
            if any(term in response_lower for term in strategic_terms):
                return "strategic"
            
            return "general"
            
        except Exception:
            return "general"
    
    def _calculate_confidence_score(self, insight_data: Dict[str, Any]) -> float:
        """Calculate confidence score for the insight data"""
        try:
            score = 0.0
            
            # Base score for having insights response
            if insight_data.get('insights_response'):
                score += 0.3
            
            # Processing success
            if insight_data.get('insights_success', False):
                score += 0.3
            
            # URL data quality
            url_data = insight_data.get('url_data', {})
            if url_data.get('title'):
                score += 0.1
            if url_data.get('url'):
                score += 0.1
            
            # Processing metadata quality
            processing_metadata = insight_data.get('processing_metadata', {})
            if processing_metadata.get('bedrock_model'):
                score += 0.1
            
            # S3 storage success
            if insight_data.get('s3_insights_key'):
                score += 0.1
            
            return min(1.0, score)
            
        except Exception:
            return 0.5  # Default medium confidence


# Global service instance
insight_db_operations_service = InsightDBOperationsService() 