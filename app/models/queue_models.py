from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class QueueStatus(str, Enum):
    """Queue processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class Priority(str, Enum):
    """Priority level enumeration"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProcessingStrategy(str, Enum):
    """Processing strategy enumeration"""
    TABLE = "table"
    STREAM = "stream"
    BATCH = "batch"


class BaseQueueModel(BaseModel):
    """Base model for all queue items"""
    PK: str = Field(..., description="Partition key")
    SK: str = Field(..., description="Sort key")
    
    status: QueueStatus = Field(default=QueueStatus.PENDING)
    priority: Priority = Field(default=Priority.MEDIUM)
    processing_strategy: ProcessingStrategy = Field(default=ProcessingStrategy.TABLE)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    error_message: Optional[str] = Field(None)
    
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class RequestAcceptanceQueue(BaseQueueModel):
    """Model for request acceptance queue items"""
    
    def __init__(self, project_id: str, project_request_id: str, **data):
        # Set keys
        data['PK'] = f"{project_id}#{project_request_id}"
        data['SK'] = f"request_acceptance#{int(datetime.utcnow().timestamp())}"
        super().__init__(**data)


class SerpQueue(BaseQueueModel):
    """Model for SERP processing queue items"""
    
    def __init__(self, project_id: str, project_request_id: str, **data):
        data['PK'] = f"{project_id}#{project_request_id}"
        data['SK'] = f"serp#{int(datetime.utcnow().timestamp())}"
        super().__init__(**data)


class PerplexityQueue(BaseQueueModel):
    """Model for Perplexity AI processing queue items"""
    
    def __init__(self, project_id: str, project_request_id: str, **data):
        data['PK'] = f"{project_id}#{project_request_id}"
        data['SK'] = f"perplexity#{int(datetime.utcnow().timestamp())}"
        super().__init__(**data)


class FetchContentQueue(BaseQueueModel):
    """Model for content fetching queue items"""
    
    def __init__(self, project_id: str, project_request_id: str, **data):
        data['PK'] = f"{project_id}#{project_request_id}"
        data['SK'] = f"fetch_content#{int(datetime.utcnow().timestamp())}"
        super().__init__(**data)


class InsightQueue(BaseQueueModel):
    """Model for insight generation queue items"""
    
    def __init__(self, project_id: str, project_request_id: str, **data):
        data['PK'] = f"{project_id}#{project_request_id}"
        data['SK'] = f"insight#{int(datetime.utcnow().timestamp())}"
        super().__init__(**data)


class ImplicationQueue(BaseQueueModel):
    """Model for implication analysis queue items"""
    
    def __init__(self, project_id: str, project_request_id: str, **data):
        data['PK'] = f"{project_id}#{project_request_id}"
        data['SK'] = f"implication#{int(datetime.utcnow().timestamp())}"
        super().__init__(**data)


class RelevanceCheckQueue(BaseQueueModel):
    """Model for relevance check queue items"""
    
    def __init__(self, project_id: str, project_request_id: str, **data):
        data['PK'] = f"{project_id}#{project_request_id}"
        data['SK'] = f"relevance_check#{int(datetime.utcnow().timestamp())}"
        super().__init__(**data)


# Queue model mapping for factory pattern
QUEUE_MODELS = {
    "request_acceptance": RequestAcceptanceQueue,
    "serp": SerpQueue,
    "perplexity": PerplexityQueue,
    "fetch_content": FetchContentQueue,
    "relevance_check": RelevanceCheckQueue,
    "insight": InsightQueue,
    "implication": ImplicationQueue
}


class QueueItemFactory:
    """Factory for creating queue items"""
    
    @staticmethod
    def create_queue_item(queue_name: str, project_id: str, project_request_id: str, **kwargs) -> BaseQueueModel:
        """Create a queue item of the specified type"""
        if queue_name not in QUEUE_MODELS:
            raise ValueError(f"Unknown queue type: {queue_name}")
        
        model_class = QUEUE_MODELS[queue_name]
        return model_class(project_id=project_id, project_request_id=project_request_id, **kwargs)


class QueueMetrics(BaseModel):
    """Model for queue metrics and monitoring"""
    queue_name: str
    pending_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    retry_count: int = 0
    average_processing_time: Optional[float] = None
    last_processed: Optional[datetime] = None
    
    @property
    def total_items(self) -> int:
        return self.pending_count + self.processing_count + self.completed_count + self.failed_count
    
    @property
    def success_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.completed_count / self.total_items
