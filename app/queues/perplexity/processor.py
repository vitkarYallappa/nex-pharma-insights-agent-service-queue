from typing import Dict, Any
from datetime import datetime

from .perplexity_api import PerplexityAPI
from .json_formatter import PerplexityJSONFormatter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PerplexityProcessor:
    """Simple Perplexity processor - one call with user prompt"""
    
    def __init__(self):
        self.name = "Perplexity Processor"
        self.formatter = PerplexityJSONFormatter()
    
    async def process_user_prompt(self, user_prompt: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user prompt with Perplexity - simple and clean"""
        try:
            logger.info(f"Processing user prompt with Perplexity")
            
            # Call Perplexity API
            async with PerplexityAPI() as perplexity_api:
                api_result = await perplexity_api.ask_perplexity(user_prompt)
            
            if not api_result.get("success", False):
                logger.error(f"Perplexity API call failed: {api_result.get('content', 'Unknown error')}")
                return self._create_error_response(api_result.get('content', 'API call failed'), context_data)
            
            # Parse the response content using JSON formatter
            raw_content = api_result.get("content", "")
            parsed_data = self.formatter.parse_response_content(raw_content)
            
            # Format for downstream processing
            formatted_data = self.formatter.format_for_downstream(parsed_data)
            
            # Extract metadata
            formatter_metadata = self.formatter.extract_metadata(parsed_data)
            
            # Enhanced response structure
            return {
                "perplexity_response": formatted_data.get("main_content", ""),  # HTML formatted content for downstream queues
                "success": True,
                "parsed_data": parsed_data,  # Full parsed structure
                "formatted_data": formatted_data,  # Structured output with main_content, publish_date, source_type
                "processing_metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor": self.name,
                    "prompt_length": len(user_prompt),
                    "has_context": context_data is not None,
                    "response_length": len(raw_content),
                    "formatted_length": len(formatted_data.get("main_content", "")),
                    **formatter_metadata
                },
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing user prompt: {str(e)}")
            return self._create_error_response(f"Processing error: {str(e)}", context_data)
    
    def _create_error_response(self, error_msg: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "perplexity_response": f"Error: {error_msg}",
            "success": False,
            "parsed_data": self.formatter._create_error_response("", error_msg),
            "processing_metadata": {
                "processed_at": datetime.utcnow().isoformat(),
                "processor": self.name,
                "error": error_msg,
                "has_context": context_data is not None,
                "response_type": "error",
                "parsed_successfully": False
            },
            "status": "error"
        }
