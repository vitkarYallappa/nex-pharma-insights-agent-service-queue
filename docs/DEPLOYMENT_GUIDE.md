# NEX Pharma Insights Agent Service - Deployment Guide

This guide provides comprehensive instructions for deploying the NEX Pharma Insights Agent Service in both **Production (AWS EC2)** and **Development (Local)** environments.

## 📋 Table of Contents

- [Overview](#overview)
- [Production Deployment (AWS EC2)](#production-deployment-aws-ec2)
- [Development Setup (Local)](#development-setup-local)
- [Environment Configuration](#environment-configuration)
- [Testing & Verification](#testing--verification)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

---

## 🎯 Overview

The NEX Pharma Insights Agent Service is a FastAPI-based microservice that processes market intelligence requests through a queue-driven architecture. It integrates with:

- **AWS DynamoDB** - Queue management and data storage
- **AWS S3** - Content storage
- **AWS Bedrock** - AI-powered analysis
- **External APIs** - Perplexity AI, SERP API

### Key Features
- ✅ **IAM Instance Role Support** - Secure AWS authentication without hardcoded credentials
- ✅ **Queue-Based Processing** - Scalable workflow with 6 specialized workers
- ✅ **Environment-Specific Configuration** - Separate configs for prod/dev
- ✅ **Comprehensive Health Checks** - Monitoring and diagnostics
- ✅ **Systemd Integration** - Production-ready service management

---

## 🚀 Production Deployment (AWS EC2)

### Prerequisites

#### AWS Infrastructure
- **EC2 Instance** (t3.medium or larger recommended)
- **IAM Instance Role** with required permissions
- **Security Group** allowing inbound traffic on port 8005
- **DynamoDB Tables** created in target region
- **S3 Bucket** for content storage

#### Required IAM Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:ListTables",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeAgent",
                "bedrock:InvokeModel"
            ],
            "Resource": "*"
        }
    ]
}
```

### Step 1: Prepare EC2 Instance

```bash
# Connect to your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Git (if not already installed)
sudo apt install git -y
```

### Step 2: Clone and Deploy

```bash
# Clone the repository
git clone <your-repository-url>
cd nex-pharma-insights-agent-service-queue

# Make deployment script executable
chmod +x deployment/deploy.sh

# Run deployment (requires sudo)
sudo ./deployment/deploy.sh
```

### Step 3: Configure Production Environment

```bash
# Edit the production configuration
sudo nano /opt/nex-pharma-insights/.env

# Update the following values:
# - PERPLEXITY_API_KEY=your-actual-perplexity-key
# - SERP_API_KEY=your-actual-serp-key  
# - ANTHROPIC_API_KEY=your-actual-anthropic-key
# - SECRET_KEY=your-production-secret-key
# - S3_BUCKET_NAME=your-actual-bucket-name
```

### Step 4: Create Database Tables

```bash
# Switch to service directory
cd /opt/nex-pharma-insights/app

# Create DynamoDB tables
sudo -u nex-pharma /opt/nex-pharma-insights/venv/bin/python scripts/migrate.py create-all
```

### Step 5: Start and Verify Service

```bash
# Start the service
sudo systemctl start nex-pharma-insights

# Check service status
sudo systemctl status nex-pharma-insights

# View logs
sudo journalctl -u nex-pharma-insights -f

# Test health endpoint
curl http://localhost:8005/health
```

### Production Service Management

```bash
# Service Control
sudo systemctl start nex-pharma-insights     # Start service
sudo systemctl stop nex-pharma-insights      # Stop service  
sudo systemctl restart nex-pharma-insights   # Restart service
sudo systemctl reload nex-pharma-insights    # Reload configuration

# Monitoring
sudo systemctl status nex-pharma-insights    # Service status
sudo journalctl -u nex-pharma-insights -f    # Live logs
sudo journalctl -u nex-pharma-insights --since "1 hour ago"  # Recent logs

# Configuration
sudo nano /opt/nex-pharma-insights/.env      # Edit environment
sudo systemctl daemon-reload                 # Reload systemd after changes
```

---

## 💻 Development Setup (Local)

### Prerequisites

- **Python 3.8+** installed
- **Git** installed
- **Virtual environment** support
- **Local DynamoDB** (optional, for full testing)
- **MinIO** (optional, for S3-compatible storage)

### Step 1: Clone Repository

```bash
# Clone the repository
git clone <your-repository-url>
cd nex-pharma-insights-agent-service-queue
```

### Step 2: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Development Environment

```bash
# Copy example environment file (if exists)
cp .env.example .env  # Or create new .env file

# Edit configuration
nano .env
```

**Development `.env` Configuration:**
```env
# ============================================================================
# DEVELOPMENT ENVIRONMENT CONFIGURATION
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

# External API Keys
PERPLEXITY_API_KEY=your-perplexity-api-key
SERP_API_KEY=your-serp-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Bedrock Configuration
BEDROCK_MOCK_MODE=false
BEDROCK_AWS_REGION=us-east-1
BEDROCK_AWS_ACCESS_KEY_ID=your-bedrock-access-key
BEDROCK_AWS_SECRET_ACCESS_KEY=your-bedrock-secret-key

# Security
SECRET_KEY=dev-secret-key-change-in-production
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=DEBUG
```

### Step 4: Setup Local Services (Optional)

#### Option A: Local DynamoDB
```bash
# Download and run local DynamoDB
wget https://s3.us-west-2.amazonaws.com/dynamodb-local/dynamodb_local_latest.tar.gz
tar -xzf dynamodb_local_latest.tar.gz
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000
```

#### Option B: MinIO (S3-compatible storage)
```bash
# Download and run MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server ./data --console-address ":9001"
```

### Step 5: Run Development Server

```bash
# Activate virtual environment
source .venv/bin/activate

# Run development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8005

# Or use the built-in runner
python app/main.py
```

### Development Workflow

```bash
# Run tests
python deployment/test_local_setup.py

# Check code quality
black app/ tests/
isort app/ tests/

# Run specific tests
python -m pytest tests/ -v

# View API documentation
# Open browser: http://localhost:8005/docs
```

---

## ⚙️ Environment Configuration

### Configuration Files

| Environment | Config File | Description |
|-------------|-------------|-------------|
| **Production** | `deployment/production.env` | EC2 with IAM roles |
| **Development** | `.env` | Local development |
| **Testing** | `.env.test` | Testing environment |

### Key Configuration Differences

| Setting | Production | Development |
|---------|------------|-------------|
| **AWS Credentials** | IAM Instance Role | Explicit keys |
| **Database** | AWS DynamoDB | Local DynamoDB |
| **Storage** | AWS S3 | MinIO |
| **Debug Mode** | `false` | `true` |
| **Log Level** | `INFO` | `DEBUG` |
| **Workers** | All enabled | All enabled |

### Environment Variables Reference

#### Core Application
- `ENVIRONMENT` - Environment name (local/development/production)
- `DEBUG` - Enable debug mode (true/false)
- `HOST` - Server bind address (0.0.0.0)
- `PORT` - Server port (8005)

#### AWS Configuration
- `AWS_REGION` - AWS region (us-east-1)
- `AWS_ACCESS_KEY_ID` - Access key (leave empty for IAM role)
- `AWS_SECRET_ACCESS_KEY` - Secret key (leave empty for IAM role)

#### Database
- `DATABASE_TYPE` - Database type (dynamodb)
- `DYNAMODB_ENDPOINT` - DynamoDB endpoint (empty for AWS)
- `TABLE_ENVIRONMENT` - Table name prefix (local/dev/prod)

#### Storage
- `STORAGE_TYPE` - Storage type (s3/minio)
- `S3_BUCKET_NAME` - Bucket name
- `S3_ENDPOINT_URL` - S3 endpoint (empty for AWS)

#### External APIs
- `PERPLEXITY_API_KEY` - Perplexity AI API key
- `SERP_API_KEY` - SERP API key
- `ANTHROPIC_API_KEY` - Anthropic API key

---

## 🧪 Testing & Verification

### Production Testing

```bash
# Test IAM role compatibility (on EC2)
python deployment/test_iam_compatibility.py

# Test service health
curl http://localhost:8005/health

# Test API endpoints
curl http://localhost:8005/
curl http://localhost:8005/metrics

# Submit test request
curl -X POST http://localhost:8005/api/v1/market-intelligence-requests \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test-project",
    "project_request_id": "test-request",
    "user_id": "test_user",
    "priority": "high",
    "processing_strategy": "table",
    "config": {
      "keywords": ["test"],
      "sources": [{"name": "Test", "type": "regulatory", "url": "https://example.com"}],
      "extraction_mode": "summary",
      "quality_threshold": 0.8
    }
  }'
```

### Development Testing

```bash
# Run local setup test
python deployment/test_local_setup.py

# Run unit tests
python -m pytest tests/ -v

# Test with sample data
python test_flow.py
```

### Health Check Endpoints

| Endpoint | Description | Expected Response |
|----------|-------------|-------------------|
| `/health` | Service health status | 200 (healthy) or 503 (degraded) |
| `/metrics` | System metrics | Worker status, queue metrics |
| `/` | Root endpoint | Service info and version |
| `/docs` | API documentation | Swagger UI (debug mode only) |

---

## 🔧 Troubleshooting

### Common Production Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status nex-pharma-insights

# View detailed logs
sudo journalctl -u nex-pharma-insights --no-pager

# Check configuration
sudo -u nex-pharma cat /opt/nex-pharma-insights/.env

# Test configuration
sudo -u nex-pharma /opt/nex-pharma-insights/venv/bin/python -c "from config import settings; print(settings.ENVIRONMENT)"
```

#### IAM Permission Issues
```bash
# Test AWS access
aws sts get-caller-identity

# Test DynamoDB access
aws dynamodb list-tables --region us-east-1

# Test S3 access
aws s3 ls

# Run IAM compatibility test
python deployment/test_iam_compatibility.py
```

#### Database Connection Issues
```bash
# Check DynamoDB tables
python scripts/migrate.py status

# Create missing tables
python scripts/migrate.py create-all

# Test database connection
python -c "
from app.database.dynamodb_client import DynamoDBClient
client = DynamoDBClient()
print('DynamoDB client created successfully')
"
```

### Common Development Issues

#### Import Errors
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

#### Configuration Issues
```bash
# Check .env file exists
ls -la .env

# Test configuration loading
python -c "from config import settings; print(f'Environment: {settings.ENVIRONMENT}')"

# Validate settings
python deployment/test_local_setup.py
```

#### Port Already in Use
```bash
# Find process using port 8005
sudo lsof -i :8005

# Kill process
sudo kill -9 <PID>

# Use different port
python -m uvicorn app.main:app --port 8006
```

---

## 🔄 Maintenance

### Production Maintenance

#### Log Management
```bash
# View recent logs
sudo journalctl -u nex-pharma-insights --since "1 hour ago"

# Log rotation (automatic with systemd)
sudo journalctl --vacuum-time=7d  # Keep 7 days of logs

# Export logs
sudo journalctl -u nex-pharma-insights --since "2024-01-01" > service.log
```

#### Updates and Deployment
```bash
# Stop service
sudo systemctl stop nex-pharma-insights

# Backup current deployment
sudo cp -r /opt/nex-pharma-insights /opt/nex-pharma-insights.backup

# Update code
cd /opt/nex-pharma-insights/app
sudo git pull origin main

# Update dependencies
sudo -u nex-pharma /opt/nex-pharma-insights/venv/bin/pip install -r requirements.txt

# Restart service
sudo systemctl start nex-pharma-insights
```

#### Monitoring
```bash
# Service status
sudo systemctl is-active nex-pharma-insights

# Resource usage
htop
df -h
free -h

# Application metrics
curl http://localhost:8005/metrics
```

### Development Maintenance

#### Dependency Updates
```bash
# Update requirements
pip list --outdated
pip install --upgrade package-name
pip freeze > requirements.txt
```

#### Code Quality
```bash
# Format code
black app/ tests/

# Sort imports  
isort app/ tests/

# Type checking (if mypy installed)
mypy app/
```

#### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest --cov=app tests/

# Performance testing
python -m pytest tests/ --benchmark-only
```

---

## 📞 Support

### Getting Help

1. **Check Logs**: Always start with service logs
2. **Run Tests**: Use provided test scripts to diagnose issues
3. **Review Configuration**: Verify environment variables and settings
4. **Check Dependencies**: Ensure all required services are running

### Useful Commands Reference

```bash
# Production Service Management
sudo systemctl {start|stop|restart|status} nex-pharma-insights
sudo journalctl -u nex-pharma-insights -f

# Development Server
source .venv/bin/activate
python -m uvicorn app.main:app --reload

# Testing
python deployment/test_local_setup.py
python deployment/test_iam_compatibility.py

# Configuration
python -c "from config import settings; print(settings.ENVIRONMENT)"

# Health Checks
curl http://localhost:8005/health
curl http://localhost:8005/metrics
```

---

**🎉 Your NEX Pharma Insights Agent Service is now ready for both production and development use!** 