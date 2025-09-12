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
        self.insights_table = "content_insight-local"
        self.regenerate_insights_table = "regenerate_insights-local"
        
        logger.info(f"Initialized {self.service_name}")
    
    async def regenerate_insights(self, content_id: str, user_prompt: str, 
                                metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Regenerate insights based on content_id and user prompt
        
        Args:
            content_id: The content ID to fetch summary for
            user_prompt: User's custom prompt for regeneration
            metadata: Additional metadata for processing
            
        Returns:
            Dict with regenerated insights and processing metadata
        """
        try:
            logger.info(f"🔄 Starting insights regeneration for content ID: {content_id}")
            
            # Step 1: Fetch existing summary from insights table
            existing_summary = await self._fetch_summary_by_content_id(content_id)
            if not existing_summary:
                raise ValueError(f"No existing summary found for content_id: {content_id}")
            
            # Step 2: Build prompt with prefix and postfix
            formatted_prompt = self._build_regeneration_prompt(existing_summary, user_prompt)
            
            # Step 3: Generate new insights using Bedrock
            bedrock_result = await self.bedrock_service.generate_insights(
                prompt=formatted_prompt,
                content_id=content_id,
                metadata=metadata
            )
            
            if not bedrock_result.get("success"):
                raise Exception(f"Bedrock service failed: {bedrock_result.get('content', 'Unknown error')}")
            
            # Step 4: Store regenerated insights
            storage_result = await self._store_regenerated_insights(
                content_id=content_id,
                user_prompt=user_prompt,
                original_summary=existing_summary,
                regenerated_content=bedrock_result.get("content", ""),
                bedrock_metadata=bedrock_result.get("processing_metadata", {}),
                metadata=metadata
            )
            
            logger.info(f"✅ Successfully regenerated insights for content ID: {content_id}")
            
            return {
                "success": True,
                "content_id": content_id,
                "regenerated_insights": bedrock_result.get("content", ""),
                "regeneration_id": storage_result.get("regeneration_id"),
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "user_prompt_length": len(user_prompt),
                    "original_summary_length": len(existing_summary),
                    "regenerated_content_length": len(bedrock_result.get("content", "")),
                    "bedrock_metadata": bedrock_result.get("processing_metadata", {})
                }
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
    
    async def _fetch_summary_by_content_id(self, content_id: str) -> Optional[str]:
        """Fetch existing summary from insights table by content_id"""
        try:
            logger.info(f"📖 Fetching summary for content ID: {content_id}")
            
            # Query insights table for the content_id
            items = self.dynamodb_client.scan_items(
                table_name=self.insights_table,
                filter_expression="content_id = :content_id",
                expression_attribute_values={":content_id": content_id}
            )
            
            if not items:
                logger.warning(f"No insights found for content_id: {content_id}")
                return None
            
            # Get the most recent insight (assuming there might be multiple)
            latest_item = max(items, key=lambda x: x.get('created_at', ''))
            
            # Extract the insight text
            summary = latest_item.get('insight_text', '') or latest_item.get('content', '')
            
            if summary:
                logger.info(f"📖 Found summary for content ID {content_id}: {len(summary)} characters")
                return summary
            else:
                logger.warning(f"Summary found but empty for content_id: {content_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching summary for content {content_id}: {str(e)}")
            return None
    
    def _build_regeneration_prompt(self, existing_summary: str, user_prompt: str) -> str:
        """Build the regeneration prompt with prefix and postfix"""
        
        prefix = """
You are an expert market intelligence analyst specializing in pharmaceutical and healthcare insights. 
You have been provided with an existing market analysis summary and a specific user request for regeneration.

Your task is to regenerate and enhance the insights based on the user's specific requirements while maintaining the core analytical value.

**EXISTING MARKET ANALYSIS SUMMARY:**
{existing_summary}

**USER'S SPECIFIC REQUEST:**
{user_prompt}

**INSTRUCTIONS FOR REGENERATION:**
"""
        
        postfix = """

**OUTPUT REQUIREMENTS:**
1. Maintain the analytical depth and market intelligence value
2. Address the user's specific requirements and focus areas
3. Provide actionable insights relevant to pharmaceutical/healthcare industry
4. Use clear structure with headings and bullet points
5. Include specific data points and market intelligence where applicable
6. Ensure the regenerated content is comprehensive yet focused on the user's request

Generate enhanced market insights that specifically address the user's requirements while building upon the existing analysis.
"""
        
        formatted_prompt = prefix.format(
            existing_summary=existing_summary,
            user_prompt=user_prompt
        ) + postfix
        
        logger.info(f"🔧 Built regeneration prompt: {len(formatted_prompt)} characters")
        return formatted_prompt
    
    async def _store_regenerated_insights(self, content_id: str, user_prompt: str, 
                                        original_summary: str, regenerated_content: str,
                                        bedrock_metadata: Dict[str, Any],
                                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Store the regenerated insights in the regenerate_insights table"""
        try:
            logger.info(f"💾 Storing regenerated insights for content ID: {content_id}")
            
            # Generate unique ID for this regeneration
            regeneration_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            # Prepare item for storage
            regeneration_item = {
                "pk": regeneration_id,
                "content_id": content_id,
                "user_prompt": user_prompt,
                "original_summary": original_summary,
                "regenerated_insights": regenerated_content,
                "regeneration_type": "insights",
                "bedrock_metadata": bedrock_metadata,
                "user_metadata": metadata or {},
                "created_at": now,
                "created_by": "regenerate_service",
                "version": 1,
                "is_active": True
            }
            
            # Store in DynamoDB
            success = self.dynamodb_client.put_item(
                table_name=self.regenerate_insights_table,
                item=regeneration_item
            )
            
            if success:
                logger.info(f"💾 Stored regenerated insights: {regeneration_id}")
                return {
                    "regeneration_id": regeneration_id,
                    "success": True,
                    "stored_at": now
                }
            else:
                raise Exception("Failed to store regenerated insights in DynamoDB")
                
        except Exception as e:
            logger.error(f"❌ Error storing regenerated insights: {str(e)}")
            raise
    
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
            sorted_items = sorted(items, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]
            
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