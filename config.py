import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    app_name: str = "Market Intelligence Service"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # AWS Settings
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    
    # DynamoDB Settings
    dynamodb_endpoint_url: Optional[str] = None  # For local development
    
    # S3 Settings
    s3_bucket_name: str = "market-intelligence-bucket"
    s3_endpoint_url: Optional[str] = None  # For local development
    
    # Bedrock Settings
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    # Queue Settings
    queue_poll_interval: int = 5  # seconds
    queue_batch_size: int = 10
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    
    # Processing Settings
    default_priority: str = "medium"
    default_processing_strategy: str = "table"
    default_quality_threshold: float = 0.8
    
    # Content Processing
    max_content_size: int = 10 * 1024 * 1024  # 10MB
    content_timeout: int = 30  # seconds
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Queue Configuration
QUEUE_TABLES = {
    "request_acceptance": "request_queue_acceptance_queue",
    "serp": "serp_queue", 
    "perplexity": "perplexity_queue",
    "fetch_content": "fetch_content_queue",
    "insight": "insight_queue",
    "implication": "implication_queue"
}

# Processing Workflow Configuration
QUEUE_WORKFLOW = {
    "request_acceptance": ["serp"],
    "serp": ["perplexity"],
    "perplexity": ["fetch_content"],
    "fetch_content": ["insight", "implication"],
    "insight": [],
    "implication": []
}

# S3 Storage Paths
S3_PATHS = {
    "raw_content": "raw-content/{project_id}/{request_id}",
    "serp_data": "raw-content/{project_id}/{request_id}/serp",
    "content_data": "raw-content/{project_id}/{request_id}/content",
    "processed": "processed/{project_id}/{request_id}",
    "insights": "processed/{project_id}/{request_id}/insights",
    "implications": "processed/{project_id}/{request_id}/implications",
    "reports": "reports/{project_id}/{request_id}/final"
}

# Queue Status Values
QUEUE_STATUS = {
    "PENDING": "pending",
    "PROCESSING": "processing", 
    "COMPLETED": "completed",
    "FAILED": "failed",
    "RETRY": "retry"
}

# Priority Levels
PRIORITY_LEVELS = {
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low"
}

# Processing Strategies
PROCESSING_STRATEGIES = {
    "TABLE": "table",
    "STREAM": "stream", 
    "BATCH": "batch"
}
