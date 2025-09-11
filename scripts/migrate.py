# ================================
# scripts/migrate.py
# ================================
# !/usr/bin/env python3
"""
DynamoDB Migration Script for Market Intelligence Service

Usage:
    python scripts/migrate.py create-all
    python scripts/migrate.py delete-all
    python scripts/migrate.py create <table_name>
    python scripts/migrate.py delete <table_name>
    python scripts/migrate.py status
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from migrations.migration_manager import MigrationManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description='DynamoDB Migration Tool')
    parser.add_argument('command', choices=['create-all', 'delete-all', 'create', 'delete', 'status'])
    parser.add_argument('table_name', nargs='?', help='Table name for create/delete operations')

    args = parser.parse_args()

    migration_manager = MigrationManager()

    try:
        if args.command == 'create-all':
            print("Creating all tables...")
            results = migration_manager.create_all_tables()
            print_results(results, "Created")

        elif args.command == 'delete-all':
            print("Deleting all tables...")
            results = migration_manager.delete_all_tables()
            print_results(results, "Deleted")

        elif args.command == 'create':
            if not args.table_name:
                print("Error: table_name required for create command")
                sys.exit(1)
            print(f"Creating table: {args.table_name}")
            result = migration_manager.create_table(args.table_name)
            print(f"Table {args.table_name}: {'SUCCESS' if result else 'FAILED'}")

        elif args.command == 'delete':
            if not args.table_name:
                print("Error: table_name required for delete command")
                sys.exit(1)
            print(f"Deleting table: {args.table_name}")
            result = migration_manager.delete_table(args.table_name)
            print(f"Table {args.table_name}: {'SUCCESS' if result else 'FAILED'}")

        elif args.command == 'status':
            print("Checking table status...")
            status = migration_manager.get_table_status()
            print_status(status)

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)


def print_results(results: dict, action: str):
    """Print migration results"""
    print(f"\n{action} Results:")
    print("-" * 50)

    for table_name, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{table_name:20} : {status}")

    success_count = sum(results.values())
    total_count = len(results)
    print(f"\nSummary: {success_count}/{total_count} tables {action.lower()} successfully")


def print_status(status: dict):
    """Print table status"""
    print("\nTable Status:")
    print("-" * 60)
    print(f"{'Queue Name':<20} {'Table Name':<30} {'Status':<10}")
    print("-" * 60)

    for queue_name, info in status.items():
        table_name = info['table_name']
        exists = "EXISTS" if info['exists'] else "NOT FOUND"
        print(f"{queue_name:<20} {table_name:<30} {exists:<10}")

    existing_count = sum(1 for s in status.values() if s['exists'])
    total_count = len(status)
    print(f"\nSummary: {existing_count}/{total_count} tables exist")


if __name__ == "__main__":
    main()