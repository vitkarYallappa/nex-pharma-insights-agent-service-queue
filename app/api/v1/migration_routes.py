from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from migrations.migration_manager import MigrationManager
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/migrations", tags=["migrations"])


# Request/Response Models
class MigrationResponse(BaseModel):
    success: bool
    message: str
    results: Dict[str, Any]


class TableMigrationRequest(BaseModel):
    table_name: str
    action: str  # create, delete, status


# Initialize migration manager
migration_manager = MigrationManager()


@router.post("/create-all", response_model=MigrationResponse)
async def create_all_tables():
    """Create all DynamoDB queue tables"""
    try:
        logger.info("API request: Create all tables")
        results = migration_manager.create_all_tables()

        success_count = sum(results.values())
        total_count = len(results)

        return MigrationResponse(
            success=success_count == total_count,
            message=f"Created {success_count}/{total_count} tables successfully",
            results=results
        )
    except Exception as e:
        logger.error(f"Failed to create tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@router.post("/delete-all", response_model=MigrationResponse)
async def delete_all_tables():
    """Delete all DynamoDB queue tables"""
    try:
        logger.info("API request: Delete all tables")
        results = migration_manager.delete_all_tables()

        success_count = sum(results.values())
        total_count = len(results)

        return MigrationResponse(
            success=success_count == total_count,
            message=f"Deleted {success_count}/{total_count} tables successfully",
            results=results
        )
    except Exception as e:
        logger.error(f"Failed to delete tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@router.post("/table", response_model=MigrationResponse)
async def manage_table(request: TableMigrationRequest):
    """Create, delete, or check status of specific table"""
    try:
        table_name = request.table_name
        action = request.action.lower()

        logger.info(f"API request: {action} table {table_name}")

        if action == "create":
            result = migration_manager.create_table(table_name)
            message = f"Table {table_name} {'created' if result else 'failed to create'}"

        elif action == "delete":
            result = migration_manager.delete_table(table_name)
            message = f"Table {table_name} {'deleted' if result else 'failed to delete'}"

        elif action == "status":
            status = migration_manager.get_table_status()
            if table_name in status:
                result = True
                message = f"Table {table_name} status retrieved"
                return MigrationResponse(
                    success=True,
                    message=message,
                    results={table_name: status[table_name]}
                )
            else:
                result = False
                message = f"Unknown table: {table_name}"
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

        return MigrationResponse(
            success=result,
            message=message,
            results={table_name: result}
        )

    except Exception as e:
        logger.error(f"Failed to {action} table {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@router.get("/status", response_model=MigrationResponse)
async def get_migration_status():
    """Get status of all queue tables"""
    try:
        logger.info("API request: Get migration status")
        status = migration_manager.get_table_status()

        existing_count = sum(1 for s in status.values() if s['exists'])
        total_count = len(status)

        return MigrationResponse(
            success=True,
            message=f"Status retrieved: {existing_count}/{total_count} tables exist",
            results=status
        )
    except Exception as e:
        logger.error(f"Failed to get migration status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/tables")
async def list_available_tables():
    """List all available queue tables for migration"""
    tables = {
        "request_acceptance": "request_queue_acceptance_queue",
        "serp": "serp_queue",
        "perplexity": "perplexity_queue",
        "fetch_content": "fetch_content_queue",
        "relevance_check": "relevance_check_queue",
        "insight": "insight_queue",
        "implication": "implication_queue"
    }

    return {
        "available_tables": tables,
        "total_count": len(tables)
    }

