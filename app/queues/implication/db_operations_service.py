import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from app.utils.logger import get_logger
from app.database.dynamodb_client import DynamoDBClient

logger = get_logger(__name__)


class ImplicationDBOperationsService:
    """Service for handling implication-related DynamoDB operations"""
    
    def __init__(self):
        self.service_name = "Implication DB Operations Service"
        self.dynamodb_client = DynamoDBClient()
        
        # DynamoDB table name for implications
        self.implication_table = "content_implication"
        
        logger.info(f"Initialized {self.service_name}")
    
    async def process_implication_completion(self, content_id: str, implication_result: Dict[str, Any], 
                                           original_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process completed implication generation and store in DynamoDB
        
        Args:
            content_id: The content ID from perplexity processing
            implication_result: Result from ImplicationProcessor
            original_metadata: Original metadata from perplexity processing
            
        Returns:
            Dict with processing results and metadata
        """
        try:
            logger.info(f"💾 Storing implication data for content ID: {content_id}")
            
            # Generate unique primary key for this implication record
            implication_pk = str(uuid.uuid4())
            
            # Prepare implication item for DynamoDB - simple structure
            now = datetime.utcnow().isoformat()
            
            implication_item = {
                "pk": implication_pk,
                "url_id": content_id,  # Using content_id as url_id for consistency
                "content_id": content_id,
                "implication_text": implication_result.get("content", ""),
                "implication_content_file_path": None,
                "implication_type": "bedrock_generated",
                "priority_level": "medium",
                "confidence_score": "0.8",
                "version": 1,
                "is_canonical": True,
                "preferred_choice": True,
                "created_at": now,
                "created_by": "system"
            }
            
            # Store in DynamoDB
            self.dynamodb_client.put_item(
                table_name=self.implication_table,
                item=implication_item
            )
            
            logger.info(f"💾 Stored implication data in DynamoDB: {implication_pk}")
            
            # Prepare return metadata
            processing_metadata = {
                "service": self.service_name,
                "content_id": content_id,
                "implication_pk": implication_pk,
                "processed_at": now,
                "success": True
            }
            
            return {
                "content_id": content_id,
                "implication_pk": implication_pk,
                "success": True,
                "processing_metadata": processing_metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Error storing implication data for content {content_id}: {str(e)}")
            
            return {
                "content_id": content_id,
                "success": False,
                "error": str(e),
                "processing_metadata": {
                    "service": self.service_name,
                    "content_id": content_id,
                    "error": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                }
            } 