import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from app.utils.logger import get_logger
from app.database.dynamodb_client import DynamoDBClient
from app.services.regenerate_insights_bedrock_service import RegenerateInsightsBedrockService

logger = get_logger(__name__)


class RegenerateInsightsService:
    """Service for regenerating insights based on user input and existing summaries"""
    
    def __init__(self):
        self.service_name = "Regenerate Insights Service"
        self.dynamodb_client = DynamoDBClient()
        self.bedrock_service = RegenerateInsightsBedrockService()
        
        # Table names - using existing table patterns
        self.insights_table = "content_insight"
        self.regenerate_insights_table = "regenerate_insights"
        
        logger.info(f"Initialized {self.service_name}")
    
    async def regenerate_insights(self, content_id: str, text_input: str, 
                                metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Regenerate insights by directly processing text input with Bedrock
        
        Args:
            content_id: The content ID for tracking and identification
            text_input: Large text input to be processed by Bedrock
            metadata: Additional metadata for processing
            
        Returns:
            Dict with regenerated insights and processing metadata
        """
        try:
            logger.info(f"🔄 Starting insights regeneration for content ID: {content_id}")
            
            # Directly generate insights using Bedrock with the provided text
            bedrock_result = await self.bedrock_service.generate_insights(
                prompt=text_input,
                content_id=content_id,
                metadata=metadata
            )
            
            if not bedrock_result.get("success"):
                raise Exception(f"Bedrock service failed: {bedrock_result.get('content', 'Unknown error')}")
            
            logger.info(f"✅ Successfully regenerated insights for content ID: {content_id}")
            
            return {
                "success": True,
                "content_id": content_id,
                "regenerated_insights": bedrock_result.get("content", "")
            }
            
        except Exception as e:
            logger.error(f"❌ Error regenerating insights for content {content_id}: {str(e)}")
            
            return {
                "success": False,
                "content_id": content_id,
                "error": str(e),
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "error": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                }
            }
    

    

    
    async def get_regeneration_history(self, content_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get regeneration history for a content_id"""
        try:
            logger.info(f"📋 Getting regeneration history for content ID: {content_id}")
            
            items = self.dynamodb_client.scan_items(
                table_name=self.regenerate_insights_table,
                filter_expression="content_id = :content_id AND regeneration_type = :type",
                expression_attribute_values={
                    ":content_id": content_id,
                    ":type": "insights"
                }
            )
            
            # Sort by creation time (newest first) and limit
            sorted_items = sorted(items, key=lambda x: x.get('created_at', '') if isinstance(x, dict) else "", reverse=True)[:limit]
            
            return {
                "success": True,
                "content_id": content_id,
                "regeneration_history": sorted_items,
                "total_count": len(sorted_items)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting regeneration history: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content_id": content_id,
                "regeneration_history": []
            } 