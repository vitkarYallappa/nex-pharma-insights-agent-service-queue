import boto3
import uuid
from typing import Dict, Any, Optional

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class RegenerateImplicationsBedrockService:
    """Simple AWS Bedrock service for processing text input"""
    
    def __init__(self):
        # Bedrock configuration
        self.aws_bedrock_agent_id = settings.BEDROCK_AWS_BEDROCK_AGENT_ID or "ZHNPJSVGDE"
        self.aws_bedrock_agent_alias_id = settings.BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID or "KOINO4TU2J"
        self.aws_region = settings.BEDROCK_AWS_REGION or "us-east-1"
        
        # Global environment setting
        self.global_environment = getattr(settings, 'GLOBAL_ENVIRONMENT', 'local')
        
        # Bedrock credentials (for local development)
        self.aws_access_key_id = settings.BEDROCK_AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = settings.BEDROCK_AWS_SECRET_ACCESS_KEY
        self.aws_session_token = settings.BEDROCK_AWS_SESSION_TOKEN
        
        self.mock_mode = settings.BEDROCK_MOCK_MODE
        
        # Initialize Bedrock client
        self.bedrock_client = None
        if not self.mock_mode:
            self._create_bedrock_client()
    
    def _create_bedrock_client(self):
        """Create Bedrock client based on GLOBAL_ENVIRONMENT setting"""
        try:
            logger.info(f"Global environment: {self.global_environment}")
            
            if self.global_environment.lower() == 'local':
                # Local development - use explicit credentials
                logger.info("Using local environment setup with explicit credentials")
                self.bedrock_client = boto3.client(
                    "bedrock-agent-runtime",
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    aws_session_token=self.aws_session_token,
                    region_name=self.aws_region
                )
            elif self.global_environment.lower() == 'ec2':
                # EC2 environment - use IAM role
                logger.info("Using EC2 environment setup with IAM role")
                self.bedrock_client = boto3.client(
                    "bedrock-agent-runtime",
                    region_name=self.aws_region
                )
            else:
                # Default fallback - use global environment setup
                logger.info(f"Using default environment setup for: {self.global_environment}")
                self.bedrock_client = boto3.client(
                    "bedrock-agent-runtime",
                    region_name=self.aws_region
                )
            
            logger.info("Bedrock client created successfully")
        except Exception as e:
            logger.error(f"Error creating Bedrock client: {e}")
            self.bedrock_client = None

    async def generate_implications(self, prompt: str, content_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate implications using Bedrock or mock data"""
        try:
            if not prompt or not prompt.strip():
                raise ValueError("Prompt cannot be empty")

            # Mock mode
            if self.mock_mode:
                return await self._generate_mock_implications(prompt, content_id)

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
            logger.error(f"Error generating implications: {str(e)}")
            return {
                "content": f"Error: {str(e)}",
                "success": False
            }

    async def _generate_mock_implications(self, prompt: str, content_id: str) -> Dict[str, Any]:
        """Generate mock implications for testing"""
        import asyncio
        await asyncio.sleep(1)  # Simulate delay
        
        mock_content = f"""
# Mock Implications Response

This is a mock response for content ID: {content_id}

## Strategic Analysis
Based on your input text, here are the generated implications:
- Mock implication point 1
- Mock implication point 2  
- Mock implication point 3

## Business Impact
This is mock data for testing purposes.
"""
        
        return {
            "content": mock_content.strip(),
            "success": True
        } 