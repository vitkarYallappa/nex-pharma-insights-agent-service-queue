"""
Gunicorn Configuration for NEX Pharma Insights Agent Service
Production-ready configuration with optimized settings
"""

import multiprocessing
import os
from pathlib import Path

# ============================================================================
# SERVER SOCKET
# ============================================================================
bind = "0.0.0.0:8005"
backlog = 2048

# ============================================================================
# WORKER PROCESSES
# ============================================================================
# Number of worker processes
# Formula: (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Maximum number of simultaneous clients per worker
worker_connections = 1000

# Worker class - use uvicorn workers for async support
worker_class = "uvicorn.workers.UvicornWorker"

# Maximum requests a worker will process before restarting
# Helps prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Worker timeout in seconds
timeout = 120
keepalive = 5

# ============================================================================
# LOGGING
# ============================================================================
# Logging configuration
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = "/var/log/nex-pharma-insights/gunicorn-access.log"
errorlog = "/var/log/nex-pharma-insights/gunicorn-error.log"

# Access log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Capture stdout/stderr in log files
capture_output = True

# Enable access logging
accesslog = "-" if os.getenv("ENVIRONMENT") == "local" else accesslog
errorlog = "-" if os.getenv("ENVIRONMENT") == "local" else errorlog

# ============================================================================
# PROCESS NAMING
# ============================================================================
proc_name = "nex-pharma-insights-agent"

# ============================================================================
# SERVER MECHANICS
# ============================================================================
# Restart workers after this many seconds
max_worker_age = 3600  # 1 hour

# Preload application code before forking worker processes
preload_app = True

# Restart workers gracefully on code changes (development)
reload = os.getenv("ENVIRONMENT", "production") == "local"

# ============================================================================
# SECURITY
# ============================================================================
# Limit the allowed size of an HTTP request header field
limit_request_field_size = 8190

# Limit the number of header fields in a request
limit_request_fields = 100

# Limit the allowed size of the HTTP request line
limit_request_line = 8190

# ============================================================================
# SSL/TLS (if using HTTPS)
# ============================================================================
# Uncomment and configure if using SSL
# keyfile = "/path/to/ssl/private.key"
# certfile = "/path/to/ssl/certificate.crt"
# ssl_version = ssl.PROTOCOL_TLSv1_2
# ciphers = "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================
# Enable sendfile for static files (if serving static content)
sendfile = True

# Enable TCP_NODELAY
tcp_nodelay = True

# ============================================================================
# WORKER LIFECYCLE HOOKS
# ============================================================================

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting NEX Pharma Insights Agent Service")
    
    # Ensure log directories exist
    log_dir = Path("/var/log/nex-pharma-insights")
    log_dir.mkdir(parents=True, exist_ok=True)

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading NEX Pharma Insights Agent Service")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("NEX Pharma Insights Agent Service is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker aborted (pid: %s)", worker.pid)

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug("%s %s", req.method, req.path)

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    worker.log.debug("Request processed: %s %s - %s", req.method, req.path, resp.status_code)

def child_exit(server, worker):
    """Called just after a worker has been exited, in the master process."""
    server.log.info("Worker exited (pid: %s)", worker.pid)

def worker_exit(server, worker):
    """Called just after a worker has been exited, in the worker process."""
    server.log.info("Worker exiting (pid: %s)", worker.pid)

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    server.log.info("Number of workers changed from %s to %s", old_value, new_value)

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Shutting down NEX Pharma Insights Agent Service")

# ============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# ============================================================================

# Development environment overrides
if os.getenv("ENVIRONMENT") == "local":
    workers = 1
    reload = True
    loglevel = "debug"
    accesslog = "-"
    errorlog = "-"

# Staging environment overrides
elif os.getenv("ENVIRONMENT") == "staging":
    workers = max(2, multiprocessing.cpu_count())
    
# Production environment (default settings above are for production)
elif os.getenv("ENVIRONMENT") == "production":
    # Use default production settings
    pass 