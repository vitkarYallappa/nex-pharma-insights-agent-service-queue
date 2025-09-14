# Production Deployment Guide

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Choose one option:

**Option A: Use existing production config (Recommended)**
```bash
# Edit deployment/production.env with your API keys
nano deployment/production.env
```

**Option B: Create simple production config**
```bash
# Copy and customize
cp production.env.example .env.production
nano .env.production
```

### 3. Required API Keys
Update these in your environment file:
```bash
PERPLEXITY_API_KEY=your-actual-key
SERP_API_KEY=your-actual-key
ANTHROPIC_API_KEY=your-actual-key
SECRET_KEY=your-production-secret-key
```

## Start Application

### Simple Start
```bash
./start_production.sh
```

### Manual Start
```bash
gunicorn app.main:app --config gunicorn.conf.py
```

### Background Start
```bash
nohup ./start_production.sh > app.log 2>&1 &
```

## Restart Options

### 1. Graceful Restart (Recommended)
```bash
# Find process ID
ps aux | grep gunicorn

# Send HUP signal for graceful restart
kill -HUP <master_pid>
```

### 2. Quick Restart Script
Create `restart.sh`:
```bash
#!/bin/bash
echo "🔄 Restarting NEX Pharma Insights Service..."

# Kill existing processes
pkill -f "gunicorn app.main:app"

# Wait for processes to stop
sleep 3

# Start again
./start_production.sh
```

### 3. Systemd Service (Production Recommended)
Create `/etc/systemd/system/nex-pharma-insights.service`:
```ini
[Unit]
Description=NEX Pharma Insights Agent Service
After=network.target

[Service]
Type=exec
User=your-user
Group=your-group
WorkingDirectory=/path/to/nex-pharma-insights-agent-service-queue
ExecStart=/path/to/nex-pharma-insights-agent-service-queue/start_production.sh
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then use systemd commands:
```bash
# Enable and start
sudo systemctl enable nex-pharma-insights
sudo systemctl start nex-pharma-insights

# Restart
sudo systemctl restart nex-pharma-insights

# Check status
sudo systemctl status nex-pharma-insights

# View logs
sudo journalctl -u nex-pharma-insights -f
```

## Process Management

### Check Running Processes
```bash
# Check if running
ps aux | grep gunicorn

# Check port usage
netstat -tlnp | grep :8005
```

### Stop Application

**Simple Stop (Recommended)**
```bash
./stop.sh
```

**Manual Stop**
```bash
# Graceful stop
pkill -TERM -f "gunicorn app.main:app"

# Force stop if needed
pkill -KILL -f "gunicorn app.main:app"
```

### Monitor Application
```bash
# Check health endpoint
curl http://localhost:8005/health

# Check application status
curl http://localhost:8005/

# View logs (if using systemd)
sudo journalctl -u nex-pharma-insights -f
```

## Management Scripts

- `start_production.sh` - Start the service
- `stop.sh` - Stop the service (for maintenance/updates)
- `restart.sh` - Restart the service with health checks

## Configuration Files

- `gunicorn.conf.py` - Gunicorn settings
- `deployment/production.env` - Production environment variables
- `production.env.example` - Environment template

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Find and kill process using port 8005
sudo lsof -ti:8005 | xargs kill -9
```

**Permission denied:**
```bash
# Make scripts executable
chmod +x start_production.sh restart.sh
```

**Import errors:**
```bash
# Ensure you're in the correct directory
cd /path/to/nex-pharma-insights-agent-service-queue
```

### Health Check
```bash
# Quick health check
curl -f http://localhost:8005/health || echo "Service is down"
```

## Maintenance Workflow

### Update Files/Code
```bash
# 1. Stop service safely
./stop.sh

# 2. Update your files (git pull, edit configs, etc.)
git pull origin main
# or edit files...

# 3. Start service again
./start_production.sh
```

### Quick Update & Restart
```bash
# Update and restart in one go
git pull origin main && ./restart.sh
```

## Production Checklist

- [ ] API keys configured in environment file
- [ ] Database tables created (`python -m scripts.migrate create-all`)
- [ ] Firewall configured for port 8005
- [ ] SSL/TLS configured (if needed)
- [ ] Monitoring setup
- [ ] Log rotation configured
- [ ] Backup strategy in place 