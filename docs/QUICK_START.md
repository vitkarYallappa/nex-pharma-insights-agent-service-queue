# Quick Start Guide

## 🚀 Production Setup (AWS EC2)

### Prerequisites
- EC2 instance with IAM role attached
- IAM role has DynamoDB, S3, and Bedrock permissions

### Deploy in 5 Steps

```bash
# 1. Clone repository
git clone <your-repo-url>
cd nex-pharma-insights-agent-service-queue

# 2. Run deployment script
sudo ./deployment/deploy.sh

# 3. Configure API keys
sudo nano /opt/nex-pharma-insights/.env
# Update: PERPLEXITY_API_KEY, SERP_API_KEY, ANTHROPIC_API_KEY, SECRET_KEY

# 4. Create database tables
cd /opt/nex-pharma-insights/app
sudo -u nex-pharma /opt/nex-pharma-insights/venv/bin/python scripts/migrate.py create-all

# 5. Start service
sudo systemctl start nex-pharma-insights
```

### Verify Production Deployment
```bash
# Check service status
sudo systemctl status nex-pharma-insights

# Test health endpoint
curl http://localhost:8005/health

# View logs
sudo journalctl -u nex-pharma-insights -f
```

---

## 💻 Development Setup (Local)

### Quick Local Setup

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd nex-pharma-insights-agent-service-queue
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env  # Or create .env file
nano .env  # Add your API keys and configuration

# 3. Run development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
```

### Verify Development Setup
```bash
# Test local setup
python deployment/test_local_setup.py

# Access API docs
open http://localhost:8005/docs
```

---

## 🧪 Essential Commands

### Production Management
```bash
# Service control
sudo systemctl {start|stop|restart|status} nex-pharma-insights

# View logs
sudo journalctl -u nex-pharma-insights -f

# Edit configuration
sudo nano /opt/nex-pharma-insights/.env
sudo systemctl restart nex-pharma-insights
```

### Development Commands
```bash
# Activate environment
source .venv/bin/activate

# Run server
python -m uvicorn app.main:app --reload

# Run tests
python deployment/test_local_setup.py
```

### Health Checks
```bash
# Basic health
curl http://localhost:8005/health

# Service metrics
curl http://localhost:8005/metrics

# API documentation
curl http://localhost:8005/docs
```

---

## 🔧 Troubleshooting

### Production Issues
```bash
# Check service logs
sudo journalctl -u nex-pharma-insights --no-pager

# Test IAM permissions
python deployment/test_iam_compatibility.py

# Restart service
sudo systemctl restart nex-pharma-insights
```

### Development Issues
```bash
# Check configuration
python -c "from config import settings; print(settings.ENVIRONMENT)"

# Test local setup
python deployment/test_local_setup.py

# Check port usage
sudo lsof -i :8005
```

---

## 📋 Configuration Templates

### Production `.env` (EC2)
```env
ENVIRONMENT=production
DEBUG=false
AWS_REGION=us-east-1
# Leave AWS credentials empty for IAM role
DATABASE_TYPE=dynamodb
STORAGE_TYPE=s3
S3_BUCKET_NAME=your-production-bucket
PERPLEXITY_API_KEY=your-key
SERP_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
SECRET_KEY=your-production-secret
```

### Development `.env` (Local)
```env
ENVIRONMENT=local
DEBUG=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-dev-key
AWS_SECRET_ACCESS_KEY=your-dev-secret
DATABASE_TYPE=dynamodb
DYNAMODB_ENDPOINT=http://localhost:8000
STORAGE_TYPE=minio
PERPLEXITY_API_KEY=your-key
SERP_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

---

**For detailed instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** 