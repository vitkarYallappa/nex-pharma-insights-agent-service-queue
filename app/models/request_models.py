from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid


class SourceConfig(BaseModel):
    """Configuration for a data source"""
    name: str = Field(..., description="Source name (e.g., 'FDA')")
    type: str = Field(..., description="Source type (e.g., 'regulatory')")
    url: str = Field(..., description="Source URL")


class RequestConfig(BaseModel):
    """Configuration for market intelligence request"""
    keywords: List[str] = Field(..., description="Keywords to search for")
    sources: List[SourceConfig] = Field(..., description="Data sources to process")
    extraction_mode: str = Field(default="summary", description="Content extraction mode")
    quality_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Quality threshold for content filtering")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('extraction_mode')
    def validate_extraction_mode(cls, v):
        allowed_modes = ['summary', 'full', 'structured']
        if v not in allowed_modes:
            raise ValueError(f'extraction_mode must be one of {allowed_modes}')
        return v


class MarketIntelligenceRequest(BaseModel):
    """Main request model for market intelligence processing"""
    project_id: str = Field(..., description="Unique project identifier")
    project_request_id: str = Field(..., description="Unique request identifier")
    user_id: str = Field(..., description="User identifier")
    priority: str = Field(default="medium", description="Processing priority")
    processing_strategy: str = Field(default="table", description="Processing strategy")
    config: RequestConfig = Field(..., description="Request configuration")
    
    @validator('priority')
    def validate_priority(cls, v):
        allowed_priorities = ['high', 'medium', 'low']
        if v not in allowed_priorities:
            raise ValueError(f'priority must be one of {allowed_priorities}')
        return v
    
    @validator('processing_strategy')
    def validate_processing_strategy(cls, v):
        allowed_strategies = ['table', 'stream', 'batch']
        if v not in allowed_strategies:
            raise ValueError(f'processing_strategy must be one of {allowed_strategies}')
        return v


class RequestResponse(BaseModel):
    """Response model for request submission"""
    status: str = Field(..., description="Request status")
    request_id: str = Field(..., description="Request identifier")
    estimated_completion: datetime = Field(..., description="Estimated completion time")
    tracking_url: str = Field(..., description="URL to track request status")


class RequestStatus(BaseModel):
    """Model for request status tracking"""
    request_id: str
    project_id: str
    status: str
    progress: Dict[str, str]  # queue_name -> status
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None


class QueueItem(BaseModel):
    """Base model for queue items"""
    PK: str = Field(..., description="Partition key: project_id#project_request_id")
    SK: str = Field(..., description="Sort key: queue_name#timestamp")
    status: str = Field(default="pending", description="Processing status")
    priority: str = Field(default="medium", description="Processing priority")
    processing_strategy: str = Field(default="table", description="Processing strategy")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict, description="Queue-specific data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    def generate_keys(self, project_id: str, project_request_id: str, queue_name: str) -> None:
        """Generate partition and sort keys"""
        self.PK = f"{project_id}#{project_request_id}"
        self.SK = f"{queue_name}#{int(datetime.utcnow().timestamp())}"


class RequestAcceptancePayload(BaseModel):
    """Payload for request acceptance queue"""
    original_request: MarketIntelligenceRequest
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    processing_plan: List[str] = Field(default_factory=list)


class SerpPayload(BaseModel):
    """Payload for SERP queue"""
    keywords: List[str]
    sources: List[SourceConfig]
    search_queries: List[str] = Field(default_factory=list)
    search_results: List[Dict[str, Any]] = Field(default_factory=list)


class PerplexityPayload(BaseModel):
    """Payload for Perplexity queue"""
    search_data: Dict[str, Any]
    analysis_prompt: str
    enhanced_data: Dict[str, Any] = Field(default_factory=dict)


class FetchContentPayload(BaseModel):
    """Payload for content fetch queue"""
    urls: List[str]
    extraction_mode: str = "summary"
    quality_threshold: float = 0.8
    content_data: List[Dict[str, Any]] = Field(default_factory=list)


class InsightPayload(BaseModel):
    """Payload for insight generation queue"""
    content_references: List[str]  # S3 paths to content
    analysis_type: str = "market_insights"
    insights: Dict[str, Any] = Field(default_factory=dict)


class ImplicationPayload(BaseModel):
    """Payload for implication analysis queue"""
    content_references: List[str]  # S3 paths to content
    analysis_type: str = "business_implications"
    implications: Dict[str, Any] = Field(default_factory=dict)
