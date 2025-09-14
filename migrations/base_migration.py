import boto3
from abc import ABC, abstractmethod
from typing import Dict, Any
from botocore.exceptions import ClientError
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class BaseMigration(ABC):
    def __init__(self):
        # For local DynamoDB, use proper dummy credentials that boto3 accepts
        if settings.dynamodb_endpoint or settings.dynamodb_endpoint_url:
            # Local DynamoDB - use dummy credentials that boto3 accepts
            aws_access_key = settings.aws_access_key_id or "local"
            aws_secret_key = settings.aws_secret_access_key or "local"
            
            # Ensure credentials are valid format for boto3
            if aws_access_key in ["dummy", "test"]:
                aws_access_key = "local"
            if aws_secret_key in ["dummy", "test"]:
                aws_secret_key = "local"
                
            endpoint_url = settings.dynamodb_endpoint or settings.dynamodb_endpoint_url
            region = settings.dynamodb_region or settings.aws_region
                
            self.dynamodb = boto3.client(
                'dynamodb',
                endpoint_url=endpoint_url,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
        else:
            # AWS DynamoDB - use real credentials
            self.dynamodb = boto3.client(
                'dynamodb',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )

    @abstractmethod
    def get_table_name(self) -> str:
        """Return the table name"""
        pass

    @abstractmethod
    def get_table_schema(self) -> Dict[str, Any]:
        """Return the table schema definition"""
        pass

    def table_exists(self) -> bool:
        """Check if table already exists"""
        try:
            self.dynamodb.describe_table(TableName=self.get_table_name())
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise

    def create_table(self) -> bool:
        """Create the DynamoDB table"""
        try:
            table_name = self.get_table_name()

            if self.table_exists():
                logger.info(f"Table {table_name} already exists, skipping creation")
                return True

            logger.info(f"Creating table: {table_name}")

            schema = self.get_table_schema()

            response = self.dynamodb.create_table(**schema)

            # Wait for table to be created
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=table_name)

            logger.info(f"Table {table_name} created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {str(e)}")
            return False

    def delete_table(self) -> bool:
        """Delete the DynamoDB table"""
        try:
            table_name = self.get_table_name()

            if not self.table_exists():
                logger.info(f"Table {table_name} does not exist, skipping deletion")
                return True

            logger.info(f"Deleting table: {table_name}")

            self.dynamodb.delete_table(TableName=table_name)

            # Wait for table to be deleted
            waiter = self.dynamodb.get_waiter('table_not_exists')
            waiter.wait(TableName=table_name)

            logger.info(f"Table {table_name} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to delete table {table_name}: {str(e)}")
            return False