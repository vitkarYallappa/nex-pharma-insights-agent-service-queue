import boto3
import uuid
from typing import Dict, Any, Optional

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class RegenerateInsightsBedrockService:
    """Simple AWS Bedrock service for processing text input"""
    
    def __init__(self):
        # Bedrock configuration
        self.aws_bedrock_agent_id = settings.BEDROCK_AWS_BEDROCK_AGENT_ID or "B7TOHQ5N03"
        self.aws_bedrock_agent_alias_id = settings.BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID or "KOINO4TU2J"
        self.aws_region = settings.BEDROCK_AWS_REGION or "us-east-1"
        
        # Bedrock credentials
        self.aws_access_key_id = settings.BEDROCK_AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = settings.BEDROCK_AWS_SECRET_ACCESS_KEY
        self.aws_session_token = settings.BEDROCK_AWS_SESSION_TOKEN
        
        self.mock_mode = settings.BEDROCK_MOCK_MODE
        
        # Initialize Bedrock client
        self.bedrock_client = None
        if not self.mock_mode:
            self._create_bedrock_client()
    
    def _create_bedrock_client(self):
        """Create Bedrock client"""
        try:
            self.bedrock_client = boto3.client(
                "bedrock-agent-runtime",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region,
                aws_session_token=self.aws_session_token if self.aws_session_token else None
            )
            logger.info("Bedrock client created successfully")
        except Exception as e:
            logger.error(f"Error creating Bedrock client: {e}")
            self.bedrock_client = None

    async def generate_insights(self, prompt: str, content_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate insights using Bedrock or mock data"""
        try:
            if not prompt or not prompt.strip():
                raise ValueError("Prompt cannot be empty")

            # Mock mode
            if self.mock_mode:
                return await self._generate_mock_insights(prompt, content_id)

            # Real Bedrock call
            if not self.bedrock_client:
                raise Exception("Bedrock client not initialized")

            session_id = f"session-{uuid.uuid4()}"
            
            response = self.bedrock_client.invoke_agent(
                agentId=self.aws_bedrock_agent_id,
                agentAliasId=self.aws_bedrock_agent_alias_id,
                sessionId=session_id,
                inputText=prompt
            )
            
            # Process response
            content = ""
            if 'completion' in response:
                for event in response['completion']:
                    if 'chunk' in event and 'bytes' in event['chunk']:
                        content += event['chunk']['bytes'].decode('utf-8')
            
            if not content:
                raise Exception("No content received from Bedrock")

            return {
                "content": content,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return {
                "content": f"Error: {str(e)}",
                "success": False
            }

    async def _generate_mock_insights(self, prompt: str, content_id: str) -> Dict[str, Any]:
        """Generate mock insights for testing"""
        import asyncio
        await asyncio.sleep(1)  # Simulate delay
        
        mock_content = f"""
# Mock Insights Response

This is a mock response for content ID: {content_id}

## Analysis
Based on your input text, here are the generated insights:
- Mock insight point 1
- Mock insight point 2  
- Mock insight point 3

## Summary
This is mock data for testing purposes.
"""
        
        return {
            "content": mock_content.strip(),
            "success": True
        } 