import boto3
import json
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from botocore.exceptions import NoCredentialsError

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class RelevanceCheckBedrockService:
    """AWS Bedrock Agent service for generating relevance check analysis"""
    
    def __init__(self):
        self.service_name = "Relevance Check Bedrock Agent Service"
        
        # Bedrock Agent configuration
        self.aws_bedrock_agent_id = settings.BEDROCK_AWS_BEDROCK_AGENT_ID or "ZHNPJSVGDE"
        self.aws_bedrock_agent_alias_id = settings.BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID or "KOINO4TU2J"
        self.aws_region = settings.BEDROCK_AWS_REGION or "us-east-1"
        
        # Global environment setting
        self.global_environment = getattr(settings, 'GLOBAL_ENVIRONMENT', 'local')
        
        # Bedrock AWS Credentials (for local development)
        self.aws_access_key_id = settings.BEDROCK_AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = settings.BEDROCK_AWS_SECRET_ACCESS_KEY
        self.aws_session_token = settings.BEDROCK_AWS_SESSION_TOKEN
        
        # Mock mode setting
        self.mock_mode = settings.BEDROCK_MOCK_MODE
        
        # Initialize Bedrock Agent client
        self.bedrock_client = None
        self._create_bedrock_client()

    
    def _create_bedrock_client(self):
        """Create Bedrock Agent Runtime client based on GLOBAL_ENVIRONMENT setting"""
        try:
            logger.info("Creating Bedrock Agent Runtime client for relevance check")
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
            
            logger.info(f"Successfully created Bedrock Agent client for agent: {self.aws_bedrock_agent_id}")
            
        except Exception as e:
            logger.error(f"Error creating Bedrock Agent client: {e}")
            self.bedrock_client = None
            raise
    
    def invoke_bedrock_agent(self, prompt_text: str, content_id: str = "") -> Optional[Dict[str, Any]]:
        """Invoke the Bedrock agent with the given prompt - using your exact working pattern"""
        try:
            if not self.bedrock_client:
                raise Exception("Bedrock Agent client not initialized")
            
            # Generate unique session ID
            session_id = f"session-{uuid.uuid4()}"
            
            logger.info(f"Invoking Bedrock Agent for content ID: {content_id}")
            
            response = self.bedrock_client.invoke_agent(
                agentId=self.aws_bedrock_agent_id,
                agentAliasId=self.aws_bedrock_agent_alias_id,
                sessionId=session_id,
                inputText=prompt_text
            )
            
            logger.info(f"Successfully received response from Bedrock Agent for content ID: {content_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock Agent for content ID {content_id}: {e}")
            return None

    def process_streaming_response(self, response: Dict[str, Any], content_id: str = "") -> str:
        """Process the streaming response from Bedrock agent - using your exact working pattern"""
        completion = ""
        
        try:
            if 'completion' in response:
                for event in response['completion']:
                    if 'chunk' in event:
                        chunk = event['chunk']
                        if 'bytes' in chunk:
                            completion += chunk['bytes'].decode('utf-8')
                    elif 'trace' in event:
                        # Optional: Handle trace events for debugging
                        trace = event['trace']
                        logger.debug(f"Bedrock Agent Trace for {content_id}: {trace}")
        except Exception as e:
            logger.error(f"Error processing Bedrock response for content ID {content_id}: {e}")
        
        return completion

    async def check_relevance(self, prompt: str, content_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Check content relevance using AWS Bedrock Agent or mock data"""
        try:
            logger.info(f"Checking relevance for content ID: {content_id}")

            # Validate input
            if not prompt or not prompt.strip():
                raise ValueError("Prompt cannot be empty")

            if len(prompt) > 100000:  # 100KB limit
                logger.warning(f"Prompt length ({len(prompt)}) exceeds recommended limit")
                prompt = prompt[:100000] + "... [truncated]"

            # Check if mock mode is enabled
            if self.mock_mode:
                logger.info(f"Using mock mode for content_id: {content_id}")
                return await self._generate_mock_relevance_check(prompt, content_id, metadata)

            if not self.bedrock_client:
                raise Exception("Bedrock Agent client not initialized")

            # Invoke Bedrock Agent - using your exact working pattern
            response = self.invoke_bedrock_agent(prompt, content_id)
            
            if not response:
                raise Exception("Failed to get response from Bedrock Agent")

            # Process streaming response - using your exact working pattern
            relevance_analysis = self.process_streaming_response(response, content_id)
            
            if not relevance_analysis or len(relevance_analysis.strip()) < 10:
                raise Exception("No meaningful content received from Bedrock Agent")

            # Add comprehensive metadata
            result = {
                "content": relevance_analysis,
                "success": True,
                "model_used": f"bedrock-agent-{self.aws_bedrock_agent_id}",
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "response_length": len(relevance_analysis),
                    "prompt_length": len(prompt),
                    "agent_id": self.aws_bedrock_agent_id,
                    "agent_alias_id": self.aws_bedrock_agent_alias_id
                }
            }

            logger.info(f"Successfully checked relevance for content ID: {content_id} ({len(relevance_analysis)} characters)")
            return result

        except Exception as e:
            logger.error(f"Error checking relevance for content ID {content_id}: {str(e)}")
            return {
                "content": f"Error checking relevance: {str(e)}",
                "success": False,
                "model_used": f"bedrock-agent-{self.aws_bedrock_agent_id}",
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
            }



    async def _generate_mock_relevance_check(self, prompt: str, content_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mock relevance check for testing"""
        import asyncio
        await asyncio.sleep(1)  # Simulate API delay
        
        mock_relevance = f"""
# Relevance Check Analysis (Mock Data)

## Content Relevance Assessment
This is a mock relevance check generated for testing purposes for content ID: {content_id}.

**Relevance Decision: YES**
**Relevance Score: 85/100**

## Key Relevance Indicators
- Contains pharmaceutical industry content
- Market intelligence elements present
- Regulatory information identified
- Competitive landscape data found

## Analysis Summary
- **Pharmaceutical Relevance**: High - Contains drug development and regulatory content
- **Market Intelligence Value**: High - Includes market analysis and competitive data
- **Query Alignment**: Good - Content aligns with user requirements

*Note: This is mock data generated for testing purposes.*
"""
        
        return {
            "content": mock_relevance.strip(),
            "success": True,
            "model_used": "mock-model",
            "processing_metadata": {
                "service": self.service_name,
                "content_id": content_id,
                "processed_at": datetime.utcnow().isoformat(),
                "response_length": len(mock_relevance),
                "mock_mode": True
            }
        }
    
    def test_connection(self) -> bool:
        """Test Bedrock connection"""
        try:
            if not self.bedrock_client:
                return False
            
            # Simple test call
            test_prompt = "Hello, this is a test."
            result = self.check_relevance(test_prompt, "test")
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {str(e)}")
            return False 