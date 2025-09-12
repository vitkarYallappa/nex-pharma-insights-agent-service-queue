from typing import Dict, Any, Optional
from datetime import datetime

from app.utils.logger import get_logger
from app.config import settings
from .bedrock_service import ImplicationBedrockService
from .prompt_config import ImplicationPromptManager

logger = get_logger(__name__)


class ImplicationProcessor:
    """Processor for generating market implications using AWS Bedrock Agent"""
    
    def __init__(self):
        self.service_name = "Implication Processor"
        
        # Initialize services
        self.bedrock_service = ImplicationBedrockService()
        self.prompt_manager = ImplicationPromptManager(
            environment=getattr(settings, 'ENVIRONMENT', 'development')
        )
        
        logger.info(f"Initialized {self.service_name}")
    
    async def generate_implications(self, content: str, content_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate market implications from content using AWS Bedrock Agent
        
        Args:
            content: The content to analyze for implications
            content_id: Unique identifier for tracking
            metadata: Additional context information
            
        Returns:
            Dict containing implications and processing metadata
        """
        try:
            logger.info(f"📋 Processing implications for content ID: {content_id}")
            
            # Validate input content
            if not self.prompt_manager.validate_content(content):
                raise ValueError("Invalid content provided for implication generation")
            
            # Prepare metadata with defaults
            processing_metadata = metadata or {}
            processing_metadata.update({
                "processor": self.service_name,
                "content_id": content_id,
                "started_at": datetime.utcnow().isoformat(),
                "content_length": len(content)
            })
            
            # Format prompt using the prompt manager
            formatted_prompt = self.prompt_manager.format_prompt(content, processing_metadata)
            
            logger.info(f"🤖 Invoking Bedrock Agent for implications...")
            
            # Generate implications using Bedrock Agent
            result = await self.bedrock_service.generate_implications(
                prompt=formatted_prompt,
                content_id=content_id,
                metadata=processing_metadata
            )
            
            if not result or not result.get("success"):
                raise Exception(f"Failed to generate implications: {result.get('content', 'Unknown error')}")
            
            # Add processor metadata to the result
            result["processing_metadata"].update({
                "processor": self.service_name,
                "prompt_length": len(formatted_prompt),
                "completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"✅ Successfully generated implications for content: {content_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating implications for content {content_id}: {str(e)}")
            
            # Return error result with consistent structure
            return {
                "content": f"Error generating implications: {str(e)}",
                "success": False,
                "model_used": "error",
                "processing_metadata": {
                    "processor": self.service_name,
                    "content_id": content_id,
                    "error": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                }
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the processor service"""
        return {
            "service_name": self.service_name,
            "bedrock_service": "ImplicationBedrockService",
            "prompt_manager": self.prompt_manager.get_environment_info(),
            "capabilities": [
                "strategic_implications",
                "business_analysis", 
                "operational_recommendations",
                "financial_implications",
                "regulatory_analysis"
            ]
        }
    
    async def test_service(self) -> bool:
        """Test the implication generation service"""
        try:
            test_content = """
            Market Analysis: The pharmaceutical industry is experiencing significant growth 
            in personalized medicine, with increasing investment in genomic research and 
            targeted therapies. Regulatory frameworks are evolving to support innovation 
            while maintaining safety standards.
            """
            
            result = await self.generate_implications(
                content=test_content,
                content_id="test-service",
                metadata={"test_mode": True}
            )
            
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Service test failed: {str(e)}")
            return False 