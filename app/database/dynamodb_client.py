import boto3
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
from datetime import datetime
import json
from decimal import Decimal

from config import settings, QUEUE_TABLES
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class DynamoDBClient:
    """DynamoDB client for queue operations"""
    
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        
        # Create DynamoDB resource and client
        self.dynamodb = self.session.resource(
            'dynamodb',
            endpoint_url=settings.dynamodb_endpoint_url
        )
        self.client = self.session.client(
            'dynamodb',
            endpoint_url=settings.dynamodb_endpoint_url
        )
        
        # Cache table objects
        self._tables = {}
    
    def get_table(self, table_name: str):
        """Get DynamoDB table object with caching"""
        if table_name not in self._tables:
            self._tables[table_name] = self.dynamodb.Table(table_name)
        return self._tables[table_name]
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        try:
            table = self.get_table(table_name)
            table.load()
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise
    
    def create_table(self, table_name: str) -> bool:
        """Create a DynamoDB table for queue operations"""
        try:
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'PK',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'SK',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'PK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'SK',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            logger.info(f"Successfully created table: {table_name}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Table {table_name} already exists")
                return True
            else:
                logger.error(f"Failed to create table {table_name}: {str(e)}")
                return False
    
    def delete_table(self, table_name: str) -> bool:
        """Delete a DynamoDB table"""
        try:
            table = self.get_table(table_name)
            table.delete()
            table.wait_until_not_exists()
            
            # Remove from cache
            if table_name in self._tables:
                del self._tables[table_name]
            
            logger.info(f"Successfully deleted table: {table_name}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Table {table_name} does not exist")
                return True
            else:
                logger.error(f"Failed to delete table {table_name}: {str(e)}")
                return False
    
    def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Put an item into a DynamoDB table"""
        try:
            table = self.get_table(table_name)
            
            # Convert datetime objects to ISO strings
            processed_item = self._process_item_for_dynamodb(item)
            
            table.put_item(Item=processed_item)
            logger.debug(f"Successfully put item in {table_name}: {item.get('PK', 'unknown')}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to put item in {table_name}: {str(e)}")
            return False
    
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get an item from a DynamoDB table"""
        try:
            table = self.get_table(table_name)
            response = table.get_item(Key=key)
            
            if 'Item' in response:
                return self._process_item_from_dynamodb(response['Item'])
            return None
            
        except ClientError as e:
            logger.error(f"Failed to get item from {table_name}: {str(e)}")
            return None
    
    def query_items(self, table_name: str, key_condition: str, 
                   expression_attribute_values: Dict[str, Any],
                   filter_expression: Optional[str] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query items from a DynamoDB table"""
        try:
            table = self.get_table(table_name)
            
            query_params = {
                'KeyConditionExpression': key_condition,
                'ExpressionAttributeValues': expression_attribute_values
            }
            
            if filter_expression:
                query_params['FilterExpression'] = filter_expression
            
            if limit:
                query_params['Limit'] = limit
            
            response = table.query(**query_params)
            
            items = []
            for item in response.get('Items', []):
                items.append(self._process_item_from_dynamodb(item))
            
            return items
            
        except ClientError as e:
            logger.error(f"Failed to query items from {table_name}: {str(e)}")
            return []
    
    def scan_items(self, table_name: str, 
                  filter_expression: Optional[str] = None,
                  expression_attribute_values: Optional[Dict[str, Any]] = None,
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scan items from a DynamoDB table"""
        try:
            table = self.get_table(table_name)
            
            scan_params = {}
            
            if filter_expression:
                scan_params['FilterExpression'] = filter_expression
            
            if expression_attribute_values:
                scan_params['ExpressionAttributeValues'] = expression_attribute_values
            
            if limit:
                scan_params['Limit'] = limit
            
            response = table.scan(**scan_params)
            
            items = []
            for item in response.get('Items', []):
                items.append(self._process_item_from_dynamodb(item))
            
            return items
            
        except ClientError as e:
            logger.error(f"Failed to scan items from {table_name}: {str(e)}")
            return []
    
    def update_item(self, table_name: str, key: Dict[str, Any], 
                   update_expression: str, 
                   expression_attribute_values: Dict[str, Any]) -> bool:
        """Update an item in a DynamoDB table"""
        try:
            table = self.get_table(table_name)
            
            table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            logger.debug(f"Successfully updated item in {table_name}: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update item in {table_name}: {str(e)}")
            return False
    
    def delete_item(self, table_name: str, key: Dict[str, Any]) -> bool:
        """Delete an item from a DynamoDB table"""
        try:
            table = self.get_table(table_name)
            table.delete_item(Key=key)
            
            logger.debug(f"Successfully deleted item from {table_name}: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete item from {table_name}: {str(e)}")
            return False
    
    def _process_item_for_dynamodb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process item for DynamoDB storage (convert datetime, etc.)"""
        processed = {}
        
        for key, value in item.items():
            if isinstance(value, datetime):
                processed[key] = value.isoformat()
            elif isinstance(value, dict):
                processed[key] = self._process_item_for_dynamodb(value)
            elif isinstance(value, list):
                processed[key] = [
                    self._process_item_for_dynamodb(v) if isinstance(v, dict) 
                    else v.isoformat() if isinstance(v, datetime) 
                    else v 
                    for v in value
                ]
            else:
                processed[key] = value
        
        return processed
    
    def _process_item_from_dynamodb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process item from DynamoDB (convert strings back to datetime, etc.)"""
        processed = {}
        
        for key, value in item.items():
            if isinstance(value, str) and key.endswith('_at'):
                try:
                    processed[key] = datetime.fromisoformat(value)
                except ValueError:
                    processed[key] = value
            elif isinstance(value, dict):
                processed[key] = self._process_item_from_dynamodb(value)
            elif isinstance(value, list):
                processed[key] = [
                    self._process_item_from_dynamodb(v) if isinstance(v, dict)
                    else v
                    for v in value
                ]
            else:
                processed[key] = value
        
        return processed
    
    def get_queue_items_by_status(self, table_name: str, status: str, 
                                 limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get queue items by status"""
        return self.scan_items(
            table_name=table_name,
            filter_expression='#status = :status',
            expression_attribute_values={':status': status},
            limit=limit
        )
    
    def update_item_status(self, table_name: str, pk: str, sk: str, 
                          new_status: str, error_message: Optional[str] = None) -> bool:
        """Update the status of a queue item"""
        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_values = {
            ':status': new_status,
            ':updated_at': datetime.utcnow().isoformat()
        }
        
        if error_message:
            update_expression += ", error_message = :error_message"
            expression_values[':error_message'] = error_message
        
        return self.update_item(
            table_name=table_name,
            key={'PK': pk, 'SK': sk},
            update_expression=update_expression,
            expression_attribute_values=expression_values
        )


# Global DynamoDB client instance
dynamodb_client = DynamoDBClient()
