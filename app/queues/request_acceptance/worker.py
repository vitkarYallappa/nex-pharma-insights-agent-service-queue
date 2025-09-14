from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.queues.base_worker import BaseWorker
from app.models.request_models import MarketIntelligenceRequest, RequestAcceptancePayload
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestAcceptanceWorker(BaseWorker):
    """Worker for processing request acceptance queue"""
    
    def __init__(self):
        super().__init__("request_acceptance")
    
    def process_item(self, item: Dict[str, Any]) -> bool:
        """Process a request acceptance item"""
        try:
            payload = item.get('payload', {})
            
            # Extract original request
            original_request_data = payload.get('original_request', {})
            
            if not original_request_data:
                logger.error("No original request found in payload")
                return False
            
            # Validate the request
            validation_results = self._validate_request(original_request_data)
            
            if not validation_results['is_valid']:
                logger.error(f"Request validation failed: {validation_results['errors']}")
                return False
            
            # Create processing plan
            processing_plan = self._create_processing_plan(original_request_data)
            
            # Update payload with validation results and processing plan
            updated_payload = {
                'original_request': original_request_data,
                'validation_results': validation_results,
                'processing_plan': processing_plan,
                'accepted_at': datetime.utcnow().isoformat()
            }
            
            # Update the item payload in DynamoDB
            from app.database.dynamodb_client import dynamodb_client
            
            success = dynamodb_client.update_item(
                self.table_name,
                {'PK': item['PK'], 'SK': item['SK']},
                "SET payload = :payload, updated_at = :updated_at",
                {
                    ':payload': updated_payload,
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
            
            if success:
                logger.info(f"Successfully processed request acceptance for {item['PK']}")
                return True
            else:
                logger.error(f"Failed to update payload for {item['PK']}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing request acceptance item: {str(e)}")
            return False
    
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for SERP queue - CREATE ONE ITEM PER SOURCE"""
        payload = completed_item.get('payload', {})
        original_request = payload.get('original_request', {})
        
        if next_queue == "serp":
            config = original_request.get('config', {})
            keywords = config.get('keywords', [])
            sources = config.get('sources', [])
            
            # This method will be called multiple times by base worker
            # We need to create separate SERP items for each source
            # Return the base payload - the base worker will handle creating multiple items
            return {
                'keywords': keywords,
                'sources': sources,  # All sources - we'll split them in _create_next_queue_item
                'extraction_mode': config.get('extraction_mode', 'summary'),
                'quality_threshold': config.get('quality_threshold', 0.8),
                'search_results': []
            }
        
        return {}
    
    def _create_next_queue_item(self, next_queue: str, project_id: str, 
                               request_id: str, completed_item: Dict[str, Any]):
        """Override to create multiple SERP items (one per source)"""
        if next_queue != "serp":
            # Use parent implementation for other queues
            return super()._create_next_queue_item(next_queue, project_id, request_id, completed_item)
        
        # For SERP queue, create one item per source
        from app.models.queue_models import QueueItemFactory
        from app.database.dynamodb_client import dynamodb_client
        from config import QUEUE_TABLES
        
        payload = completed_item.get('payload', {})
        original_request = payload.get('original_request', {})
        config = original_request.get('config', {})
        keywords = config.get('keywords', [])
        sources = config.get('sources', [])
        
        logger.info(f"Creating {len(sources)} SERP queue items for {len(keywords)} keywords")
        
        for i, source in enumerate(sources):
            try:
                # Create SERP payload for this specific source
                serp_payload = {
                    'keywords': keywords,
                    'source': source,  # Single source per SERP item
                    'source_index': i,
                    'total_sources': len(sources),
                    'extraction_mode': config.get('extraction_mode', 'summary'),
                    'quality_threshold': config.get('quality_threshold', 0.8),
                    'search_queries': self._generate_search_queries_for_source(keywords, source),
                    'search_results': []
                }
                
                # Create queue item
                queue_item = QueueItemFactory.create_queue_item(
                    queue_name="serp",
                    project_id=project_id,
                    project_request_id=request_id,
                    priority=completed_item.get('priority', 'medium'),
                    processing_strategy=completed_item.get('processing_strategy', 'table'),
                    payload=serp_payload,
                    metadata={
                        **completed_item.get('metadata', {}),
                        'source_name': source.get('name', ''),
                        'source_type': source.get('type', ''),
                        'created_from': 'request_acceptance'
                    }
                )
                
                # Store in DynamoDB
                table_name = QUEUE_TABLES["serp"]
                success = dynamodb_client.put_item(table_name, queue_item.dict())
                
                if success:
                    logger.info(f"Created SERP queue item {i+1}/{len(sources)} for source: {source.get('name')}")
                else:
                    logger.error(f"Failed to create SERP queue item for source: {source.get('name')}")
                    
            except Exception as e:
                logger.error(f"Failed to create SERP item for source {source.get('name', 'unknown')}: {str(e)}")
        
        logger.info(f"Completed creating SERP queue items for request {request_id}")
    
    def _generate_search_queries_for_source(self, keywords: List[str], source: Dict[str, Any]) -> List[str]:
        """Generate search queries for a specific source"""
        queries = []
        source_url = source.get('url', '')
        source_name = source.get('name', '')
        
        # Basic keyword queries
        for keyword in keywords:
            queries.append(keyword)
        
        # Source-specific queries
        if source_url:
            for keyword in keywords[:3]:  # Limit to first 3 keywords
                queries.append(f"{keyword} site:{source_url}")
        
        # Source name + keyword combinations
        if source_name:
            for keyword in keywords[:2]:  # Limit to first 2 keywords
                queries.append(f"{keyword} {source_name}")
        
        # Remove duplicates and limit
        unique_queries = list(set(queries))
        return unique_queries[:8]  # Limit to 8 queries per source
    
    def _validate_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the market intelligence request"""
        errors = []
        warnings = []
        
        try:
            # Validate required fields
            required_fields = ['project_id', 'project_request_id', 'user_id', 'config']
            for field in required_fields:
                if not request_data.get(field):
                    errors.append(f"Missing required field: {field}")
            
            # Validate config
            config = request_data.get('config', {})
            if config:
                # Validate keywords
                keywords = config.get('keywords', [])
                if not keywords:
                    errors.append("No keywords provided in config")
                elif len(keywords) > 20:
                    warnings.append("Large number of keywords may impact performance")
                
                # Validate sources
                sources = config.get('sources', [])
                if not sources:
                    errors.append("No sources provided in config")
                else:
                    for i, source in enumerate(sources):
                        if not isinstance(source, dict):
                            errors.append(f"Source {i} is not a valid object")
                            continue
                        
                        if not source.get('name'):
                            errors.append(f"Source {i} missing name")
                        if not source.get('url'):
                            errors.append(f"Source {i} missing URL")
                        if not source.get('type'):
                            warnings.append(f"Source {i} missing type")
                
                # Validate extraction mode
                extraction_mode = config.get('extraction_mode', 'summary')
                valid_modes = ['summary', 'full', 'structured']
                if extraction_mode not in valid_modes:
                    errors.append(f"Invalid extraction_mode: {extraction_mode}. Must be one of {valid_modes}")
                
                # Validate quality threshold
                quality_threshold = config.get('quality_threshold', 0.8)
                if not isinstance(quality_threshold, (int, float)) or not (0.0 <= quality_threshold <= 1.0):
                    errors.append("quality_threshold must be a number between 0.0 and 1.0")
            
            # Validate priority
            priority = request_data.get('priority', 'medium')
            valid_priorities = ['high', 'medium', 'low']
            if priority not in valid_priorities:
                errors.append(f"Invalid priority: {priority}. Must be one of {valid_priorities}")
            
            # Validate processing strategy
            processing_strategy = request_data.get('processing_strategy', 'table')
            valid_strategies = ['table', 'stream', 'batch']
            if processing_strategy not in valid_strategies:
                errors.append(f"Invalid processing_strategy: {processing_strategy}. Must be one of {valid_strategies}")
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'validated_at': datetime.utcnow().isoformat()
            }
    
    def _create_processing_plan(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create processing plan based on request configuration"""
        config = request_data.get('config', {})
        processing_strategy = request_data.get('processing_strategy', 'table')
        sources = config.get('sources', [])
        keywords = config.get('keywords', [])
        
        # Calculate expected items per queue
        expected_serp_items = len(sources)  # One per source
        expected_perplexity_items = expected_serp_items * 5  # Estimate 5 URLs per source
        expected_final_items = expected_perplexity_items * 2  # Both insight and implication
        
        # Standard workflow
        plan = {
            'queues': ['serp', 'perplexity', 'insight', 'implication'],
            'strategy': processing_strategy,
            'expected_items': {
                'serp': expected_serp_items,
                'perplexity': expected_perplexity_items,
                'insight': expected_perplexity_items,
                'implication': expected_perplexity_items
            },
            'estimated_duration_minutes': self._estimate_processing_time(config, processing_strategy),
            'created_at': datetime.utcnow().isoformat()
        }
        
        return plan
    
    def _estimate_processing_time(self, config: Dict[str, Any], strategy: str) -> int:
        """Estimate processing time in minutes"""
        base_time = 5  # Base processing time
        
        # Factor in number of keywords and sources
        keywords_count = len(config.get('keywords', []))
        sources_count = len(config.get('sources', []))
        
        keyword_factor = min(keywords_count * 2, 20)  # Max 20 minutes for keywords
        source_factor = min(sources_count * 3, 30)    # Max 30 minutes for sources
        
        # Strategy multipliers
        strategy_multipliers = {
            'stream': 0.8,  # Faster processing
            'table': 1.0,   # Standard processing
            'batch': 1.5    # Slower but more thorough
        }
        
        multiplier = strategy_multipliers.get(strategy, 1.0)
        
        total_time = (base_time + keyword_factor + source_factor) * multiplier
        
        return int(total_time)
