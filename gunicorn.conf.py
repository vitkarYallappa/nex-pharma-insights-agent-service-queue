"""
Gunicorn configuration for NEX Pharma Insights Agent Service
"""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8005"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "nex-pharma-insights-agent"

# Daemon mode (set to True for production)
daemon = False

# PID file
pidfile = "/tmp/gunicorn.pid"

# User/group to run as (uncomment and set for production)
# user = "nex-pharma"
# group = "nex-pharma"

# Preload application for better performance
preload_app = True

# Enable auto-reload in development (disable in production)
reload = False 