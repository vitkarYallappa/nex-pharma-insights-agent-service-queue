# ================================
# scripts/setup_infrastructure.py
# ================================
# !/usr/bin/env python3
"""
Complete infrastructure setup script

This script sets up all required AWS resources:
- DynamoDB tables for queues
- S3 bucket for content storage
- IAM roles and policies (if needed)
"""

import sys
import boto3
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from migrations.migration_manager import MigrationManager
from config import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InfrastructureSetup:
    def __init__(self):
        self.migration_manager = MigrationManager()
        self.s3_client = boto3.client(
            's3',
            region_name=Config.AWS_REGION,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
        )

    def setup_all(self):
        """Set up complete infrastructure"""
        print("Setting up Market Intelligence Service Infrastructure...")

        # 1. Create DynamoDB tables
        print("\n1. Creating DynamoDB tables...")
        table_results = self.migration_manager.create_all_tables()
        self._print_table_results(table_results)

        # 2. Create S3 bucket
        print("\n2. Creating S3 bucket...")
        bucket_result = self._create_s3_bucket()
        print(f"S3 bucket: {'SUCCESS' if bucket_result else 'FAILED'}")

        # 3. Summary
        successful_tables = sum(table_results.values())
        total_tables = len(table_results)

        print(f"\n=== Infrastructure Setup Summary ===")
        print(f"DynamoDB tables: {successful_tables}/{total_tables} created")
        print(f"S3 bucket: {'Created' if bucket_result else 'Failed'}")

        if successful_tables == total_tables and bucket_result:
            print("✅ Infrastructure setup completed successfully!")
            return True
        else:
            print("❌ Infrastructure setup completed with errors")
            return False

    def _create_s3_bucket(self) -> bool:
        """Create S3 bucket for content storage"""
        try:
            bucket_name = Config.S3_BUCKET

            # Check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                print(f"S3 bucket {bucket_name} already exists")
                return True
            except Exception:
                pass

            # Create bucket
            if Config.AWS_REGION == 'us-east-1':
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': Config.AWS_REGION}
                )

            # Set bucket versioning
            self.s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )

            # Set bucket encryption
            self.s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            )

            print(f"S3 bucket {bucket_name} created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create S3 bucket: {str(e)}")
            return False

    def _print_table_results(self, results: dict):
        """Print table creation results"""
        for table_name, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"  {table_name}: {status}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--tables-only':
        # Only create tables
        migration_manager = MigrationManager()
        results = migration_manager.create_all_tables()

        success_count = sum(results.values())
        total_count = len(results)
        print(f"\nTables created: {success_count}/{total_count}")
    else:
        # Full infrastructure setup
        setup = InfrastructureSetup()
        success = setup.setup_all()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()