from typing import Dict, Any
from datetime import datetime

from .bedrock_service import ImplicationBedrockService
from .prompt_config import ImplicationPromptManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImplicationProcessor:
    """Processor for generating business implications using AWS Bedrock"""
    
    def __init__(self):
        self.name = "Implication Processor"
        self.bedrock_service = ImplicationBedrockService()
    
    def generate_implications(self, perplexity_response: str, url_data: Dict[str, Any], 
                            user_prompt: str = "", content_id: str = "") -> Dict[str, Any]:
        """Generate business implications from Perplexity response using Bedrock"""
        try:
            logger.info(f"Generating business implications for content ID: {content_id}")
            
            # Prepare implication prompt using prompt manager
            implication_prompt = ImplicationPromptManager.get_prompt(
                perplexity_response=perplexity_response,
                url_data=url_data,
                user_prompt=user_prompt,
                content_id=content_id
            )
            
            # Call Bedrock service
            result = self.bedrock_service.generate_implications(implication_prompt, content_id)
            
            # Process response
            return {
                "implications": result.get("content", ""),
                "success": result.get("success", False),
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "content_id": content_id,
                    "url": url_data.get('url', ''),
                    "prompt_length": len(implication_prompt),
                    "prompt_mode": ImplicationPromptManager.get_current_mode(),
                    "bedrock_model": result.get("model_used", "unknown")
                },
                "status": "success" if result.get("success") else "error"
            }
            
        except Exception as e:
            logger.error(f"Error generating implications for content ID {content_id}: {str(e)}")
            return {
                "implications": f"Error generating implications: {str(e)}",
                "success": False,
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "content_id": content_id,
                    "error": str(e)
                },
                "status": "error"
            }
    

