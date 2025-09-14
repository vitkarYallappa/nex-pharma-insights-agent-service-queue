#!/bin/bash

# NEX Pharma Insights Agent Service - Restart Script

echo "🔄 Restarting NEX Pharma Insights Service..."

# Find and display current processes
echo "📋 Current processes:"
ps aux | grep -E "gunicorn.*app.main:app" | grep -v grep

# Graceful shutdown first
echo "🛑 Attempting graceful shutdown..."
pkill -TERM -f "gunicorn app.main:app"

# Wait for graceful shutdown
echo "⏳ Waiting for processes to stop..."
sleep 5

# Check if any processes are still running
REMAINING=$(pgrep -f "gunicorn app.main:app" | wc -l)
if [ $REMAINING -gt 0 ]; then
    echo "⚠️  Force killing remaining processes..."
    pkill -KILL -f "gunicorn app.main:app"
    sleep 2
fi

# Verify all processes are stopped
FINAL_CHECK=$(pgrep -f "gunicorn app.main:app" | wc -l)
if [ $FINAL_CHECK -gt 0 ]; then
    echo "❌ Failed to stop all processes. Manual intervention required."
    exit 1
fi

echo "✅ All processes stopped successfully"

# Start the service again
echo "🚀 Starting service..."
./start_production.sh &

# Wait a moment and check if it started
sleep 3
NEW_PROCESSES=$(pgrep -f "gunicorn app.main:app" | wc -l)
if [ $NEW_PROCESSES -gt 0 ]; then
    echo "✅ Service restarted successfully!"
    echo "📋 New processes:"
    ps aux | grep -E "gunicorn.*app.main:app" | grep -v grep
    
    # Quick health check
    echo "🏥 Performing health check..."
    sleep 2
    if curl -f -s http://localhost:8005/health > /dev/null; then
        echo "✅ Health check passed - Service is running!"
    else
        echo "⚠️  Health check failed - Service may still be starting..."
    fi
else
    echo "❌ Failed to start service. Check logs for errors."
    exit 1
fi 