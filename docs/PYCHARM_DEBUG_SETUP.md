# PyCharm Debugging Setup Guide

This guide shows you how to set up PyCharm for debugging your NEX Pharma Insights Agent Service with the current configuration.

## 🎯 PyCharm Configuration

### 1. **Project Setup**

#### Open Project in PyCharm
```bash
# Open PyCharm and select:
# File > Open > /path/to/nex-pharma-insights-agent-service-queue
```

#### Configure Python Interpreter
1. **File** → **Settings** → **Project** → **Python Interpreter**
2. **Add Interpreter** → **Existing Environment**
3. **Interpreter Path**: `/path/to/your-project/.venv/bin/python`
4. **Apply** and **OK**

### 2. **Run/Debug Configurations**

#### Main FastAPI Application
**Run** → **Edit Configurations** → **+** → **Python**

```
Name: NEX Pharma Service
Script path: /path/to/your-project/app/main.py
Parameters: (leave empty)
Python interpreter: Project Default (.venv)
Working directory: /path/to/your-project
Environment variables:
  - PYTHONPATH=/path/to/your-project
  - ENVIRONMENT=local
```

#### Alternative: Uvicorn Server
**Run** → **Edit Configurations** → **+** → **Python**

```
Name: NEX Pharma Uvicorn
Module name: uvicorn
Parameters: app.main:app --reload --host 0.0.0.0 --port 8005 --log-level debug
Python interpreter: Project Default (.venv)
Working directory: /path/to/your-project
Environment variables:
  - PYTHONPATH=/path/to/your-project
  - ENVIRONMENT=local
```

#### Individual Queue Workers
**Run** → **Edit Configurations** → **+** → **Python**

```
Name: Test Request Acceptance Worker
Script path: /path/to/your-project/app/queues/request_acceptance/worker.py
Parameters: (leave empty)
Python interpreter: Project Default (.venv)
Working directory: /path/to/your-project
```

#### Test Scripts
```
Name: Local Setup Test
Script path: /path/to/your-project/deployment/test_local_setup.py
Python interpreter: Project Default (.venv)
Working directory: /path/to/your-project
```

### 3. **Environment Configuration**

#### Create `.env` for Local Development
Create/edit `.env` file in project root:

```env
# ============================================================================
# PYCHARM DEBUGGING ENVIRONMENT
# ============================================================================

# Application Settings
ENVIRONMENT=local
TABLE_ENVIRONMENT=local
DEBUG=true
HOST=0.0.0.0
PORT=8005

# AWS Configuration (for local development)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-dev-access-key
AWS_SECRET_ACCESS_KEY=your-dev-secret-key

# Database Configuration
DATABASE_TYPE=dynamodb
DYNAMODB_ENDPOINT=http://localhost:8000  # Local DynamoDB
DYNAMODB_REGION=us-east-1

# Storage Configuration  
STORAGE_TYPE=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
S3_BUCKET_NAME=dev-agent-content-bucket

# External API Keys (Add your actual keys)
PERPLEXITY_API_KEY=your-perplexity-api-key
SERP_API_KEY=your-serp-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Bedrock Configuration
BEDROCK_MOCK_MODE=false
BEDROCK_AWS_REGION=us-east-1
BEDROCK_AWS_ACCESS_KEY_ID=your-bedrock-access-key
BEDROCK_AWS_SECRET_ACCESS_KEY=your-bedrock-secret-key

# Security
SECRET_KEY=dev-secret-key-for-debugging
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging (Enhanced for debugging)
LOG_LEVEL=DEBUG
```

## 🐛 Debugging Strategies

### 1. **FastAPI Application Debugging**

#### Set Breakpoints
- **Main Application**: `app/main.py` - lifespan function, route handlers
- **API Routes**: `app/api/v1/routes.py` - request processing
- **Queue Workers**: Individual worker files for queue processing
- **Database Clients**: `app/database/` - AWS service interactions

#### Debug FastAPI Server
1. **Set breakpoints** in your code
2. **Run** → **Debug 'NEX Pharma Service'**
3. **Access endpoints**: `http://localhost:8005/docs`
4. **Make API calls** to trigger breakpoints

### 2. **Queue Worker Debugging**

#### Individual Worker Testing
```python
# Create a test file: debug_worker.py
import asyncio
from app.queues.request_acceptance.worker import RequestAcceptanceWorker

async def debug_worker():
    worker = RequestAcceptanceWorker()
    
    # Set breakpoints here
    test_item = {
        "PK": "PROJECT#test-project",
        "SK": "REQUEST#test-request",
        "payload": {
            "project_id": "test-project",
            "user_id": "debug_user",
            "config": {"keywords": ["test"]}
        }
    }
    
    # Debug process_item method
    result = await worker.process_item(test_item)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(debug_worker())
```

#### Debug Configuration
```
Name: Debug Worker
Script path: /path/to/your-project/debug_worker.py
Python interpreter: Project Default (.venv)
Working directory: /path/to/your-project
```

### 3. **Database & AWS Service Debugging**

#### Test AWS Clients
```python
# Create: debug_aws.py
from app.database.dynamodb_client import DynamoDBClient
from app.database.s3_client import S3Client

def debug_aws_clients():
    # Set breakpoints here
    dynamodb_client = DynamoDBClient()
    s3_client = S3Client()
    
    # Test operations
    print("DynamoDB client created")
    print("S3 client created")

if __name__ == "__main__":
    debug_aws_clients()
```

### 4. **Configuration Debugging**

#### Test Configuration Loading
```python
# Create: debug_config.py
from config import settings

def debug_configuration():
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug mode: {settings.DEBUG}")
    print(f"AWS Region: {settings.AWS_REGION}")
    print(f"Database Type: {settings.DATABASE_TYPE}")
    print(f"Storage Type: {settings.STORAGE_TYPE}")
    
    # Check API keys (without printing sensitive data)
    print(f"Has Perplexity Key: {bool(settings.PERPLEXITY_API_KEY)}")
    print(f"Has SERP Key: {bool(settings.SERP_API_KEY)}")

if __name__ == "__main__":
    debug_configuration()
```

## 🧪 Testing & Debugging Workflow

### 1. **Start Local Services** (Optional)
```bash
# Terminal 1: Local DynamoDB (if needed)
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000

# Terminal 2: MinIO (if needed)
./minio server ./data --console-address ":9001"
```

### 2. **PyCharm Debugging Steps**

#### Step 1: Set Breakpoints
- **API Endpoints**: Set breakpoints in route handlers
- **Queue Processing**: Set breakpoints in worker `process_item` methods
- **AWS Operations**: Set breakpoints in database client methods
- **Configuration**: Set breakpoints in settings loading

#### Step 2: Start Debug Session
1. **Select configuration**: "NEX Pharma Service" or "NEX Pharma Uvicorn"
2. **Click Debug button** (🐛)
3. **Wait for server startup**
4. **Access**: `http://localhost:8005/docs`

#### Step 3: Trigger Breakpoints
- **API Testing**: Use Swagger UI at `/docs`
- **Direct Requests**: Use PyCharm HTTP Client or Postman
- **Queue Testing**: Run individual worker debug scripts

### 3. **Common Debugging Scenarios**

#### Debug API Request Flow
```python
# Set breakpoints in:
# 1. app/api/v1/routes.py - submit_market_intelligence_request()
# 2. app/queues/request_acceptance/worker.py - process_item()
# 3. app/database/dynamodb_client.py - put_item()

# Then make API request via Swagger UI
```

#### Debug Queue Processing
```python
# Set breakpoints in:
# 1. app/queues/base_worker.py - poll_queue()
# 2. Specific worker process_item() methods
# 3. Database operations

# Run individual worker or full service
```

#### Debug AWS Integration
```python
# Set breakpoints in:
# 1. app/database/dynamodb_client.py - __init__()
# 2. app/database/s3_client.py - __init__()
# 3. Bedrock service initialization

# Check credential resolution and client creation
```

## 🔧 PyCharm Debugging Features

### 1. **Variable Inspection**
- **Hover over variables** to see values
- **Variables panel** shows current scope
- **Evaluate expressions** in debug console

### 2. **Step Through Code**
- **Step Over** (F8): Execute current line
- **Step Into** (F7): Enter function calls
- **Step Out** (Shift+F8): Exit current function
- **Resume** (F9): Continue execution

### 3. **Debug Console**
```python
# In debug console, you can:
# - Inspect variables: print(settings.ENVIRONMENT)
# - Call functions: worker.get_queue_metrics()
# - Modify state: item['status'] = 'debug'
```

### 4. **Conditional Breakpoints**
- **Right-click breakpoint** → **More** → **Condition**
- **Example**: `item.get('project_id') == 'test-project'`

## 📊 Monitoring & Logging

### 1. **Enhanced Logging for Debug**
```python
# In your code, add detailed logging:
import logging
logger = logging.getLogger(__name__)

def your_function():
    logger.debug(f"Processing item: {item}")
    logger.debug(f"Current state: {state}")
    # Your code here
    logger.debug(f"Result: {result}")
```

### 2. **PyCharm Log Viewer**
- **View** → **Tool Windows** → **Run**
- **Console tab** shows application logs
- **Filter logs** by level (DEBUG, INFO, ERROR)

### 3. **Real-time Monitoring**
```python
# Add to your debug session:
def monitor_queue_status():
    from app.database.dynamodb_client import DynamoDBClient
    client = DynamoDBClient()
    
    # Check queue items
    items = client.scan_items("request_queue_acceptance_queue")
    print(f"Queue items: {len(items)}")
    
    return items
```

## 🎯 Quick Debug Commands

### PyCharm Terminal (Alt+F12)
```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
python deployment/test_local_setup.py

# Check configuration
python -c "from config import settings; print(f'Env: {settings.ENVIRONMENT}')"

# Test individual components
python -c "from app.database.dynamodb_client import DynamoDBClient; print('DynamoDB OK')"

# Run specific worker
python -m app.queues.request_acceptance.worker
```

### HTTP Client Testing
Create `.http` files in PyCharm:

```http
### Health Check
GET http://localhost:8005/health

### Submit Request
POST http://localhost:8005/api/v1/market-intelligence-requests
Content-Type: application/json

{
  "project_id": "debug-project",
  "project_request_id": "debug-request",
  "user_id": "debug_user",
  "priority": "high",
  "processing_strategy": "table",
  "config": {
    "keywords": ["debug"],
    "sources": [{"name": "Debug Source", "type": "regulatory", "url": "https://example.com"}],
    "extraction_mode": "summary",
    "quality_threshold": 0.8
  }
}
```

## 🚀 Pro Tips

### 1. **Efficient Debugging**
- **Use conditional breakpoints** for specific scenarios
- **Debug individual components** before full integration
- **Keep debug scripts** for common testing scenarios
- **Use PyCharm's HTTP client** for API testing

### 2. **Configuration Management**
- **Separate debug configs** from production
- **Use environment variables** for sensitive data
- **Test with different environments** (local, dev, staging)

### 3. **Performance Debugging**
- **Profile code** using PyCharm's profiler
- **Monitor memory usage** in debug sessions
- **Check async operations** with proper await handling

---

**🎉 You're now ready to debug your NEX Pharma Insights Agent Service efficiently in PyCharm!** 