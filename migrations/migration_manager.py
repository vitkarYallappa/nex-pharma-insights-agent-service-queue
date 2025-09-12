from typing import List, Dict, Any
from .request_acceptance_migration import RequestAcceptanceMigration
from .serp_migration import SerpMigration
from .perplexity_migration import PerplexityMigration
from .insight_migration import InsightMigration
from .implication_migration import ImplicationMigration
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MigrationManager:
    def __init__(self):
        self.migrations = {
            'request_acceptance': RequestAcceptanceMigration(),
            'serp': SerpMigration(),
            'perplexity': PerplexityMigration(),
            'insight': InsightMigration(),
            'implication': ImplicationMigration()
        }

    def create_all_tables(self) -> Dict[str, bool]:
        """Create all queue tables"""
        results = {}

        logger.info("Starting migration: Creating all tables")

        for name, migration in self.migrations.items():
            logger.info(f"Creating table for {name}")
            results[name] = migration.create_table()

        success_count = sum(results.values())
        total_count = len(results)

        logger.info(f"Migration completed: {success_count}/{total_count} tables created successfully")

        return results

    def create_table(self, table_name: str) -> bool:
        """Create specific table"""
        if table_name not in self.migrations:
            logger.error(f"Unknown table: {table_name}")
            return False

        logger.info(f"Creating table: {table_name}")
        return self.migrations[table_name].create_table()

    def delete_all_tables(self) -> Dict[str, bool]:
        """Delete all queue tables"""
        results = {}

        logger.info("Starting migration: Deleting all tables")

        # Delete in reverse order to handle dependencies
        for name in reversed(list(self.migrations.keys())):
            migration = self.migrations[name]
            logger.info(f"Deleting table for {name}")
            results[name] = migration.delete_table()

        success_count = sum(results.values())
        total_count = len(results)

        logger.info(f"Migration completed: {success_count}/{total_count} tables deleted successfully")

        return results

    def delete_table(self, table_name: str) -> bool:
        """Delete specific table"""
        if table_name not in self.migrations:
            logger.error(f"Unknown table: {table_name}")
            return False

        logger.info(f"Deleting table: {table_name}")
        return self.migrations[table_name].delete_table()

    def get_table_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tables"""
        status = {}

        for name, migration in self.migrations.items():
            table_name = migration.get_table_name()
            exists = migration.table_exists()

            status[name] = {
                'table_name': table_name,
                'exists': exists,
                'status': 'active' if exists else 'not_created'
            }

        return status