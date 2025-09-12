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


class RegenerateInsightsBedrockService:
    """AWS Bedrock Agent service specifically for regenerating market insights"""
    
    def __init__(self):
        self.service_name = "Regenerate Insights Bedrock Service"
        
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
            logger.info("Creating Bedrock Agent Runtime client for regenerate insights")
            
            logger.info(f"Initializing Bedrock Agent client for agent: {self.aws_bedrock_agent_id}")
            
            self.bedrock_client = boto3.client(
                "bedrock-agent-runtime",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region,
                aws_session_token=self.aws_session_token if self.aws_session_token else None
            )
            
            logger.info(f"Successfully created Bedrock Agent client for regenerate insights: {self.aws_bedrock_agent_id}")
            
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
            session_id = f"regenerate-insights-{uuid.uuid4()}"
            
            logger.info(f"Invoking Bedrock Agent for regenerate insights - content ID: {content_id}")
            
            response = self.bedrock_client.invoke_agent(
                agentId=self.aws_bedrock_agent_id,
                agentAliasId=self.aws_bedrock_agent_alias_id,
                sessionId=session_id,
                inputText=prompt_text
            )
            
            logger.info(f"Successfully received response from Bedrock Agent for regenerate insights - content ID: {content_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock Agent for regenerate insights - content ID {content_id}: {e}")
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
                        logger.debug(f"Bedrock Agent Trace for regenerate insights {content_id}: {trace}")
        except Exception as e:
            logger.error(f"Error processing Bedrock response for regenerate insights - content ID {content_id}: {e}")
        
        return completion

    async def generate_insights(self, prompt: str, content_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate regenerated market insights using AWS Bedrock Agent or mock data"""
        try:
            logger.info(f"Generating regenerated insights for content ID: {content_id}")

            # Validate input
            if not prompt or not prompt.strip():
                raise ValueError("Prompt cannot be empty")

            if len(prompt) > 100000:  # 100KB limit
                logger.warning(f"Prompt length ({len(prompt)}) exceeds recommended limit")
                prompt = prompt[:100000] + "... [truncated]"

            # Check if mock mode is enabled
            if self.mock_mode:
                logger.info(f"Using mock mode for regenerate insights - content_id: {content_id}")
                return await self._generate_mock_insights(prompt, content_id, metadata)

            if not self.bedrock_client:
                raise Exception("Bedrock Agent client not initialized")

            # Invoke Bedrock Agent
            response = self.invoke_bedrock_agent(prompt, content_id)
            
            if not response:
                raise Exception("Failed to get response from Bedrock Agent")

            # Process streaming response
            insights = self.process_streaming_response(response, content_id)
            
            if not insights or len(insights.strip()) < 10:
                raise Exception("No meaningful content received from Bedrock Agent")

            # Add comprehensive metadata
            result = {
                "content": insights,
                "success": True,
                "model_used": f"bedrock-agent-{self.aws_bedrock_agent_id}",
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "response_length": len(insights),
                    "prompt_length": len(prompt),
                    "agent_id": self.aws_bedrock_agent_id,
                    "agent_alias_id": self.aws_bedrock_agent_alias_id,
                    "operation_type": "regenerate_insights"
                }
            }

            logger.info(f"Successfully generated regenerated insights for content ID: {content_id} ({len(insights)} characters)")
            return result

        except Exception as e:
            logger.error(f"Error generating regenerated insights for content ID {content_id}: {str(e)}")
            return {
                "content": f"Error generating regenerated insights: {str(e)}",
                "success": False,
                "model_used": f"bedrock-agent-{self.aws_bedrock_agent_id}",
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "processed_at": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "operation_type": "regenerate_insights"
                }
            }

    async def _generate_mock_insights(self, prompt: str, content_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mock regenerated insights for testing"""
        import asyncio
        await asyncio.sleep(1)  # Simulate API delay
        
        mock_insights = f"""
# Regenerated Market Insights Analysis (Mock Data)

## Executive Summary
This is a mock regenerated insight generated for testing purposes for content ID: {content_id}.
The analysis has been customized based on the user's specific requirements.

## Enhanced Market Trends & Opportunities
- Regenerated analysis shows evolving market dynamics in pharmaceutical sector
- User-specified focus areas reveal new opportunities in digital health solutions
- Regulatory landscape analysis updated based on recent developments

## Refined Competitive Landscape Analysis
- Updated competitive positioning based on user requirements
- New market entrants analysis with enhanced focus
- Strategic recommendations tailored to user specifications

## Customized Key Success Factors
- Enhanced regulatory compliance strategies
- Innovation pathways aligned with user priorities
- Strategic partnerships optimized for specific market segments

## User-Focused Recommendations
- Tailored strategic initiatives based on user input
- Customized market entry strategies
- Specific action items aligned with user requirements

*Note: This is mock regenerated data generated for testing purposes based on user input.*
"""
        
        return {
            "content": mock_insights.strip(),
            "success": True,
            "model_used": "mock-model",
            "processing_metadata": {
                "service": self.service_name,
                "content_id": content_id,
                "processed_at": datetime.utcnow().isoformat(),
                "response_length": len(mock_insights),
                "mock_mode": True,
                "operation_type": "regenerate_insights"
            }
        }
    
    def test_connection(self) -> bool:
        """Test Bedrock connection for regenerate insights"""
        try:
            if not self.bedrock_client:
                return False
            
            # Simple test call
            test_prompt = "Hello, this is a test for regenerate insights."
            result = self.generate_insights(test_prompt, "test")
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Bedrock connection test failed for regenerate insights: {str(e)}")
            return False 