from typing import Dict, Any, List
import json
from datetime import datetime

from app.queues.base_worker import BaseWorker
from app.queues.perplexity.content_service import PerplexityContentService
from app.database.s3_client import s3_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PerplexityWorker(BaseWorker):
    """Worker for processing Perplexity AI enhancement queue"""
    
    def __init__(self):
        super().__init__("perplexity")
        self.content_service = PerplexityContentService()
    
    def process_item(self, item: Dict[str, Any]) -> bool:
        """Process a Perplexity item for a batch of URLs"""
        try:
            payload = item.get('payload', {})
            
            search_data = payload.get('search_data', {})
            analysis_prompt = payload.get('analysis_prompt', '')
            
            if not search_data:
                logger.error("No search data found in payload")
                return False
            
            source = search_data.get('source', {})
            batch_index = search_data.get('batch_index', 0)
            urls = search_data.get('urls', [])
            
            logger.info(f"Processing Perplexity batch {batch_index+1} for source: {source.get('name')} with {len(urls)} URLs")
            
            # Enhance data using Perplexity AI
            enhanced_data = self._enhance_search_data(search_data, analysis_prompt)
            
            if not enhanced_data:
                logger.error(f"Failed to enhance search data for batch {batch_index+1}")
                return False
            
            # Extract project and request IDs
            project_id, request_id = self._extract_ids_from_pk(item.get('PK', ''))
            
            # Store enhanced data in S3
            s3_key = s3_client.store_content_data(project_id, request_id, {
                'enhanced_search_data': enhanced_data,
                'original_search_data': search_data,
                'analysis_prompt': analysis_prompt,
                'processed_at': datetime.utcnow().isoformat(),
                'batch_info': {
                    'batch_index': batch_index,
                    'source_name': source.get('name'),
                    'urls_processed': len(urls)
                },
                'enhancement_metadata': {
                    'ai_model_used': 'perplexity',
                    'processing_time': enhanced_data.get('processing_time', 0),
                    'confidence_score': enhanced_data.get('confidence_score', 0.0)
                }
            })
            
            if not s3_key:
                logger.error(f"Failed to store enhanced data in S3 for batch {batch_index+1}")
                return False
            
            # Update payload with enhanced results
            updated_payload = payload.copy()
            updated_payload.update({
                'enhanced_data': enhanced_data,
                's3_enhanced_key': s3_key,
                'processed_at': datetime.utcnow().isoformat(),
                'enhancement_summary': enhanced_data.get('summary', {}),
                'content_references': self._extract_content_references(enhanced_data)
            })
            
            # Update the item in DynamoDB
            from app.database.dynamodb_client import dynamodb_client
            
            success = dynamodb_client.update_item(
                table_name=self.table_name,
                key={'PK': item['PK'], 'SK': item['SK']},
                update_expression="SET payload = :payload, updated_at = :updated_at",
                expression_attribute_values={
                    ':payload': updated_payload,
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
            
            if success:
                logger.info(f"Successfully processed Perplexity enhancement for batch {batch_index+1}")
                return True
            else:
                logger.error(f"Failed to update Perplexity payload for batch {batch_index+1}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing Perplexity item: {str(e)}")
            return False
    
    def prepare_next_queue_payload(self, next_queue: str, completed_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for next queues - NOT USED, we override _create_next_queue_item"""
        # This won't be used since we override _create_next_queue_item
        return {}
    
    def _create_next_queue_item(self, next_queue: str, project_id: str, 
                               request_id: str, completed_item: Dict[str, Any]):
        """Override to create BOTH Insight and Implication queue items simultaneously"""
        # We want to trigger BOTH insight and implication queues for each Perplexity completion
        from app.models.queue_models import QueueItemFactory
        from app.database.dynamodb_client import dynamodb_client
        from config import QUEUE_TABLES
        
        payload = completed_item.get('payload', {})
        enhanced_data = payload.get('enhanced_data', {})
        search_data = payload.get('search_data', {})
        source = search_data.get('source', {})
        batch_index = search_data.get('batch_index', 0)
        
        # Extract content references for both queues
        content_references = payload.get('content_references', [])
        s3_enhanced_key = payload.get('s3_enhanced_key', '')
        
        # Create both Insight and Implication queue items
        queues_to_create = ['insight', 'implication']
        
        logger.info(f"Creating {len(queues_to_create)} queue items (insight + implication) for Perplexity batch {batch_index+1}")
        
        for queue_name in queues_to_create:
            try:
                # Create payload specific to each queue type
                if queue_name == 'insight':
                    queue_payload = {
                        'content_references': content_references,
                        's3_enhanced_key': s3_enhanced_key,
                        'analysis_type': 'market_insights',
                        'source_info': {
                            'name': source.get('name'),
                            'type': source.get('type'),
                            'batch_index': batch_index
                        },
                        'enhanced_summary': enhanced_data.get('summary', {}),
                        'insights': {}
                    }
                else:  # implication
                    queue_payload = {
                        'content_references': content_references,
                        's3_enhanced_key': s3_enhanced_key,
                        'analysis_type': 'business_implications',
                        'source_info': {
                            'name': source.get('name'),
                            'type': source.get('type'),
                            'batch_index': batch_index
                        },
                        'enhanced_summary': enhanced_data.get('summary', {}),
                        'implications': {}
                    }
                
                # Create queue item
                queue_item = QueueItemFactory.create_queue_item(
                    queue_name=queue_name,
                    project_id=project_id,
                    project_request_id=request_id,
                    priority=completed_item.get('priority', 'medium'),
                    processing_strategy=completed_item.get('processing_strategy', 'table'),
                    payload=queue_payload,
                    metadata={
                        **completed_item.get('metadata', {}),
                        'source_name': source.get('name', ''),
                        'batch_index': batch_index,
                        'analysis_type': queue_payload['analysis_type'],
                        'created_from': 'perplexity'
                    }
                )
                
                # Store in DynamoDB
                table_name = QUEUE_TABLES[queue_name]
                success = dynamodb_client.put_item(table_name, queue_item.dict())
                
                if success:
                    logger.info(f"Created {queue_name} queue item for batch {batch_index+1} from source: {source.get('name')}")
                else:
                    logger.error(f"Failed to create {queue_name} queue item for batch {batch_index+1}")
                    
            except Exception as e:
                logger.error(f"Failed to create {queue_name} item for batch {batch_index+1}: {str(e)}")
        
        logger.info(f"Completed creating insight + implication queue items for Perplexity batch {batch_index+1}")
    
    def _extract_content_references(self, enhanced_data: Dict[str, Any]) -> List[str]:
        """Extract content references from enhanced data"""
        references = []
        
        # Get URLs from enhanced results
        enhanced_results = enhanced_data.get('enhanced_results', [])
        for result in enhanced_results:
            if result.get('url') and result.get('content_priority') in ['high', 'medium']:
                references.append(result['url'])
        
        # Get prioritized URLs from recommendations
        priority_urls = enhanced_data.get('recommendations', {}).get('content_extraction_priority', [])
        references.extend(priority_urls[:10])  # Limit to top 10
        
        # Remove duplicates
        return list(set(references))
    
    def _enhance_search_data(self, search_data: Dict[str, Any], analysis_prompt: str) -> Dict[str, Any]:
        """Enhance search data using Perplexity AI"""
        try:
            start_time = datetime.utcnow()
            
            # Get search results
            search_results = search_data.get('results', [])
            keywords = search_data.get('keywords', [])
            source = search_data.get('source', {})
            
            if not search_results:
                logger.warning("No search results to enhance")
                return {}
            
            logger.info(f"Enhancing {len(search_results)} search results from {source.get('name')} using Perplexity AI")
            
            # Analyze search results using Perplexity
            analysis_result = self.content_service.analyze_search_results(
                search_results, keywords, analysis_prompt
            )
            
            if not analysis_result:
                logger.error("Failed to get analysis from Perplexity service")
                return {}
            
            # Enhance individual results
            enhanced_results = []
            for result in search_results:
                enhanced_result = self._enhance_single_result(result, keywords, analysis_result)
                enhanced_results.append(enhanced_result)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create enhanced data structure
            enhanced_data = {
                'analysis': analysis_result,
                'enhanced_results': enhanced_results,
                'summary': {
                    'total_results_analyzed': len(search_results),
                    'enhanced_results_count': len(enhanced_results),
                    'key_themes': analysis_result.get('key_themes', []),
                    'relevance_score': analysis_result.get('overall_relevance', 0.0),
                    'data_quality_score': analysis_result.get('data_quality', 0.0),
                    'source_name': source.get('name'),
                    'source_type': source.get('type')
                },
                'recommendations': {
                    'content_extraction_priority': self._prioritize_content_extraction(enhanced_results),
                    'recommended_extraction_mode': self._recommend_extraction_mode(analysis_result),
                    'recommended_quality_threshold': self._recommend_quality_threshold(analysis_result)
                },
                'metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'processing_time': processing_time,
                    'ai_model': 'perplexity',
                    'confidence_score': analysis_result.get('confidence', 0.0),
                    'batch_info': {
                        'batch_index': search_data.get('batch_index', 0),
                        'total_batches': search_data.get('total_batches', 1)
                    }
                }
            }
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error enhancing search data: {str(e)}")
            return {}
    
    def _enhance_single_result(self, result: Dict[str, Any], keywords: List[str], 
                              analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a single search result"""
        enhanced = result.copy()
        
        # Add AI-generated enhancements
        enhanced.update({
            'ai_relevance_score': self._calculate_ai_relevance(result, keywords, analysis_result),
            'content_priority': self._calculate_content_priority(result, analysis_result),
            'extraction_recommendation': self._get_extraction_recommendation(result, analysis_result),
            'key_concepts': self._extract_key_concepts(result, keywords),
            'enhanced_at': datetime.utcnow().isoformat()
        })
        
        return enhanced
    
    def _calculate_ai_relevance(self, result: Dict[str, Any], keywords: List[str], 
                               analysis_result: Dict[str, Any]) -> float:
        """Calculate AI-enhanced relevance score"""
        base_relevance = result.get('relevance_score', 0.5)
        
        # Factor in AI analysis
        theme_match = 0.0
        key_themes = analysis_result.get('key_themes', [])
        
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        
        for theme in key_themes:
            if theme.lower() in title or theme.lower() in snippet:
                theme_match += 0.1
        
        # Combine scores
        ai_relevance = min(1.0, base_relevance + theme_match)
        return round(ai_relevance, 3)
    
    def _calculate_content_priority(self, result: Dict[str, Any], 
                                   analysis_result: Dict[str, Any]) -> str:
        """Calculate content extraction priority"""
        relevance = result.get('relevance_score', 0.0)
        source = result.get('source', '').lower()
        
        # High priority sources
        high_priority_sources = ['fda', 'nih', 'pubmed', 'clinicaltrials', 'who', 'ema']
        
        if any(hp_source in source for hp_source in high_priority_sources):
            return 'high'
        elif relevance > 0.7:
            return 'high'
        elif relevance > 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _get_extraction_recommendation(self, result: Dict[str, Any], 
                                     analysis_result: Dict[str, Any]) -> str:
        """Get content extraction recommendation"""
        priority = self._calculate_content_priority(result, analysis_result)
        
        if priority == 'high':
            return 'full'
        elif priority == 'medium':
            return 'summary'
        else:
            return 'structured'
    
    def _extract_key_concepts(self, result: Dict[str, Any], keywords: List[str]) -> List[str]:
        """Extract key concepts from result"""
        concepts = []
        
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        
        # Add matching keywords
        for keyword in keywords:
            if keyword.lower() in title or keyword.lower() in snippet:
                concepts.append(keyword)
        
        # Add some domain-specific concepts
        pharma_concepts = ['drug', 'medication', 'treatment', 'clinical', 'trial', 'fda', 'approval', 'regulatory']
        for concept in pharma_concepts:
            if concept in title or concept in snippet:
                concepts.append(concept)
        
        return list(set(concepts))  # Remove duplicates
    
    def _prioritize_content_extraction(self, enhanced_results: List[Dict[str, Any]]) -> List[str]:
        """Prioritize URLs for content extraction"""
        # Sort by AI relevance and priority
        sorted_results = sorted(
            enhanced_results,
            key=lambda x: (
                1 if x.get('content_priority') == 'high' else 
                0.5 if x.get('content_priority') == 'medium' else 0,
                x.get('ai_relevance_score', 0)
            ),
            reverse=True
        )
        
        return [result.get('url') for result in sorted_results if result.get('url')]
    
    def _recommend_extraction_mode(self, analysis_result: Dict[str, Any]) -> str:
        """Recommend extraction mode based on analysis"""
        data_quality = analysis_result.get('data_quality', 0.0)
        
        if data_quality > 0.8:
            return 'full'
        elif data_quality > 0.5:
            return 'summary'
        else:
            return 'structured'
    
    def _recommend_quality_threshold(self, analysis_result: Dict[str, Any]) -> float:
        """Recommend quality threshold based on analysis"""
        data_quality = analysis_result.get('data_quality', 0.0)
        
        if data_quality > 0.8:
            return 0.9
        elif data_quality > 0.6:
            return 0.8
        else:
            return 0.7
