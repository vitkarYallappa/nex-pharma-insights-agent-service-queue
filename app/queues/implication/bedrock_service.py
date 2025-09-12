import boto3
import json
from typing import Dict, Any
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImplicationBedrockService:
    """AWS Bedrock service for generating business implications"""
    
    def __init__(self):
        self.service_name = "Implication Bedrock Service"
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"  # Claude 3 Sonnet
        
        # Initialize Bedrock client
        try:
            self.bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name='us-east-1'  # Adjust region as needed
            )
            logger.info("Initialized Bedrock client for implications")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            self.bedrock_client = None
    
    def generate_implications(self, prompt: str, content_id: str = "") -> Dict[str, Any]:
        """Generate business implications using AWS Bedrock"""
        try:
            if not self.bedrock_client:
                raise Exception("Bedrock client not initialized")
            
            logger.info(f"💡 BEDROCK IMPLICATIONS - Content ID: {content_id} | Calling Bedrock for business implications")
            
            # Prepare the request body for Claude 3
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if response_body.get('content') and len(response_body['content']) > 0:
                implications_content = response_body['content'][0]['text']
                
                logger.info(f"✅ BEDROCK IMPLICATIONS SUCCESS - Content ID: {content_id} | Generated {len(implications_content)} characters")
                
                return {
                    "content": implications_content,
                    "success": True,
                    "model_used": self.model_id,
                    "processing_metadata": {
                        "service": self.service_name,
                        "content_id": content_id,
                        "processed_at": datetime.utcnow().isoformat(),
                        "response_length": len(implications_content),
                        "tokens_used": response_body.get('usage', {}).get('output_tokens', 0)
                    }
                }
            else:
                raise Exception("No content in Bedrock response")
                
        except Exception as e:
            logger.error(f"❌ BEDROCK IMPLICATIONS ERROR - Content ID: {content_id} | Error calling Bedrock: {str(e)}")
            return {
                "content": f"Error generating implications: {str(e)}",
                "success": False,
                "model_used": self.model_id,
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
            }
    
    def test_connection(self) -> bool:
        """Test Bedrock connection"""
        try:
            if not self.bedrock_client:
                return False
            
            # Simple test call
            test_prompt = "Hello, this is a test."
            result = self.generate_implications(test_prompt, "test")
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {str(e)}")
            return False
