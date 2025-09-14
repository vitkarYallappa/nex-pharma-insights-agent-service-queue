"""
Database Operations Service for Relevance Check Queue
Handles DynamoDB operations for content_relevance table
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid

from boto3.dynamodb.conditions import Attr

from app.database.dynamodb_client import dynamodb_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default KITs and KIQs content for fallback scenarios
DEFAULT_KITS_KIQS_CONTENT = """KITs

Competitor Pipeline & Clinical Development
Trial initiations, readouts, delays, regulatory submissions, approvals, or setbacks.

Market Access & Pricing
Payer decisions, formulary updates, HTA reviews, price changes, reimbursement news.

Commercial & Marketing Strategy
New campaigns, brand positioning, DTC/physician outreach, partnerships.

Regulatory & Policy Landscape
Guideline updates, new regulations, safety warnings, black box labels.

Launch Activities & Timelines
Launch milestones, territory expansions, stocking reports, early adoption metrics.

Mergers, Acquisitions, and Partnerships
Alliances, licensing deals, co-commercialization, distribution partnerships.

HCP Engagement & Advocacy
KOL activities, advisory boards, guideline influence, publications, speaking events.

Scientific & Innovation Trends
Novel MOAs, platform technologies, biomarker strategies, competitor R&D focus.

Patient Advocacy & Sentiment
Patient group activity, social sentiment, advocacy campaigns.

Manufacturing & Supply Chain
Production capacity, shortages, recalls, manufacturing investments.


KIQs: Market & Competitive Landscape
What are competitors' near-term and long-term launch timelines?
What new trial data or regulatory updates could disrupt our market positioning?
Are there emerging players or startups targeting our indication?

Access & Pricing
Are there payer decisions or HTA outcomes that could affect uptake?
Is there evidence of pricing pressure or innovative pricing models (outcomes-based, etc.)?

Commercial Execution
How are competitors differentiating their messaging and branding?
Are there new channels or campaigns being tested (digital, omnichannel, etc.)?

Medical Affairs & Evidence
Which KOLs are influencing guidelines or prescribing?
Are there shifts in clinical practice guidelines?

Policy & Regulatory
Are there regulatory shifts that may accelerate or delay market entry?
Is there increased scrutiny on safety, manufacturing, or supply?

Innovation & Pipeline
Are new MOAs or platforms being developed that threaten our assets?
What's the scientific differentiation strategy competitors are pursuing?

Operational & Corporate
Are M&A or licensing moves signaling a shift in strategy?
Is manufacturing capacity becoming a bottleneck or strength for competitors?"""


class RelevanceCheckDBOperationsService:
    """Service to handle DynamoDB operations for Relevance Check results"""
    
    def __init__(self):
        self.service_name = "Relevance Check DB Operations Service"
        # DynamoDB table name
        self.content_relevance_table = "content_relevance"
    
    def process_relevance_completion(self, relevance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Relevance Check completion and store data in content_relevance table
        
        Args:
            relevance_data: Complete Relevance Check processing result
            
        Returns:
            Dict with operation results
        """
        try:
            logger.info(f"Processing Relevance Check completion for DynamoDB operations")
            
            # Extract key information
            content_id = relevance_data.get('content_id')
            project_id = relevance_data.get('project_id')
            request_id = relevance_data.get('request_id')
            relevance_response = relevance_data.get('relevance_response', '')
            url_data = relevance_data.get('url_data', {})
            
            if not content_id:
                raise ValueError("Missing content_id")
            if not project_id or not request_id:
                raise ValueError("Missing project_id or request_id")

            logger.info(f"🔍 RELEVANCE DB OPERATIONS - Content ID: {content_id} | Storing relevance data")
            
            # Store in content_relevance table
            result = self._store_content_relevance(relevance_data, content_id)
            
            processing_result = {
                'content_relevance_result': result,
                'processing_metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'service': self.service_name,
                    'content_id': content_id,
                    'project_id': project_id,
                    'request_id': request_id,
                    'table_processed': self.content_relevance_table
                }
            }
            
            if result.get('success'):
                logger.info(f"✅ RELEVANCE DB SUCCESS - Content ID: {content_id} | Successfully stored relevance data")
            else:
                logger.error(f"❌ RELEVANCE DB FAILED - Content ID: {content_id} | Failed to store relevance data")
            
            return processing_result
            
        except Exception as e:
            logger.error(f"❌ RELEVANCE DB ERROR - Content ID: {relevance_data.get('content_id', 'Unknown')} | Error processing relevance completion: {str(e)}")
            return {
                'error': str(e),
                'processing_metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'service': self.service_name,
                    'content_id': relevance_data.get('content_id', 'Unknown'),
                    'status': 'error'
                }
            }
    
    def _store_content_relevance(self, relevance_data: Dict[str, Any], content_id: str) -> Dict[str, Any]:
        """
        Store data in content_relevance table
        
        Args:
            relevance_data: Relevance Check processing result
            content_id: Content ID from perplexity processing
            
        Returns:
            Dict with operation result
        """
        try:
            project_id = relevance_data.get('project_id')
            request_id = relevance_data.get('request_id')
            relevance_response = relevance_data.get('relevance_response', '')
            url_data = relevance_data.get('url_data', {})
            s3_relevance_key = relevance_data.get('s3_relevance_key', '')
            processing_metadata = relevance_data.get('processing_metadata', {})
            
            # Create content relevance item matching the provided structure
            now = datetime.utcnow().isoformat()
            relevance_pk = str(uuid.uuid4())
            
            # Generate relevance content file path
            relevance_content_file_path = f"relevance/{project_id}/{request_id}/{content_id}/relevance.json"
            
            # Determine relevance category based on content analysis
            relevance_category = self._determine_relevance_category(relevance_response, url_data)
            
            # Calculate confidence score based on processing quality
            confidence_score = self._calculate_confidence_score(relevance_data)
            
            # Extract relevance score from analysis
            relevance_score = self._extract_relevance_score(relevance_response)
            
            # Determine if content is relevant based on score and analysis
            is_relevant = self._determine_is_relevant(relevance_response, relevance_score)

            update_confidence_score = f"{confidence_score}"
            content_relevance_item = {
                'pk': relevance_pk,
                'url_id': content_id,  # Using content_id as url_id for linking
                'content_id': content_id,
                'relevance_text': relevance_response,
                'relevance_score': relevance_score,
                'is_relevant': is_relevant,
                'relevance_content_file_path': relevance_content_file_path,
                'relevance_category': relevance_category,
                'confidence_score': update_confidence_score,
                'version': 1,
                'is_canonical': True,
                'preferred_choice': True,
                'created_at': now,
                'created_by': 'relevance_check_service'
            }
            
            # Store in DynamoDB
            success = dynamodb_client.put_item(self.content_relevance_table, content_relevance_item)
            
            if success:
                logger.info(f"✅ RELEVANCE DB STORED - Content ID: {content_id} | Stored relevance item: {relevance_pk} | Score: {relevance_score:.2f} | Relevant: {is_relevant}")
                return {
                    'success': True,
                    'table_name': self.content_relevance_table,
                    'item_key': relevance_pk,
                    'content_id': content_id,
                    'relevance_category': relevance_category,
                    'relevance_score': relevance_score,
                    'is_relevant': is_relevant,
                    'confidence_score': update_confidence_score,
                    'message': 'Content relevance data stored successfully'
                }
            else:
                raise Exception("Failed to store item in DynamoDB")
                
        except Exception as e:
            logger.error(f"❌ RELEVANCE DB ERROR - Content ID: {content_id} | Error storing content relevance: {str(e)}")
            return {
                'success': False,
                'table_name': self.content_relevance_table,
                'content_id': content_id,
                'error': str(e)
            }
    
    def _determine_relevance_category(self, relevance_response: str, url_data: Dict[str, Any]) -> str:
        """Determine relevance category based on content analysis"""
        try:
            if not relevance_response:
                return "general"
            
            analysis_lower = relevance_response.lower()
            
            # High relevance indicators
            if any(term in analysis_lower for term in ['high relevance', 'highly relevant', 'very relevant']):
                return "high_relevance"
            
            # Pharmaceutical relevance
            pharma_terms = ['pharmaceutical', 'drug', 'medicine', 'clinical', 'fda']
            if any(term in analysis_lower for term in pharma_terms):
                return "pharmaceutical"
            
            # Market relevance
            market_terms = ['market', 'competitive', 'revenue', 'sales', 'growth']
            if any(term in analysis_lower for term in market_terms):
                return "market_intelligence"
            
            # Regulatory relevance
            regulatory_terms = ['regulatory', 'compliance', 'approval', 'guideline']
            if any(term in analysis_lower for term in regulatory_terms):
                return "regulatory"
            
            # Low relevance indicators
            if any(term in analysis_lower for term in ['low relevance', 'not relevant', 'limited relevance']):
                return "low_relevance"
            
            return "general"
            
        except Exception:
            return "general"
    
    def _calculate_confidence_score(self, relevance_data: Dict[str, Any]) -> float:
        """Calculate confidence score for the relevance data"""
        try:
            score = 0.0
            
            # Base score for having relevance response
            if relevance_data.get('relevance_response'):
                score += 0.3
            
            # Processing success
            if relevance_data.get('relevance_success', False):
                score += 0.3
            
            # Processing metadata quality
            processing_metadata = relevance_data.get('processing_metadata', {})
            if processing_metadata.get('bedrock_model'):
                score += 0.1
            
            # URL data quality
            url_data = relevance_data.get('url_data', {})
            if url_data.get('title'):
                score += 0.05
            if url_data.get('url'):
                score += 0.05
            
            # S3 storage success
            if relevance_data.get('s3_relevance_key'):
                score += 0.1
            
            return min(1.0, score)
            
        except Exception:
            return 0.5  # Default medium confidence
    
    def _extract_relevance_score(self, relevance_response: str) -> float:
        """Extract relevance score from Bedrock response"""
        try:
            if not relevance_response:
                return 0.0
            
            analysis_lower = relevance_response.lower()
            
            # Look for explicit score patterns
            import re
            
            # Pattern 1: "relevance score: 85/100" or "score: 85"
            score_patterns = [
                r'relevance score[:\s]*(\d+)(?:/100)?',
                r'score[:\s]*(\d+)(?:/100)?',
                r'(\d+)/100',
                r'(\d+)%'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, analysis_lower)
                if match:
                    score = int(match.group(1))
                    return min(1.0, score / 100.0)  # Convert to 0.0-1.0 range
            
            # Pattern 2: Look for decimal scores like "0.85" or "0.9"
            decimal_match = re.search(r'(?:score|relevance)[:\s]*([0-1]\.\d+)', analysis_lower)
            if decimal_match:
                return float(decimal_match.group(1))
            
            # Fallback: Analyze text for relevance indicators
            if any(term in analysis_lower for term in ['highly relevant', 'very relevant', 'extremely relevant']):
                return 0.9
            elif any(term in analysis_lower for term in ['relevant', 'good match', 'aligns well']):
                return 0.7
            elif any(term in analysis_lower for term in ['somewhat relevant', 'partially relevant']):
                return 0.5
            elif any(term in analysis_lower for term in ['low relevance', 'limited relevance']):
                return 0.3
            elif any(term in analysis_lower for term in ['not relevant', 'irrelevant', 'no relevance']):
                return 0.1
            
            return 0.5  # Default medium relevance
            
        except Exception:
            return 0.5  # Default medium relevance
    
    def _determine_is_relevant(self, relevance_response: str, relevance_score: float) -> bool:
        """Determine if content is relevant based on score and analysis"""
        try:
            if not relevance_response:
                return False
            
            # Primary check: Use relevance score
            if relevance_score >= 0.6:  # 60% threshold for relevance
                return True
            
            # Secondary check: Look for explicit relevance decisions
            analysis_lower = relevance_response.lower()
            
            # Explicit "Yes" decisions
            if any(phrase in analysis_lower for phrase in [
                'relevance decision: yes',
                'relevant: yes',
                'is relevant: yes',
                'decision: relevant'
            ]):
                return True
            
            # Explicit "No" decisions
            if any(phrase in analysis_lower for phrase in [
                'relevance decision: no',
                'relevant: no',
                'is relevant: no',
                'decision: not relevant',
                'decision: irrelevant'
            ]):
                return False
            
            # Fallback to score-based decision
            return relevance_score >= 0.5
            
        except Exception:
            return relevance_score >= 0.5 if relevance_score else False

    def fetch_request_content(self, project_id: str, request_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"Fetching request description for project_id: {project_id}, request_id: {request_id}")

            # response = dynamodb_client.scan_items(
            #     table_name="requests",
            #     filter_expression=Attr("project_id").eq(project_id),
            #     limit=10  # fetch a few in case there are multiple
            # )
            #
            # # Debug logging
            # logger.info(f"DynamoDB response type: {type(response)}, content: {response}")
            #
            # # Handle response more safely
            # if not response:
            #     logger.warning(f"No response from DynamoDB for project_id: {project_id}")
            #     return {
            #         "success": True,
            #         "description": DEFAULT_KITS_KIQS_CONTENT
            #     }
            #
            # # Extract items safely
            # if isinstance(response, dict):
            #     items = response.get("Items", [])
            # else:
            #     logger.warning(f"Unexpected response type from DynamoDB: {type(response)}")
            #     return {
            #         "success": True,
            #         "description": DEFAULT_KITS_KIQS_CONTENT
            #     }
            #
            # # Ensure items is a list
            # if not isinstance(items, list):
            #     logger.warning(f"Items is not a list, got: {type(items)}")
            #     return {
            #         "success": True,
            #         "description": DEFAULT_KITS_KIQS_CONTENT
            #     }
            #
            # if not items:
            #     logger.warning(f"No request found for project_id: {project_id}, request_id: {request_id}")
            #     return {
            #         "success": True,
            #         "description": DEFAULT_KITS_KIQS_CONTENT  # fallback
            #     }
            #
            # # Filter out non-dict items and pick most recent item
            # dict_items = [item for item in items if isinstance(item, dict)]
            #
            # if not dict_items:
            #     logger.warning(f"No valid dict items found in response for project_id: {project_id}")
            #     return {
            #         "success": True,
            #         "description": DEFAULT_KITS_KIQS_CONTENT
            #     }
            #
            # latest_item = max(dict_items, key=lambda x: x.get("created_at", ""))
            #
            # # fetch description directly from the description column
            # description = latest_item.get("description", "")
            #
            # # if no description found, use fallback
            # if not description:
            #     description = DEFAULT_KITS_KIQS_CONTENT
            #
            # logger.info(
            #     f"✅ REQUEST DESCRIPTION FETCHED - Project ID: {project_id} | Request ID: {request_id} | Length: {len(description)}"
            # )

            return {
                "success": True,
                "description": DEFAULT_KITS_KIQS_CONTENT
            }

        except Exception as e:
            logger.error(
                f"❌ REQUEST FETCH ERROR - Project ID: {project_id}, Request ID: {request_id} | Error: {str(e)}")
            # Always return success=True but attach default KITs/KIQs content
            return {
                "success": True,
                "description": DEFAULT_KITS_KIQS_CONTENT
            }


# Global service instance
relevance_check_db_operations_service = RelevanceCheckDBOperationsService() 