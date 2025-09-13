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


class ImplicationBedrockService:
    """AWS Bedrock Agent service for generating market implications"""
    
    def __init__(self):
        self.service_name = "Implication Bedrock Agent Service"
        
        # Bedrock Agent configuration - using settings from config
        self.aws_bedrock_agent_id = settings.BEDROCK_AWS_BEDROCK_AGENT_ID or "B7TOHQ5N03"
        self.aws_bedrock_agent_alias_id = settings.BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID or "KOINO4TU2J"
        self.aws_region = settings.BEDROCK_AWS_REGION or "us-east-1"
        
        # Bedrock AWS Credentials - using settings from config
        self.aws_access_key_id = settings.BEDROCK_AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = settings.BEDROCK_AWS_SECRET_ACCESS_KEY
        self.aws_session_token = settings.BEDROCK_AWS_SESSION_TOKEN
        
        # Validate credentials are loaded
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            logger.error("❌ BEDROCK CREDENTIALS MISSING - Check your .env file for BEDROCK_AWS_ACCESS_KEY_ID and BEDROCK_AWS_SECRET_ACCESS_KEY")
            
            # Try manual fallback loading from .env file
            manual_creds = self._load_credentials_manually()
            if manual_creds:
                logger.info("✅ Manual credential loading successful")
                self.aws_access_key_id = manual_creds.get('access_key')
                self.aws_secret_access_key = manual_creds.get('secret_key')
                self.aws_session_token = manual_creds.get('session_token')
                self.aws_bedrock_agent_id = manual_creds.get('agent_id', self.aws_bedrock_agent_id)
                self.aws_bedrock_agent_alias_id = manual_creds.get('agent_alias', self.aws_bedrock_agent_alias_id)
            else:
                logger.error("❌ Failed to load Bedrock credentials")
        
        self.mock_mode = settings.BEDROCK_MOCK_MODE  # Use settings for mock mode
        
        # Initialize Bedrock Agent client
        self.bedrock_client = None
        self._create_bedrock_client()
    
    def _load_credentials_manually(self) -> Optional[Dict[str, str]]:
        """Manually load Bedrock credentials from .env file as fallback"""
        try:
            from pathlib import Path
            
            # Look for .env file in multiple locations
            env_locations = [".env", "../.env", "../../.env"]
            for env_path in env_locations:
                env_file = Path(env_path)
                if env_file.exists():
                    credentials = {}
                    with open(env_file, 'r') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")  # Remove quotes
                                
                                if key == 'BEDROCK_AWS_ACCESS_KEY_ID':
                                    credentials['access_key'] = value
                                elif key == 'BEDROCK_AWS_SECRET_ACCESS_KEY':
                                    credentials['secret_key'] = value
                                elif key == 'BEDROCK_AWS_SESSION_TOKEN':
                                    credentials['session_token'] = value
                                elif key == 'BEDROCK_AWS_BEDROCK_AGENT_ID':
                                    credentials['agent_id'] = value
                                elif key == 'BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID':
                                    credentials['agent_alias'] = value
                    
                    if credentials.get('access_key') and credentials.get('secret_key'):
                        return credentials
                    
            return None
            
        except Exception as e:
            logger.error(f"Error loading credentials manually: {e}")
            return None
    
    def _create_bedrock_client(self):
        """Create and return a Bedrock Agent Runtime client - using your exact working pattern"""
        try:
            logger.info("Creating Bedrock Agent Runtime client for implications")
            logger.info(f"Initializing Bedrock Agent client for agent: {self.aws_bedrock_agent_id}")
            
            # Check if we have explicit credentials
            if self.aws_access_key_id and self.aws_secret_access_key and \
               self.aws_access_key_id not in ["local", "dummy", "test"] and \
               self.aws_secret_access_key not in ["local", "dummy", "test"]:
                # Use explicit credentials (for local development)
                self.bedrock_client = boto3.client(
                    "bedrock-agent-runtime",
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.aws_region,
                    aws_session_token=self.aws_session_token if self.aws_session_token else None
                )
            else:
                # Use default credential chain (IAM instance role, environment variables, etc.)
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

    async def generate_implications(self, prompt: str, content_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate market implications using AWS Bedrock Agent or mock data"""
        try:
            logger.info(f"Generating implications for content ID: {content_id}")

            # Validate input
            if not prompt or not prompt.strip():
                raise ValueError("Prompt cannot be empty")

            if len(prompt) > 100000:  # 100KB limit
                logger.warning(f"Prompt length ({len(prompt)}) exceeds recommended limit")
                prompt = prompt[:100000] + "... [truncated]"

            # Check if mock mode is enabled
            if self.mock_mode:
                logger.info(f"Using mock mode for content_id: {content_id}")
                return await self._generate_mock_implications(prompt, content_id, metadata)

            if not self.bedrock_client:
                raise Exception("Bedrock Agent client not initialized")

            # Invoke Bedrock Agent - using your exact working pattern
            response = self.invoke_bedrock_agent(prompt, content_id)
            
            if not response:
                raise Exception("Failed to get response from Bedrock Agent")

            # Process streaming response - using your exact working pattern
            implications = self.process_streaming_response(response, content_id)
            
            if not implications or len(implications.strip()) < 10:
                raise Exception("No meaningful content received from Bedrock Agent")

            # Add comprehensive metadata
            result = {
                "content": implications,
                "success": True,
                "model_used": f"bedrock-agent-{self.aws_bedrock_agent_id}",
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "response_length": len(implications),
                    "prompt_length": len(prompt),
                    "agent_id": self.aws_bedrock_agent_id,
                    "agent_alias_id": self.aws_bedrock_agent_alias_id
                }
            }

            logger.info(f"Successfully generated implications for content ID: {content_id} ({len(implications)} characters)")
            return result

        except Exception as e:
            logger.error(f"Error generating implications for content ID {content_id}: {str(e)}")
            return {
                "content": f"Error generating implications: {str(e)}",
                "success": False,
                "model_used": f"bedrock-agent-{self.aws_bedrock_agent_id}",
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
            }



    async def _generate_mock_implications(self, prompt: str, content_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mock implications for testing"""
        import asyncio
        await asyncio.sleep(1)  # Simulate API delay
        
        mock_implications = f"""
# Strategic Implications Analysis (Mock Data)

## Executive Summary
This is a mock implication analysis generated for testing purposes for content ID: {content_id}.

## Strategic Business Implications
- Market positioning opportunities require immediate attention
- Competitive advantages can be leveraged through strategic partnerships
- Regulatory compliance presents both challenges and opportunities

## Operational Implications
- Resource allocation needs optimization for maximum efficiency
- Technology infrastructure requires strategic upgrades
- Workforce development programs should be prioritized

## Financial Implications
- Investment opportunities identified in emerging market segments
- Cost optimization strategies can improve profit margins
- Risk management protocols need enhancement

## Long-term Strategic Recommendations
- Develop comprehensive market entry strategies
- Establish strategic alliances with key industry players
- Invest in innovation and R&D capabilities

*Note: This is mock data generated for testing purposes.*
"""
        
        return {
            "content": mock_implications.strip(),
            "success": True,
            "model_used": "mock-model",
            "processing_metadata": {
                "service": self.service_name,
                "content_id": content_id,
                "processed_at": datetime.utcnow().isoformat(),
                "response_length": len(mock_implications),
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
            result = self.generate_implications(test_prompt, "test")
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {str(e)}")
            return False 