from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.request_models import (
    RegenerateInsightsRequest, RegenerateImplicationsRequest, 
    RegenerateResponse, RegenerationHistoryResponse
)
from app.services.regenerate_insights_service import RegenerateInsightsService
from app.services.regenerate_implications_service import RegenerateImplicationsService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Regenerate Content"])


@router.post("/regenerate/insights", response_model=RegenerateResponse)
async def regenerate_insights(
    request: RegenerateInsightsRequest,
    background_tasks: BackgroundTasks
):
    """
    Regenerate insights by processing large text input with Bedrock.
    
    This endpoint:
    1. Takes content_id and large text input from user
    2. Directly calls Bedrock service to process the text
    3. Stores the regenerated insights in regenerate_insights table
    """
    try:
        logger.info(f"Received regenerate insights request for content_id: {request.content_id}")
        
        # Initialize the regenerate insights service
        regenerate_service = RegenerateInsightsService()
        
        # Process the regeneration request
        result = await regenerate_service.regenerate_insights(
            content_id=request.content_id,
            text_input=request.text_input,
            metadata=request.metadata
        )
        
        if result.get("success"):
            logger.info(f"Successfully regenerated insights for content_id: {request.content_id}")
            
            return RegenerateResponse(
                success=True,
                content_id=request.content_id,
                regenerated_content=result.get("regenerated_insights")
            )
        else:
            logger.error(f"Failed to regenerate insights: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to regenerate insights: {result.get('error', 'Unknown error')}"
            )
            
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error regenerating insights: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while regenerating insights"
        )


@router.post("/regenerate/implications", response_model=RegenerateResponse)
async def regenerate_implications(
    request: RegenerateImplicationsRequest,
    background_tasks: BackgroundTasks
):
    """
    Regenerate implications by processing large text input with Bedrock.
    
    This endpoint:
    1. Takes content_id and large text input from user
    2. Directly calls Bedrock service to process the text
    3. Returns the regenerated implications
    """
    try:
        logger.info(f"Received regenerate implications request for content_id: {request.content_id}")
        
        # Initialize the regenerate implications service
        regenerate_service = RegenerateImplicationsService()
        
        # Process the regeneration request
        result = await regenerate_service.regenerate_implications(
            content_id=request.content_id,
            text_input=request.text_input,
            metadata=request.metadata
        )
        
        if result.get("success"):
            logger.info(f"Successfully regenerated implications for content_id: {request.content_id}")
            
            return RegenerateResponse(
                success=True,
                content_id=request.content_id,
                regenerated_content=result.get("regenerated_implications")
            )
        else:
            logger.error(f"Failed to regenerate implications: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to regenerate implications: {result.get('error', 'Unknown error')}"
            )
            
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error regenerating implications: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while regenerating implications"
        )


@router.get("/regenerate/insights/{content_id}/history", response_model=RegenerationHistoryResponse)
async def get_insights_regeneration_history(content_id: str, limit: int = 10):
    """Get regeneration history for insights by content_id"""
    try:
        logger.info(f"Getting insights regeneration history for content_id: {content_id}")
        
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        regenerate_service = RegenerateInsightsService()
        result = await regenerate_service.get_regeneration_history(content_id, limit)
        
        if result.get("success"):
            return RegenerationHistoryResponse(
                success=True,
                content_id=content_id,
                regeneration_history=result.get("regeneration_history", []),
                total_count=result.get("total_count", 0)
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get regeneration history: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting insights regeneration history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve regeneration history"
        )


@router.get("/regenerate/implications/{content_id}/history", response_model=RegenerationHistoryResponse)
async def get_implications_regeneration_history(content_id: str, limit: int = 10):
    """Get regeneration history for implications by content_id"""
    try:
        logger.info(f"Getting implications regeneration history for content_id: {content_id}")
        
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        regenerate_service = RegenerateImplicationsService()
        result = await regenerate_service.get_regeneration_history(content_id, limit)
        
        if result.get("success"):
            return RegenerationHistoryResponse(
                success=True,
                content_id=content_id,
                regeneration_history=result.get("regeneration_history", []),
                total_count=result.get("total_count", 0)
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get regeneration history: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting implications regeneration history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve regeneration history"
        )


@router.get("/regenerate/insights/{content_id}/latest")
async def get_latest_regenerated_insights(content_id: str):
    """Get the latest regenerated insights for a content_id"""
    try:
        logger.info(f"Getting latest regenerated insights for content_id: {content_id}")
        
        regenerate_service = RegenerateInsightsService()
        result = await regenerate_service.get_regeneration_history(content_id, limit=1)
        
        if result.get("success") and result.get("regeneration_history"):
            latest = result["regeneration_history"][0]
            return {
                "success": True,
                "content_id": content_id,
                "latest_regeneration": latest,
                "regenerated_at": latest.get("created_at"),
                "regeneration_id": latest.get("pk")
            }
        else:
            return {
                "success": True,
                "content_id": content_id,
                "latest_regeneration": None,
                "message": "No regenerated insights found for this content_id"
            }
            
    except Exception as e:
        logger.error(f"Error getting latest regenerated insights: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve latest regenerated insights"
        )


@router.get("/regenerate/implications/{content_id}/latest")
async def get_latest_regenerated_implications(content_id: str):
    """Get the latest regenerated implications for a content_id"""
    try:
        logger.info(f"Getting latest regenerated implications for content_id: {content_id}")
        
        regenerate_service = RegenerateImplicationsService()
        result = await regenerate_service.get_regeneration_history(content_id, limit=1)
        
        if result.get("success") and result.get("regeneration_history"):
            latest = result["regeneration_history"][0]
            return {
                "success": True,
                "content_id": content_id,
                "latest_regeneration": latest,
                "regenerated_at": latest.get("created_at"),
                "regeneration_id": latest.get("pk")
            }
        else:
            return {
                "success": True,
                "content_id": content_id,
                "latest_regeneration": None,
                "message": "No regenerated implications found for this content_id"
            }
            
    except Exception as e:
        logger.error(f"Error getting latest regenerated implications: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve latest regenerated implications"
        ) 