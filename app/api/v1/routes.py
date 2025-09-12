from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings, QUEUE_TABLES, QUEUE_PROCESSING_LIMITS
from app.models.request_models import (
    MarketIntelligenceRequest, RequestResponse, RequestStatus
)
from app.models.queue_models import QueueItemFactory
from app.database.dynamodb_client import dynamodb_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Market Intelligence"])


class ProcessingLimitsUpdate(BaseModel):
    """Model for updating processing limits"""
    max_perplexity_urls_per_serp: int = None
    max_serp_results: int = None
    max_insight_items: int = None
    max_implication_items: int = None
    task_delay_seconds: int = None


@router.get("/processing-limits")
async def get_processing_limits():
    """Get current processing limits configuration"""
    try:
        return {
            "status": "success",
            "processing_limits": QUEUE_PROCESSING_LIMITS,
            "description": {
                "max_perplexity_urls_per_serp": "Maximum URLs to send to Perplexity from each SERP result",
                "max_serp_results": "Maximum search results to process",
                "max_insight_items": "Maximum insight items per request",
                "max_implication_items": "Maximum implication items per request",
                "task_delay_seconds": "Delay in seconds between processing each queue item"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get processing limits: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve processing limits")


@router.post("/processing-limits")
async def update_processing_limits(limits: ProcessingLimitsUpdate):
    """Update processing limits configuration"""
    try:
        # Update only provided values
        updated_limits = QUEUE_PROCESSING_LIMITS.copy()
        
        if limits.max_perplexity_urls_per_serp is not None:
            if limits.max_perplexity_urls_per_serp < 1 or limits.max_perplexity_urls_per_serp > 20:
                raise HTTPException(status_code=400, detail="max_perplexity_urls_per_serp must be between 1 and 20")
            updated_limits["max_perplexity_urls_per_serp"] = limits.max_perplexity_urls_per_serp
            
        if limits.max_serp_results is not None:
            if limits.max_serp_results < 1 or limits.max_serp_results > 100:
                raise HTTPException(status_code=400, detail="max_serp_results must be between 1 and 100")
            updated_limits["max_serp_results"] = limits.max_serp_results
            
        if limits.max_insight_items is not None:
            if limits.max_insight_items < 1 or limits.max_insight_items > 50:
                raise HTTPException(status_code=400, detail="max_insight_items must be between 1 and 50")
            updated_limits["max_insight_items"] = limits.max_insight_items
            
        if limits.max_implication_items is not None:
            if limits.max_implication_items < 1 or limits.max_implication_items > 50:
                raise HTTPException(status_code=400, detail="max_implication_items must be between 1 and 50")
            updated_limits["max_implication_items"] = limits.max_implication_items
        
        if limits.task_delay_seconds is not None:
            if limits.task_delay_seconds < 0 or limits.task_delay_seconds > 60:
                raise HTTPException(status_code=400, detail="task_delay_seconds must be between 0 and 60")
            updated_limits["task_delay_seconds"] = limits.task_delay_seconds
        
        # Update the global configuration (in production, this would be stored in database)
        QUEUE_PROCESSING_LIMITS.update(updated_limits)
        
        logger.info(f"Processing limits updated: {updated_limits}")
        
        return {
            "status": "success",
            "message": "Processing limits updated successfully",
            "updated_limits": updated_limits
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update processing limits: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update processing limits")


@router.post("/market-intelligence-requests", response_model=RequestResponse)
async def create_market_intelligence_request(
    request: MarketIntelligenceRequest,
    background_tasks: BackgroundTasks
):
    """
    Accept market intelligence requests and initiate queue-based processing.
    
    This endpoint:
    1. Validates the incoming request
    2. Creates initial queue item in request_acceptance queue
    3. Returns acceptance confirmation with tracking information
    """
    try:
        logger.info(f"Received market intelligence request for project: {request.project_id}")
        
        # Validate request
        validation_errors = _validate_request(request)
        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail=f"Request validation failed: {'; '.join(validation_errors)}"
            )
        
        # Create queue item for request acceptance
        queue_item = QueueItemFactory.create_queue_item(
            queue_name="request_acceptance",
            project_id=request.project_id,
            project_request_id=request.project_request_id,
            priority=request.priority,
            processing_strategy=request.processing_strategy,
            payload={
                'original_request': request.dict(),
                'validation_results': {},
                'processing_plan': {}
            },
            metadata={
                'user_id': request.user_id,
                'submitted_at': datetime.utcnow().isoformat(),
                'api_version': settings.app_version
            }
        )
        
        # Store in DynamoDB
        table_name = QUEUE_TABLES["request_acceptance"]
        success = dynamodb_client.put_item(table_name, queue_item.dict())
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to queue request for processing"
            )
        
        # Calculate estimated completion time
        estimated_completion = _calculate_estimated_completion(request)
        
        logger.info(f"Request {request.project_request_id} successfully queued for processing")
        
        return RequestResponse(
            status="accepted",
            request_id=request.project_request_id,
            estimated_completion=estimated_completion,
            tracking_url=f"{settings.api_prefix}/requests/{request.project_request_id}/status"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing request"
        )


@router.get("/requests/{request_id}/status", response_model=RequestStatus)
async def get_request_status(request_id: str):
    """Get processing status of a request across all queues"""
    try:
        logger.info(f"Getting status for request: {request_id}")
        
        # Find project_id by scanning for the request_id
        project_id = await _find_project_id_for_request(request_id)
        
        if not project_id:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Get status from all queue tables
        queue_progress = {}
        overall_status = "not_found"
        latest_update = None
        error_message = None
        
        pk = f"{project_id}#{request_id}"
        
        for queue_name, table_name in QUEUE_TABLES.items():
            try:
                # Query items for this request in this queue
                items = dynamodb_client.query_items(
                    table_name=table_name,
                    key_condition="PK = :pk",
                    expression_attribute_values={":pk": pk}
                )
                
                if items:
                    # Get the latest item for this queue
                    latest_item = max(items, key=lambda x: x.get('created_at', ''))
                    queue_progress[queue_name] = latest_item.get('status', 'unknown')
                    
                    # Update overall status and latest update time
                    item_updated = latest_item.get('updated_at')
                    if not latest_update or (item_updated and item_updated > latest_update):
                        latest_update = item_updated
                    
                    # Capture any error messages
                    if latest_item.get('status') == 'failed' and latest_item.get('error_message'):
                        error_message = latest_item.get('error_message')
                
            except Exception as e:
                logger.warning(f"Failed to get status from {queue_name}: {str(e)}")
                queue_progress[queue_name] = "error"
        
        # Determine overall status
        overall_status = _determine_overall_status(queue_progress)
        
        # Get creation time from request_acceptance queue
        created_at = None
        if 'request_acceptance' in queue_progress:
            try:
                acceptance_items = dynamodb_client.query_items(
                    table_name=QUEUE_TABLES["request_acceptance"],
                    key_condition="PK = :pk",
                    expression_attribute_values={":pk": pk}
                )
                if acceptance_items:
                    created_at = min(item.get('created_at') for item in acceptance_items if item.get('created_at'))
            except Exception:
                pass
        
        return RequestStatus(
            request_id=request_id,
            project_id=project_id,
            status=overall_status,
            progress=queue_progress,
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow(),
            updated_at=datetime.fromisoformat(latest_update) if latest_update else datetime.utcnow(),
            error_message=error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve request status"
        )


@router.get("/requests/{request_id}/results")
async def get_request_results(request_id: str):
    """Get processing results for a completed request"""
    try:
        logger.info(f"Getting results for request: {request_id}")
        
        # Find project_id
        project_id = await _find_project_id_for_request(request_id)
        
        if not project_id:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Check if request is completed
        status_response = await get_request_status(request_id)
        
        if status_response.status not in ["completed", "partially_completed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Request is not completed. Current status: {status_response.status}"
            )
        
        # Collect results from S3 and final queue tables
        results = {
            "request_id": request_id,
            "project_id": project_id,
            "status": status_response.status,
            "completed_at": status_response.updated_at.isoformat(),
            "results": {
                "insights": None,
                "implications": None,
                "raw_data_references": []
            }
        }
        
        # Get insights and implications from their respective queues
        pk = f"{project_id}#{request_id}"
        
        # Get insights
        if status_response.progress.get("insight") == "completed":
            insight_items = dynamodb_client.query_items(
                table_name=QUEUE_TABLES["insight"],
                key_condition="PK = :pk",
                expression_attribute_values={":pk": pk}
            )
            if insight_items:
                latest_insight = max(insight_items, key=lambda x: x.get('updated_at', ''))
                results["results"]["insights"] = latest_insight.get('payload', {}).get('insights', {})
        
        # Get implications
        if status_response.progress.get("implication") == "completed":
            implication_items = dynamodb_client.query_items(
                table_name=QUEUE_TABLES["implication"],
                key_condition="PK = :pk",
                expression_attribute_values={":pk": pk}
            )
            if implication_items:
                latest_implication = max(implication_items, key=lambda x: x.get('updated_at', ''))
                results["results"]["implications"] = latest_implication.get('payload', {}).get('implications', {})
        
        # Get S3 data references
        from app.database.s3_client import s3_client
        s3_references = s3_client.get_content_references(project_id, request_id)
        results["results"]["raw_data_references"] = s3_references
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve request results"
        )


@router.get("/requests")
async def list_requests(
    project_id: str = None,
    status: str = None,
    limit: int = 50,
    user_id: str = None
):
    """List market intelligence requests with optional filtering"""
    try:
        logger.info(f"Listing requests with filters: project_id={project_id}, status={status}, limit={limit}")
        
        # Query request_acceptance table for all requests
        table_name = QUEUE_TABLES["request_acceptance"]
        
        if project_id:
            # Query by project_id prefix
            items = dynamodb_client.scan_items(
                table_name=table_name,
                filter_expression="begins_with(PK, :project_id)",
                expression_attribute_values={":project_id": project_id},
                limit=limit
            )
        else:
            # Scan all items
            items = dynamodb_client.scan_items(
                table_name=table_name,
                limit=limit
            )
        
        # Process and filter results
        requests = []
        for item in items:
            try:
                # Extract project_id and request_id from PK
                pk_parts = item.get('PK', '').split('#')
                if len(pk_parts) != 2:
                    continue
                
                item_project_id, item_request_id = pk_parts
                
                # Apply user filter if specified
                if user_id and item.get('metadata', {}).get('user_id') != user_id:
                    continue
                
                # Get current status
                current_status = item.get('status', 'unknown')
                
                # Apply status filter if specified
                if status and current_status != status:
                    continue
                
                request_info = {
                    "request_id": item_request_id,
                    "project_id": item_project_id,
                    "status": current_status,
                    "priority": item.get('priority', 'medium'),
                    "processing_strategy": item.get('processing_strategy', 'table'),
                    "created_at": item.get('created_at'),
                    "updated_at": item.get('updated_at'),
                    "user_id": item.get('metadata', {}).get('user_id'),
                    "retry_count": item.get('retry_count', 0)
                }
                
                requests.append(request_info)
                
            except Exception as e:
                logger.warning(f"Failed to process item {item.get('PK', 'unknown')}: {str(e)}")
                continue
        
        # Sort by creation time (newest first)
        requests.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {
            "requests": requests,
            "total_count": len(requests),
            "filters_applied": {
                "project_id": project_id,
                "status": status,
                "user_id": user_id,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list requests: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve requests list"
        )


@router.delete("/requests/{request_id}")
async def cancel_request(request_id: str):
    """Cancel a pending or processing request"""
    try:
        logger.info(f"Cancelling request: {request_id}")
        
        # Find project_id
        project_id = await _find_project_id_for_request(request_id)
        
        if not project_id:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Check current status
        status_response = await get_request_status(request_id)
        
        if status_response.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel request with status: {status_response.status}"
            )
        
        # Update all pending/processing items to cancelled
        pk = f"{project_id}#{request_id}"
        cancelled_count = 0
        
        for queue_name, table_name in QUEUE_TABLES.items():
            try:
                items = dynamodb_client.query_items(
                    table_name=table_name,
                    key_condition="PK = :pk",
                    expression_attribute_values={":pk": pk}
                )
                
                for item in items:
                    current_status = item.get('status', '')
                    if current_status in ['pending', 'processing', 'retry']:
                        success = dynamodb_client.update_item_status(
                            table_name=table_name,
                            pk=item['PK'],
                            sk=item['SK'],
                            new_status='cancelled',
                            error_message='Request cancelled by user'
                        )
                        if success:
                            cancelled_count += 1
                            
            except Exception as e:
                logger.warning(f"Failed to cancel items in {queue_name}: {str(e)}")
        
        logger.info(f"Cancelled {cancelled_count} queue items for request {request_id}")
        
        return {
            "message": "Request cancelled successfully",
            "request_id": request_id,
            "cancelled_items": cancelled_count,
            "status": "cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel request {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel request"
        )


# Helper functions

def _validate_request(request: MarketIntelligenceRequest) -> List[str]:
    """Validate market intelligence request and return list of errors"""
    errors = []
    
    # Basic field validation (Pydantic handles most of this)
    if not request.config.keywords:
        errors.append("At least one keyword is required")
    
    if not request.config.sources:
        errors.append("At least one source is required")
    
    # Validate sources
    for i, source in enumerate(request.config.sources):
        if not source.name.strip():
            errors.append(f"Source {i+1}: name is required")
        if not source.url.strip():
            errors.append(f"Source {i+1}: URL is required")
        if not source.type.strip():
            errors.append(f"Source {i+1}: type is required")
    
    # Validate limits
    if len(request.config.keywords) > 20:
        errors.append("Maximum 20 keywords allowed")
    
    if len(request.config.sources) > 10:
        errors.append("Maximum 10 sources allowed")
    
    return errors


def _calculate_estimated_completion(request: MarketIntelligenceRequest) -> datetime:
    """Calculate estimated completion time based on request complexity"""
    
    # Base processing time
    base_minutes = 15
    
    # Factor in complexity
    keyword_factor = len(request.config.keywords) * 2
    source_factor = len(request.config.sources) * 3
    
    # Processing strategy impact
    strategy_multipliers = {
        "stream": 0.7,   # Faster processing
        "table": 1.0,    # Standard processing
        "batch": 1.3     # Slower but more thorough
    }
    
    # Priority impact
    priority_multipliers = {
        "high": 0.8,     # Higher resource allocation
        "medium": 1.0,   # Standard processing
        "low": 1.4       # Lower priority, longer wait
    }
    
    strategy_mult = strategy_multipliers.get(request.processing_strategy, 1.0)
    priority_mult = priority_multipliers.get(request.priority, 1.0)
    
    total_minutes = (base_minutes + keyword_factor + source_factor) * strategy_mult * priority_mult
    
    # Add some randomness for realism (±20%)
    import random
    variance = random.uniform(0.8, 1.2)
    total_minutes *= variance
    
    estimated_time = datetime.utcnow() + timedelta(minutes=int(total_minutes))
    return estimated_time


async def _find_project_id_for_request(request_id: str) -> str:
    """Find project_id for a given request_id by scanning request_acceptance table"""
    try:
        table_name = QUEUE_TABLES["request_acceptance"]
        
        # Scan for items containing the request_id
        items = dynamodb_client.scan_items(
            table_name=table_name,
            filter_expression="contains(PK, :request_id)",
            expression_attribute_values={":request_id": request_id},
            limit=1
        )
        
        if items:
            pk = items[0].get('PK', '')
            pk_parts = pk.split('#')
            if len(pk_parts) == 2:
                return pk_parts[0]  # project_id
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to find project_id for request {request_id}: {str(e)}")
        return None


def _determine_overall_status(queue_progress: Dict[str, str]) -> str:
    """Determine overall request status from individual queue statuses"""
    
    if not queue_progress:
        return "not_found"
    
    # Define queue processing order
    queue_order = ["request_acceptance", "serp", "perplexity", "fetch_content", "insight", "implication"]
    
    # Check for failures
    if any(status == "failed" for status in queue_progress.values()):
        return "failed"
    
    # Check for cancellation
    if any(status == "cancelled" for status in queue_progress.values()):
        return "cancelled"
    
    # Check completion status
    final_queues = ["insight", "implication"]
    final_statuses = [queue_progress.get(queue, "not_started") for queue in final_queues]
    
    if all(status == "completed" for status in final_statuses):
        return "completed"
    
    if any(status == "completed" for status in final_statuses):
        return "partially_completed"
    
    # Check if any queue is processing
    if any(status == "processing" for status in queue_progress.values()):
        return "processing"
    
    # Check if any queue is pending
    if any(status in ["pending", "retry"] for status in queue_progress.values()):
        return "queued"
    
    # Default status based on furthest progress
    for queue in reversed(queue_order):
        if queue in queue_progress:
            status = queue_progress[queue]
            if status == "completed":
                continue
            elif status in ["processing", "pending", "retry"]:
                return "processing"
            else:
                return "queued"
    
    return "unknown"
