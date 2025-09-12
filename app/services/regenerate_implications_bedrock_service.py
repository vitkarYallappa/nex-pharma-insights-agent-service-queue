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


class RegenerateImplicationsBedrockService:
    """AWS Bedrock Agent service specifically for regenerating market implications"""
    
    def __init__(self):
        self.service_name = "Regenerate Implications Bedrock Service"
        
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
        """Create and return a Bedrock Agent Runtime client"""
        try:
            logger.info("Creating Bedrock Agent Runtime client for regenerate implications")
            logger.info(f"Initializing Bedrock Agent client for agent: {self.aws_bedrock_agent_id}")
            
            self.bedrock_client = boto3.client(
                "bedrock-agent-runtime",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region,
                aws_session_token=self.aws_session_token if self.aws_session_token else None
            )
            
            logger.info(f"Successfully created Bedrock Agent client for regenerate implications: {self.aws_bedrock_agent_id}")
            
        except Exception as e:
            logger.error(f"Error creating Bedrock Agent client: {e}")
            self.bedrock_client = None
            raise
    
    def invoke_bedrock_agent(self, prompt_text: str, content_id: str = "") -> Optional[Dict[str, Any]]:
        """Invoke the Bedrock agent with the given prompt"""
        try:
            if not self.bedrock_client:
                raise Exception("Bedrock Agent client not initialized")
            
            # Generate unique session ID for regeneration
            session_id = f"regenerate-implications-{uuid.uuid4()}"
            
            logger.info(f"Invoking Bedrock Agent for regenerate implications - content ID: {content_id}")
            
            response = self.bedrock_client.invoke_agent(
                agentId=self.aws_bedrock_agent_id,
                agentAliasId=self.aws_bedrock_agent_alias_id,
                sessionId=session_id,
                inputText=prompt_text
            )
            
            logger.info(f"Successfully received response from Bedrock Agent for regenerate implications - content ID: {content_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock Agent for regenerate implications - content ID {content_id}: {e}")
            return None

    def process_streaming_response(self, response: Dict[str, Any], content_id: str = "") -> str:
        """Process the streaming response from Bedrock agent"""
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
                        logger.debug(f"Bedrock Agent Trace for regenerate implications {content_id}: {trace}")
        except Exception as e:
            logger.error(f"Error processing Bedrock response for regenerate implications - content ID {content_id}: {e}")
        
        return completion

    async def generate_implications(self, prompt: str, content_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate regenerated market implications using AWS Bedrock Agent or mock data"""
        try:
            logger.info(f"Generating regenerated implications for content ID: {content_id}")

            # Validate input
            if not prompt or not prompt.strip():
                raise ValueError("Prompt cannot be empty")

            if len(prompt) > 100000:  # 100KB limit
                logger.warning(f"Prompt length ({len(prompt)}) exceeds recommended limit")
                prompt = prompt[:100000] + "... [truncated]"

            # Check if mock mode is enabled
            if self.mock_mode:
                logger.info(f"Using mock mode for regenerate implications - content_id: {content_id}")
                return await self._generate_mock_implications(prompt, content_id, metadata)

            if not self.bedrock_client:
                raise Exception("Bedrock Agent client not initialized")

            # Invoke Bedrock Agent
            response = self.invoke_bedrock_agent(prompt, content_id)
            
            if not response:
                raise Exception("Failed to get response from Bedrock Agent")

            # Process streaming response
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
                    "agent_alias_id": self.aws_bedrock_agent_alias_id,
                    "operation_type": "regenerate_implications"
                }
            }

            logger.info(f"Successfully generated regenerated implications for content ID: {content_id} ({len(implications)} characters)")
            return result

        except Exception as e:
            logger.error(f"Error generating regenerated implications for content ID {content_id}: {str(e)}")
            return {
                "content": f"Error generating regenerated implications: {str(e)}",
                "success": False,
                "model_used": f"bedrock-agent-{self.aws_bedrock_agent_id}",
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "operation_type": "regenerate_implications"
                }
            }

    async def _generate_mock_implications(self, prompt: str, content_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mock regenerated implications for testing"""
        import asyncio
        await asyncio.sleep(1)  # Simulate API delay
        
        mock_implications = f"""
# Regenerated Strategic Implications Analysis (Mock Data)

## Executive Summary
This is a mock regenerated implication analysis generated for testing purposes for content ID: {content_id}.
The strategic analysis has been customized based on the user's specific requirements and focus areas.

## Enhanced Strategic Business Implications
- Regenerated market positioning opportunities tailored to user specifications
- Competitive advantages refined based on user input requirements
- Strategic partnerships aligned with user-defined priorities
- Market entry strategies customized for specific user focus areas

## Refined Operational Implications
- Resource allocation recommendations optimized for user requirements
- Process optimization opportunities enhanced based on user feedback
- Technology infrastructure needs aligned with user strategic goals
- Organizational capability requirements tailored to user specifications

## Customized Financial Implications
- Investment opportunities refined based on user priorities
- Cost optimization strategies aligned with user focus areas
- Revenue enhancement opportunities customized for user requirements
- Risk management considerations enhanced based on user input

## User-Focused Regulatory & Compliance Implications
- Regulatory compliance requirements tailored to user specifications
- Policy change impacts analyzed based on user priorities
- Risk mitigation strategies customized for user requirements

## Personalized Long-term Strategic Recommendations
- Strategic priorities aligned with user-defined timeframes
- Innovation and R&D focus areas based on user requirements
- Market positioning strategies customized for user specifications
- Competitive differentiation approaches tailored to user input

*Note: This is mock regenerated data generated for testing purposes based on user input.*
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
                "mock_mode": True,
                "operation_type": "regenerate_implications"
            }
        }
    
    def test_connection(self) -> bool:
        """Test Bedrock connection for regenerate implications"""
        try:
            if not self.bedrock_client:
                return False
            
            # Simple test call
            test_prompt = "Hello, this is a test for regenerate implications."
            result = self.generate_implications(test_prompt, "test")
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Bedrock connection test failed for regenerate implications: {str(e)}")
            return False 