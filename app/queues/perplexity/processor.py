from typing import Dict, Any
from datetime import datetime

from .perplexity_api import PerplexityAPI
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PerplexityProcessor:
    """Simple Perplexity processor - one call with user prompt"""
    
    def __init__(self):
        self.name = "Perplexity Processor"
    
    async def process_user_prompt(self, user_prompt: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user prompt with Perplexity - simple and clean"""
        try:
            logger.info(f"Processing user prompt with Perplexity")
            
            # Call Perplexity API
            async with PerplexityAPI() as perplexity_api:
                result = await perplexity_api.ask_perplexity(user_prompt)
            
            # Simple response structure
            return {
                "perplexity_response": result.get("content", ""),
                "success": result.get("success", False),
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "prompt_length": len(user_prompt),
                    "has_context": context_data is not None
                },
                "status": "success" if result.get("success") else "error"
            }
            
        except Exception as e:
            logger.error(f"Error processing user prompt: {str(e)}")
            return {
                "perplexity_response": f"Error: {str(e)}",
                "success": False,
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "error": str(e)
                },
                "status": "error"
            }
