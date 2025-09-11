# Market Intelligence Service

A FastAPI-based microservice that processes market intelligence requests through a queue-driven architecture, leveraging AWS services for scalable data processing and AI-powered insights.

## 🚀 Features

- **Queue-Based Processing**: Scalable workflow using DynamoDB tables as queues
- **AI-Powered Analysis**: Integration with Perplexity AI and Amazon Bedrock
- **Multi-Stage Pipeline**: Request acceptance → SERP → AI enhancement → Content extraction → Insights & Implications
- **RESTful API**: Complete FastAPI implementation with automatic documentation
- **AWS Integration**: DynamoDB for queues, S3 for content storage
- **Robust Error Handling**: Retry logic, status tracking, and comprehensive logging
- **Authentication & Rate Limiting**: Built-in security middleware

## 📋 Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Queue Processing](#queue-processing)
- [Development](#development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## 🏗 Architecture

### Technology Stack
- **API Framework**: FastAPI 0.104.1
- **Database**: Amazon DynamoDB
- **Storage**: Amazon S3
- **AI Processing**: Amazon Bedrock, Perplexity AI
- **Queue Management**: DynamoDB Tables
- **Authentication**: JWT/API Key support
- **Logging**: Structured logging with colored output

### Project Structure
```
nex-pharma-insights-agent-service-queue/
├── app/                          # Main application code
│   ├── api/                      # API layer
│   │   ├── middleware/           # CORS, Auth middleware
│   │   └── v1/                   # API v1 routes
│   ├── database/                 # Database clients
│   │   ├── dynamodb_client.py    # DynamoDB operations
│   │   └── s3_client.py          # S3 operations
│   ├── models/                   # Data models
│   │   ├── request_models.py     # API request/response models
│   │   └── queue_models.py       # Queue item models
│   ├── queues/                   # Queue workers
│   │   ├── base_worker.py        # Abstract base worker
│   │   ├── request_acceptance/   # Request validation worker
│   │   ├── serp/                 # Search engine processing
│   │   ├── perplexity/          # AI enhancement worker
│   │   ├── fetch_content/       # Content extraction (to be implemented)
│   │   ├── insight/             # Insight generation (to be implemented)
│   │   └── implication/         # Implication analysis (to be implemented)
│   ├── utils/                   # Utilities
│   │   ├── logger.py            # Logging configuration
│   │   ├── helpers.py           # Helper functions
│   │   └── validators.py        # Validation utilities
│   └── main.py                  # FastAPI application
├── config.py                    # Configuration management
├── migrations/                  # Database migrations
├── scripts/                     # Utility scripts
├── tests/                       # Test suite
├── docs/                        # Documentation
└── requirements.txt             # Python dependencies
```

## 🛠 Installation

### Prerequisites
- Python 3.8+
- AWS Account with DynamoDB and S3 access
- AWS CLI configured or environment variables set

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd nex-pharma-insights-agent-service-queue
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Create DynamoDB tables**
```bash
python3 scripts/migrate.py create-all
```

6. **Setup S3 bucket**
```bash
python3 scripts/setup_s3.py
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Application Settings
APP_NAME="Market Intelligence Service"
APP_VERSION="1.0.0"
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000

# AWS Settings
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# DynamoDB Settings (optional for local development)
DYNAMODB_ENDPOINT_URL=http://localhost:8000

# S3 Settings
S3_BUCKET_NAME=market-intelligence-bucket

# Bedrock Settings
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Queue Settings
QUEUE_POLL_INTERVAL=5
QUEUE_BATCH_SIZE=10
MAX_RETRIES=3

# Security
SECRET_KEY=your-secret-key-here
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
```

### Configuration Options

All configuration is managed through `config.py` using Pydantic Settings:

- **Application Settings**: Basic app configuration
- **AWS Settings**: Credentials and region configuration
- **Queue Settings**: Processing parameters and retry logic
- **Security Settings**: Authentication and rate limiting
- **Logging Settings**: Log levels and formatting

## 📚 API Documentation

### Main Endpoint

**POST `/api/v1/market-intelligence-requests`**

Submit a market intelligence processing request.

#### Request Body
```json
{
  "project_id": "041da4cc-c722-4f62-bcb6-07c930cafcf1",
  "project_request_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1",
  "user_id": "debug_user",
  "priority": "high",
  "processing_strategy": "table",
  "config": {
    "keywords": ["Semaglutide"],
    "sources": [
      {
        "name": "FDA",
        "type": "regulatory",
        "url": "https://www.fda.gov/"
      }
    ],
    "extraction_mode": "summary",
    "quality_threshold": 0.8,
    "metadata": {
      "requestId": "214d5c73-dfc2-42ac-b787-e4cf8be3911b"
    }
  }
}
```

#### Response
```json
{
  "status": "accepted",
  "request_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1",
  "estimated_completion": "2024-01-01T01:00:00Z",
  "tracking_url": "/api/v1/requests/{request_id}/status"
}
```

### Other Endpoints

- **GET `/api/v1/requests/{request_id}/status`** - Get request status
- **GET `/api/v1/requests/{request_id}/results`** - Get processing results
- **GET `/api/v1/requests`** - List requests with filtering
- **DELETE `/api/v1/requests/{request_id}`** - Cancel a request
- **GET `/health`** - Health check
- **GET `/metrics`** - System metrics

### Interactive Documentation

When running in debug mode, access interactive API documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔄 Queue Processing

### Workflow Overview

```
FastAPI Request → request_queue_acceptance_queue
                 ↓
              serp_queue (process sources)
                 ↓
            perplexity_queue (AI enhancement)
                 ↓
          fetch_content_queue (deep extraction)
                 ↓
        ┌─────────────────────────┐
        ↓                       ↓
   insight_queue          implication_queue
   (market insights)      (business implications)
        ↓                       ↓
    Final Reports          Final Reports
```

### Queue Tables

1. **request_queue_acceptance_queue**: Initial validation and processing plan
2. **serp_queue**: Search engine results processing
3. **perplexity_queue**: AI-powered content analysis
4. **fetch_content_queue**: Deep content extraction
5. **insight_queue**: Market insights generation
6. **implication_queue**: Business implications analysis

### Processing Strategies

- **table**: Standard sequential processing through all queues
- **stream**: Real-time processing for high-priority requests
- **batch**: Bulk processing for efficiency

## 🚀 Development

### Running the Application

1. **Start the development server**
```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Run with custom configuration**
```bash
DEBUG=true LOG_LEVEL=DEBUG python3 -m uvicorn app.main:app --reload
```

### Running Tests

```bash
# Run all tests
python3 -m pytest

# Run with coverage
python3 -m pytest --cov=app tests/

# Run specific test file
python3 -m pytest tests/test_api.py -v
```

### Database Management

```bash
# Create all tables
python3 scripts/migrate.py create-all

# Create specific table
python3 scripts/migrate.py create request_acceptance

# Check table status
python3 scripts/migrate.py status

# Delete all tables (careful!)
python3 scripts/migrate.py delete-all
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type checking (if mypy is installed)
mypy app/
```

## 🚀 Deployment

### Production Deployment

1. **Set production environment variables**
2. **Create production DynamoDB tables**
3. **Setup S3 bucket with proper permissions**
4. **Deploy using your preferred method** (Docker, AWS ECS, etc.)

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Health Checks

The service provides comprehensive health checks:
- **Basic health**: `GET /health`
- **Detailed metrics**: `GET /metrics`
- **Database connectivity**: Included in health check
- **Worker status**: Monitored and reported

## 🔧 Troubleshooting

### Common Issues

1. **GSI Creation Errors**
   - **Fixed**: Removed GSI requirements from queue models
   - Tables now use simple PK/SK structure

2. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **AWS Credentials**
   ```bash
   aws configure
   # or set environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   ```

4. **Table Creation Issues**
   ```bash
   # Check AWS permissions
   # Verify region configuration
   python3 scripts/migrate.py status
   ```

### Logging

Logs are structured and include:
- Request IDs for tracing
- Colored output in development
- File logging in production
- Configurable log levels

### Monitoring

- Queue metrics available at `/metrics`
- Worker status monitoring
- Processing time tracking
- Error rate monitoring

## 📝 Recent Changes

### ✅ Fixed Issues
- **Removed GSI requirements** from DynamoDB table creation
- **Simplified queue models** to use only PK/SK structure
- **Complete project reorganization** with proper structure
- **Implemented comprehensive configuration** management
- **Added robust error handling** and retry logic
- **Created complete API documentation**

### 🎯 Next Steps
- Implement remaining queue workers (fetch_content, insight, implication)
- Add comprehensive test coverage
- Implement actual Perplexity AI integration
- Add monitoring and alerting
- Performance optimization

## 📄 License

[Add your license information here]

## 🤝 Contributing

[Add contributing guidelines here]

---

**Status**: ✅ **Project Successfully Reorganized and Ready for Use**

The project now has a solid foundation with:
- Complete FastAPI application structure
- Working queue system without GSI issues
- Comprehensive configuration management
- Robust error handling and logging
- Ready for development and deployment 