from typing import Dict, Any
from datetime import datetime

from .bedrock_service import InsightBedrockService
from .prompt_config import InsightPromptManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InsightProcessor:
    """Processor for generating market insights using AWS Bedrock"""
    
    def __init__(self):
        self.name = "Insight Processor"
        self.bedrock_service = InsightBedrockService()
    
    async def generate_insights(self, perplexity_response: str, url_data: Dict[str, Any], 
                               user_prompt: str = "", content_id: str = "") -> Dict[str, Any]:
        """Generate market insights from Perplexity response using Bedrock"""
        try:
            logger.info(f"Generating market insights for content ID: {content_id}")
            
            # Prepare insight prompt using prompt manager
            insight_prompt = InsightPromptManager.get_prompt(
                perplexity_response=perplexity_response,
                url_data=url_data,
                user_prompt=user_prompt,
                content_id=content_id
            )
            
            # Call Bedrock service (async)
            result = await self.bedrock_service.generate_insights(insight_prompt, content_id)
            
            # Process response
            return {
                "insights": result.get("content", ""),
                "success": result.get("success", False),
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "content_id": content_id,
                    "url": url_data.get('url', ''),
                    "prompt_length": len(insight_prompt),
                    "prompt_mode": InsightPromptManager.get_current_mode(),
                    "bedrock_model": result.get("model_used", "unknown")
                },
                "status": "success" if result.get("success") else "error"
            }
            
        except Exception as e:
            logger.error(f"Error generating insights for content ID {content_id}: {str(e)}")
            return {
                "insights": f"Error generating insights: {str(e)}",
                "success": False,
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "content_id": content_id,
                    "error": str(e)
                },
                "status": "error"
            }
    

