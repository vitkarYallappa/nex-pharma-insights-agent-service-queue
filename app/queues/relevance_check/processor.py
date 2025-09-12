from typing import Dict, Any
from datetime import datetime

from .bedrock_service import RelevanceCheckBedrockService
from .prompt_config import RelevanceCheckPromptManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RelevanceCheckProcessor:
    """Processor for checking content relevance using AWS Bedrock"""
    
    def __init__(self):
        self.name = "Relevance Check Processor"
        self.bedrock_service = RelevanceCheckBedrockService()
    
    async def check_relevance(self, perplexity_response: str, url_data: Dict[str, Any], 
                            user_prompt: str = "", content_id: str = "") -> Dict[str, Any]:
        """Check content relevance from Perplexity response using Bedrock"""
        try:
            logger.info(f"Checking relevance for content ID: {content_id}")
            
            # Prepare relevance check prompt using prompt manager
            relevance_prompt = RelevanceCheckPromptManager.get_prompt(
                perplexity_response=perplexity_response,
                url_data=url_data,
                user_prompt=user_prompt,
                content_id=content_id
            )
            
            # Call Bedrock service (async)
            result = await self.bedrock_service.check_relevance(relevance_prompt, content_id)
            
            # Process response
            return {
                "relevance_analysis": result.get("content", ""),
                "success": result.get("success", False),
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "content_id": content_id,
                    "url": url_data.get('url', ''),
                    "prompt_length": len(relevance_prompt),
                    "prompt_mode": RelevanceCheckPromptManager.get_current_mode(),
                    "bedrock_model": result.get("model_used", "unknown")
                },
                "status": "success" if result.get("success") else "error"
            }
            
        except Exception as e:
            logger.error(f"Error checking relevance for content ID {content_id}: {str(e)}")
            return {
                "relevance_analysis": f"Error checking relevance: {str(e)}",
                "success": False,
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "content_id": content_id,
                    "error": str(e)
                },
                "status": "error"
            } 