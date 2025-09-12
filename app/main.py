import threading
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from app.utils.logger import get_logger, setup_logging
from app.api.v1.routes import router as api_router
from app.api.v1.migration_routes import router as migration_router
from app.api.v1.regenerate_routes import router as regenerate_router

# Import workers
from app.queues.request_acceptance.worker import RequestAcceptanceWorker
from app.queues.serp.worker import SerpWorker
from app.queues.perplexity.worker import PerplexityWorker
from app.queues.relevance_check.worker import RelevanceCheckWorker
from app.queues.insight.worker import InsightWorker
from app.queues.implication.worker import ImplicationWorker

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Global worker instances
workers = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Market Intelligence Service...")
    
    # Check database tables
    await check_database_tables()
    
    # Start queue workers
    await start_workers()
    
    logger.info("Market Intelligence Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Market Intelligence Service...")
    
    # Stop workers
    await stop_workers()
    
    logger.info("Market Intelligence Service stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A FastAPI-based microservice for processing market intelligence requests through a queue-driven architecture",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Setup CORS directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(migration_router, prefix=settings.api_prefix)
app.include_router(regenerate_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check worker status
        worker_status = {}
        for name, worker in workers.items():
            worker_status[name] = {
                "running": worker.is_running if worker else False,
                "thread_alive": worker.thread.is_alive() if worker and worker.thread else False
            }
        
        # Check database connectivity
        from app.database.dynamodb_client import dynamodb_client
        from migrations.migration_manager import MigrationManager
        
        migration_manager = MigrationManager()
        table_status = migration_manager.get_table_status()
        
        db_healthy = all(info['exists'] for info in table_status.values())
        
        health_status = {
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected" if db_healthy else "issues_detected",
                "tables": table_status
            },
            "workers": worker_status,
            "version": settings.app_version
        }
        
        status_code = 200 if db_healthy else 503
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )


@app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    try:
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "workers": {},
            "system": {
                "uptime_seconds": 0,  # Would track actual uptime
                "memory_usage": "N/A",  # Would use psutil in production
                "cpu_usage": "N/A"
            }
        }
        
        # Get worker metrics
        for name, worker in workers.items():
            if worker:
                try:
                    worker_metrics = worker.get_queue_metrics()
                    metrics["workers"][name] = worker_metrics
                except Exception as e:
                    metrics["workers"][name] = {"error": str(e)}
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


async def check_database_tables():
    """Check if all required database tables exist"""
    try:
        from migrations.migration_manager import MigrationManager
        
        migration_manager = MigrationManager()
        status = migration_manager.get_table_status()
        
        missing_tables = [name for name, info in status.items() if not info['exists']]
        
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            logger.info("Run 'python scripts/migrate.py create-all' to create missing tables")
        else:
            logger.info("All required tables exist")
            
    except Exception as e:
        logger.error(f"Failed to check database tables: {str(e)}")


async def start_workers():
    """Start all queue workers"""
    try:
        logger.info("Starting queue workers...")
        
        # Initialize workers
        worker_classes = [
            ("request_acceptance", RequestAcceptanceWorker),
            ("serp", SerpWorker),
            ("perplexity", PerplexityWorker),
            ("relevance_check", RelevanceCheckWorker),
            ("insight", InsightWorker),
            ("implication", ImplicationWorker),
        ]
        
        for name, worker_class in worker_classes:
            try:
                logger.info(f"🚀 INITIALIZING {name.upper()} QUEUE WORKER...")
                worker = worker_class()
                workers[name] = worker
                
                # Start worker thread
                worker.start_worker_thread()
                
                logger.info(f"✅ {name.upper()} QUEUE WORKER STARTED - Polling for tasks every {worker.poll_interval}s")
                
            except Exception as e:
                logger.error(f"❌ FAILED TO START {name.upper()} WORKER: {str(e)}")
                workers[name] = None
        
        active_workers = [w for w in workers.values() if w]
        logger.info(f"🎯 QUEUE SYSTEM READY - {len(active_workers)}/{len(worker_classes)} workers running successfully")
        
        # Log active queues
        if active_workers:
            active_queue_names = [name.upper() for name, worker in workers.items() if worker]
            logger.info(f"📋 ACTIVE QUEUES: {', '.join(active_queue_names)}")
        else:
            logger.warning("⚠️  NO QUEUE WORKERS ARE RUNNING!")
        
    except Exception as e:
        logger.error(f"Failed to start workers: {str(e)}")


async def stop_workers():
    """Stop all queue workers"""
    try:
        logger.info("Stopping queue workers...")
        
        for name, worker in workers.items():
            if worker:
                try:
                    worker.stop_polling()
                    logger.info(f"Stopped {name} worker")
                except Exception as e:
                    logger.error(f"Failed to stop {name} worker: {str(e)}")
        
        # Clear workers
        workers.clear()
        
        logger.info("All workers stopped")
        
    except Exception as e:
        logger.error(f"Failed to stop workers: {str(e)}")


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )