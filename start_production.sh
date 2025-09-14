#!/bin/bash

# NEX Pharma Insights Agent Service - Production Startup Script

set -e

echo "🚀 Starting NEX Pharma Insights Agent Service in Production Mode..."

# Load production environment file
if [ -f "deployment/production.env" ]; then
    echo "📄 Loading production environment from deployment/production.env..."
    export $(grep -v '^#' deployment/production.env | xargs)
elif [ -f ".env.production" ]; then
    echo "📄 Loading production environment from .env.production..."
    export $(grep -v '^#' .env.production | xargs)
elif [ -f ".env" ]; then
    echo "📄 Loading environment from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  No environment file found, using defaults..."
    export ENVIRONMENT=production
    export DEBUG=false
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Install/update dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations if needed
echo "🗄️  Checking database tables..."
python -m scripts.migrate create-all

# Start the application with Gunicorn
echo "🌐 Starting application with Gunicorn..."
exec gunicorn app.main:app \
    --config gunicorn.conf.py \
    --log-level info \
    --access-logfile - \
    --error-logfile - 