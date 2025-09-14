#!/bin/bash

# NEX Pharma Insights Agent Service - Stop Script

echo "🛑 Stopping NEX Pharma Insights Service..."

# Check if service is running
RUNNING_PROCESSES=$(pgrep -f "gunicorn app.main:app" | wc -l)
if [ $RUNNING_PROCESSES -eq 0 ]; then
    echo "ℹ️  Service is not running"
    exit 0
fi

# Display current processes
echo "📋 Current processes to stop:"
ps aux | grep -E "gunicorn.*app.main:app" | grep -v grep

# Graceful shutdown first
echo "🔄 Attempting graceful shutdown..."
pkill -TERM -f "gunicorn app.main:app"

# Wait for graceful shutdown
echo "⏳ Waiting for processes to stop gracefully..."
for i in {1..10}; do
    REMAINING=$(pgrep -f "gunicorn app.main:app" | wc -l)
    if [ $REMAINING -eq 0 ]; then
        echo "✅ All processes stopped gracefully"
        exit 0
    fi
    echo "   Waiting... ($i/10)"
    sleep 1
done

# If still running after 10 seconds, force kill
REMAINING=$(pgrep -f "gunicorn app.main:app" | wc -l)
if [ $REMAINING -gt 0 ]; then
    echo "⚠️  Processes still running. Force stopping..."
    pkill -KILL -f "gunicorn app.main:app"
    sleep 2
    
    # Final check
    FINAL_CHECK=$(pgrep -f "gunicorn app.main:app" | wc -l)
    if [ $FINAL_CHECK -eq 0 ]; then
        echo "✅ All processes force stopped"
    else
        echo "❌ Failed to stop some processes. Manual intervention required:"
        ps aux | grep -E "gunicorn.*app.main:app" | grep -v grep
        exit 1
    fi
fi

echo "🏁 Service stopped successfully. Safe to update files or perform maintenance." 