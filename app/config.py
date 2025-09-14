"""
Unified Settings Configuration
Combines all settings from different modules into a single, comprehensive configuration.
"""

import os
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field


class TableNames:
    """Table name management for different environments"""
    
    @staticmethod
    def get_users_table(env: str) -> str:
        return f"users"
    
    @staticmethod
    def get_projects_table(env: str) -> str:
        return f"projects"
    
    @staticmethod
    def get_requests_table(env: str) -> str:
        return f"requests"
    
    @staticmethod
    def get_content_repository_table(env: str) -> str:
        return f"content_repository"


class TableConfig:
    """Table configuration for different environments"""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.table_names = TableNames()


class UnifiedSettings(BaseSettings):
    """
    Unified settings class that combines all configuration needs:
    - FastAPI app settings
    - Agent service settings  
    - API keys and external services
    - Database and storage configurations
    - Environment-specific settings
    """
    
    # ============================================================================
    # PROJECT & ENVIRONMENT CONFIGURATION
    # ============================================================================
    PROJECT_NAME: str = Field(default="NEX Pharma Insights Agent Service")
    VERSION: str = Field(default="1.0.0")
    DESCRIPTION: str = Field(default="AI-powered pharmaceutical market intelligence platform")
    
    # Environment Configuration
    ENVIRONMENT: str = Field(default="local")  # local, development, staging, production
    TABLE_ENVIRONMENT: str = Field(default="local")  # local, dev, staging, prod
    GLOBAL_ENVIRONMENT: str = Field(default="local")  # local, ec2, production - controls AWS service configuration
    DEBUG: bool = Field(default=True)
    
    # ============================================================================
    # SERVER CONFIGURATION
    # ============================================================================
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8005)
    
    # API Configuration
    API_V1_PREFIX: str = Field(default="/api/v1")
    DOCS_URL: str = Field(default="/docs")
    REDOC_URL: str = Field(default="/redoc")
    
    # ============================================================================
    # EXTERNAL API KEYS & CONFIGURATIONS
    # ============================================================================
    # AI/ML Service APIs
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4")
    
    # Bedrock Configuration
    BEDROCK_MOCK_MODE: bool = Field(default=False)
    BEDROCK_AWS_BEDROCK_AGENT_ID: Optional[str] = Field(default=None)
    BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID: Optional[str] = Field(default=None)
    BEDROCK_AWS_REGION: Optional[str] = Field(default=None)
    BEDROCK_AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    BEDROCK_AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    BEDROCK_AWS_SESSION_TOKEN: Optional[str] = Field(default=None)
    
    PERPLEXITY_API_KEY: Optional[str] = Field(default=None)
    SERP_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    
    # ============================================================================
    # AWS & CLOUD CONFIGURATION
    # ============================================================================
    AWS_REGION: str = Field(default="us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default="local")  # Default for local development
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default="local")  # Default for local development
    BEDROCK_MODEL_ID: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")
    
    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    DATABASE_TYPE: str = Field(default="dynamodb")  # dynamodb, sqlite
    DYNAMODB_ENDPOINT: Optional[str] = Field(default="http://localhost:8000")  # Local DynamoDB
    DYNAMODB_REGION: str = Field(default="us-east-1")
    
    # ============================================================================
    # STORAGE CONFIGURATION
    # ============================================================================
    STORAGE_TYPE: str = Field(default="minio")  # "minio" or "s3"
    MINIO_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    S3_BUCKET_NAME: str = Field(default="nex-pharma-insight-s3-bucket")
    
    # ============================================================================
    # SECURITY CONFIGURATION
    # ============================================================================
    SECRET_KEY: str = Field(default="your-secret-key-here-change-in-production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # ============================================================================
    # LOGGING CONFIGURATION
    # ============================================================================
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/app.log")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_MAX_SIZE: int = Field(default=10 * 1024 * 1024)  # 10MB
    LOG_BACKUP_COUNT: int = Field(default=5)
    
    # ============================================================================
    # CORS CONFIGURATION
    # ============================================================================
    CORS_ORIGINS: List[str] = Field(default=[
        "http://localhost:3000", 
        "http://localhost:8000", 
        "http://localhost:8001", 
        "http://localhost:8002", 
        "http://localhost:8005"
    ])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])
    
    # ============================================================================
    # API LIMITS & PAGINATION
    # ============================================================================
    DEFAULT_PAGE_SIZE: int = Field(default=20)
    MAX_PAGE_SIZE: int = Field(default=100)
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_WINDOW: int = Field(default=60)  # seconds
    
    # ============================================================================
    # QUEUE SETTINGS (for backward compatibility)
    # ============================================================================
    queue_poll_interval: int = Field(default=5)  # seconds
    queue_batch_size: int = Field(default=10)
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=60)  # seconds
    
    # Processing Settings
    default_priority: str = Field(default="medium")
    default_processing_strategy: str = Field(default="table")
    default_quality_threshold: float = Field(default=0.8)
    
    # Content Processing
    max_content_size: int = Field(default=10 * 1024 * 1024)  # 10MB
    content_timeout: int = Field(default=30)  # seconds
    
    # ============================================================================
    # COMPUTED PROPERTIES
    # ============================================================================
    @property
    def table_config(self) -> TableConfig:
        """Get table configuration for current environment"""
        return TableConfig(self.TABLE_ENVIRONMENT)
    
    @property
    def USERS_TABLE(self) -> str:
        """Get users table name for current environment"""
        return TableNames.get_users_table(self.TABLE_ENVIRONMENT)
    
    @property
    def projects_table(self) -> str:
        """Get projects table name for current environment"""
        return TableNames.get_projects_table(self.TABLE_ENVIRONMENT)
    
    @property
    def requests_table(self) -> str:
        """Get requests table name for current environment"""
        return TableNames.get_requests_table(self.TABLE_ENVIRONMENT)
    
    @property
    def content_repository_table(self) -> str:
        """Get content repository table name for current environment"""
        return TableNames.get_content_repository_table(self.TABLE_ENVIRONMENT)
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == "local"
    
    @property
    def log_file_path(self) -> str:
        """Get log file path with directory creation"""
        if self.is_development:
            log_file = os.path.join("..", "logs", "app.log")
        else:
            log_file = self.LOG_FILE
        
        # Ensure logs directory exists
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)
        return log_file
    
    # Backward compatibility properties
    @property
    def app_name(self) -> str:
        return self.PROJECT_NAME
    
    @property
    def app_version(self) -> str:
        return self.VERSION
    
    @property
    def debug(self) -> bool:
        return self.DEBUG
    
    @property
    def api_host(self) -> str:
        return self.HOST
    
    @property
    def api_port(self) -> int:
        return self.PORT
    
    @property
    def api_prefix(self) -> str:
        return self.API_V1_PREFIX
    
    @property
    def aws_region(self) -> str:
        return self.AWS_REGION
    
    @property
    def aws_access_key_id(self) -> str:
        return self.AWS_ACCESS_KEY_ID
    
    @property
    def aws_secret_access_key(self) -> str:
        return self.AWS_SECRET_ACCESS_KEY
    
    @property
    def dynamodb_endpoint(self) -> str:
        return self.DYNAMODB_ENDPOINT
    
    @property
    def dynamodb_endpoint_url(self) -> str:
        return self.DYNAMODB_ENDPOINT
    
    @property
    def dynamodb_region(self) -> str:
        return self.DYNAMODB_REGION
    
    @property
    def s3_bucket_name(self) -> str:
        return self.S3_BUCKET_NAME
    
    @property
    def s3_endpoint_url(self) -> Optional[str]:
        """Return S3 endpoint URL based on storage type"""
        if self.STORAGE_TYPE == "minio":
            return f"http://{self.MINIO_ENDPOINT}"
        return None  # For AWS S3, use None
    
    @property
    def bedrock_model_id(self) -> str:
        return self.BEDROCK_MODEL_ID
    
    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY
    
    @property
    def algorithm(self) -> str:
        return self.ALGORITHM
    
    @property
    def access_token_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES
    
    @property
    def log_level(self) -> str:
        return self.LOG_LEVEL
    
    @property
    def log_format(self) -> str:
        return self.LOG_FORMAT
    
    # ============================================================================
    # AWS & STORAGE PROPERTIES
    # ============================================================================
    @property
    def aws_access_key_id(self) -> Optional[str]:
        return self.AWS_ACCESS_KEY_ID
    
    @property
    def aws_secret_access_key(self) -> Optional[str]:
        return self.AWS_SECRET_ACCESS_KEY
    
    @property
    def aws_region(self) -> str:
        return self.AWS_REGION
    
    @property
    def s3_bucket_name(self) -> str:
        return self.S3_BUCKET_NAME
    
    @property
    def dynamodb_endpoint(self) -> Optional[str]:
        return self.DYNAMODB_ENDPOINT
    
    @property
    def dynamodb_region(self) -> str:
        return self.DYNAMODB_REGION
    
    # ============================================================================
    # VALIDATION METHODS
    # ============================================================================
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are present"""
        return {
            "openai": bool(self.OPENAI_API_KEY),
            "perplexity": bool(self.PERPLEXITY_API_KEY),
            "serp": bool(self.SERP_API_KEY),
            "anthropic": bool(self.ANTHROPIC_API_KEY),
            "bedrock_agent_id": bool(self.BEDROCK_AWS_BEDROCK_AGENT_ID),
            "bedrock_agent_alias_id": bool(self.BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID)
        }
    
    def get_missing_api_keys(self) -> List[str]:
        """Get list of missing API keys"""
        validation = self.validate_api_keys()
        return [key for key, is_present in validation.items() if not is_present]
    
    # ============================================================================
    # PYDANTIC CONFIGURATION
    # ============================================================================
    class Config:
        # Try multiple .env file locations - relative to config.py location
        import os
        from pathlib import Path
        
        # Get the directory where config.py is located (app/)
        config_dir = Path(__file__).parent
        
        # Look for .env file in config directory and parent directories
        env_file = [
            str(config_dir / ".env"),           # app/.env
            str(config_dir.parent / ".env"),    # project_root/.env (this is what we want)
            str(config_dir.parent.parent / ".env")  # grandparent/.env
        ]
        case_sensitive = True
        extra = "allow"  # Allow extra properties
        env_file_encoding = 'utf-8'


# ============================================================================
# GLOBAL SETTINGS INSTANCE
# ============================================================================
settings = UnifiedSettings()


# ============================================================================
# SETTINGS VALIDATION ON IMPORT
# ============================================================================
def validate_settings_on_startup():
    """Validate critical settings on application startup"""
    import os
    from pathlib import Path
    
    # Debug environment loading
    print(f"🔍 Current working directory: {Path.cwd()}")
    print(f"🔍 Environment variables loaded: {bool(os.getenv('SERP_API_KEY'))}")
    
    # Check for .env files
    for env_path in [".env", "../.env", "../../.env"]:
        env_file = Path(env_path)
        if env_file.exists():
            print(f"📄 Found .env file: {env_file.absolute()}")
            break
    else:
        print("⚠️  No .env file found in expected locations")
    
    missing_keys = settings.get_missing_api_keys()
    if missing_keys:
        print(f"⚠️  Warning: Missing API keys: {', '.join(missing_keys)}")
        print("💡 Some features may not work without these API keys")
        
        # Additional debugging for SERP key
        if 'serp' in missing_keys:
            print(f"🔍 SERP_API_KEY debug:")
            print(f"   - Settings value: {getattr(settings, 'SERP_API_KEY', 'NOT_FOUND')}")
            print(f"   - Environment value: {os.getenv('SERP_API_KEY', 'NOT_FOUND')}")
    
    print(f"🚀 Settings loaded for environment: {settings.ENVIRONMENT}")
    print(f"📊 Table environment: {settings.TABLE_ENVIRONMENT}")
    print(f"💾 Storage type: {settings.STORAGE_TYPE}")
    print(f"🗄️  Database type: {settings.DATABASE_TYPE}")


# Export critical settings to environment variables for compatibility
def export_to_environment():
    """Export critical settings to environment variables"""
    import os
    
    # Export API keys to environment if they're not already set
    if settings.SERP_API_KEY and not os.getenv('SERP_API_KEY'):
        os.environ['SERP_API_KEY'] = settings.SERP_API_KEY
        
    if settings.OPENAI_API_KEY and not os.getenv('OPENAI_API_KEY'):
        os.environ['OPENAI_API_KEY'] = settings.OPENAI_API_KEY
        
    if settings.PERPLEXITY_API_KEY and not os.getenv('PERPLEXITY_API_KEY'):
        os.environ['PERPLEXITY_API_KEY'] = settings.PERPLEXITY_API_KEY
        
    if settings.ANTHROPIC_API_KEY and not os.getenv('ANTHROPIC_API_KEY'):
        os.environ['ANTHROPIC_API_KEY'] = settings.ANTHROPIC_API_KEY
        
    # Export Bedrock agent configuration
    if settings.BEDROCK_AWS_BEDROCK_AGENT_ID and not os.getenv('BEDROCK_AWS_BEDROCK_AGENT_ID'):
        os.environ['BEDROCK_AWS_BEDROCK_AGENT_ID'] = settings.BEDROCK_AWS_BEDROCK_AGENT_ID
        
    if settings.BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID and not os.getenv('BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID'):
        os.environ['BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID'] = settings.BEDROCK_AWS_BEDROCK_AGENT_ALIAS_ID


# Auto-validate and export on import (optional - can be disabled in production)
if settings.DEBUG:
    validate_settings_on_startup()
    export_to_environment()

# Queue Configuration
QUEUE_TABLES = {
    "request_acceptance": "request_queue_acceptance_queue",
    "serp": "serp_queue", 
    "perplexity": "perplexity_queue",
    "fetch_content": "fetch_content_queue",
    "relevance_check": "relevance_check_queue",
    "insight": "insight_queue",
    "implication": "implication_queue"
}

# Processing Workflow Configuration
QUEUE_WORKFLOW = {
    "request_acceptance": ["serp"],
    "serp": ["perplexity"],
    "perplexity": ["insight", "implication"],  # Perplexity triggers all three in parallel
    "relevance_check": [],  # Relevance check is now a parallel process
    "fetch_content": ["insight", "implication"],  # Keep this for other flows if needed
    "insight": [],
    "implication": []
}

# Queue Processing Limits
QUEUE_PROCESSING_LIMITS = {
    "max_perplexity_urls_per_serp": 3,  # Maximum URLs to send to Perplexity from each SERP result (was 1, now 3 to match code)
    "max_serp_results": 50,  # Maximum search results to process
    "max_insight_items": 10,  # Maximum insight items per request
    "max_implication_items": 10,  # Maximum implication items per request
    "task_delay_seconds": 3  # Delay between processing each queue item (seconds) - restored to 3 for stability
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
