import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
import os

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PerplexityAPI:
    """Simple Perplexity API client - one call with user prompt"""
    
    def __init__(self):
        # Load API key from environment or config
        self.api_key = os.getenv('PERPLEXITY_API_KEY', 'your-perplexity-api-key')
        self.base_url = "https://api.perplexity.ai"
        self.session = None
        
        # Check if API key is properly configured
        if self.api_key == 'your-perplexity-api-key' or not self.api_key:
            logger.warning("Perplexity API key not configured. Set PERPLEXITY_API_KEY environment variable.")
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def ask_perplexity(self, user_prompt: str) -> Dict[str, Any]:
        """Simple call to Perplexity with user prompt"""
        try:
            # Check if API key is configured
            if self.api_key == 'your-perplexity-api-key' or not self.api_key:
                logger.warning("Perplexity API key not configured, using mock response")
                return self._create_mock_response(user_prompt)
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            logger.info(f"Calling Perplexity API with user prompt")
            
            # Simple API call
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.2
            }
            
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return self._parse_simple_response(data)
                elif response.status == 401:
                    logger.error("Perplexity API authentication failed (401). Check your API key.")
                    return self._create_auth_error_response(user_prompt)
                elif response.status == 429:
                    logger.error("Perplexity API rate limit exceeded (429). Please try again later.")
                    return self._create_rate_limit_response(user_prompt)
                else:
                    logger.warning(f"Perplexity API failed with status {response.status}")
                    return self._create_error_response(user_prompt, f"API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error calling Perplexity API: {str(e)}")
            return self._create_error_response(user_prompt, str(e))
    
    def _parse_simple_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Perplexity response - keep it simple"""
        try:
            choices = data.get("choices", [])
            if not choices:
                return {"content": "No response from Perplexity", "success": False}
            
            content = choices[0].get("message", {}).get("content", "")
            
            if not content:
                return {"content": "Empty response from Perplexity", "success": False}
            
            return {
                "content": content,
                "success": True,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing Perplexity response: {str(e)}")
            return {"content": f"Error parsing response: {str(e)}", "success": False}
    
    def _create_mock_response(self, user_prompt: str) -> Dict[str, Any]:
        """Create mock response when API key is not configured"""
        mock_content = f"""
        Mock Perplexity Analysis for: {user_prompt[:100]}...
        
        Key Findings:
        1. This is a simulated response since Perplexity API key is not configured
        2. The system is working correctly but using mock data
        3. To get real Perplexity responses, set the PERPLEXITY_API_KEY environment variable
        
        Market Intelligence:
        - Mock market data analysis
        - Simulated competitive insights
        - Sample regulatory information
        
        Recommendations:
        - Configure proper API key for real analysis
        - Review mock data structure for integration testing
        """
        
        return {
            "content": mock_content.strip(),
            "success": True,
            "processed_at": datetime.utcnow().isoformat(),
            "mock": True
        }
    
    def _create_auth_error_response(self, user_prompt: str) -> Dict[str, Any]:
        """Create response for authentication errors"""
        return {
            "content": f"Authentication failed: Invalid Perplexity API key. Please check your PERPLEXITY_API_KEY configuration.",
            "success": False,
            "processed_at": datetime.utcnow().isoformat(),
            "error": "authentication_failed"
        }
    
    def _create_rate_limit_response(self, user_prompt: str) -> Dict[str, Any]:
        """Create response for rate limit errors"""
        return {
            "content": f"Rate limit exceeded: Perplexity API requests are being throttled. Please try again later.",
            "success": False,
            "processed_at": datetime.utcnow().isoformat(),
            "error": "rate_limit_exceeded"
        }
    
    def _create_error_response(self, user_prompt: str, error_msg: str) -> Dict[str, Any]:
        """Create response for general errors"""
        return {
            "content": f"Error processing request: {error_msg}",
            "success": False,
            "processed_at": datetime.utcnow().isoformat(),
            "error": "api_error"
        }
