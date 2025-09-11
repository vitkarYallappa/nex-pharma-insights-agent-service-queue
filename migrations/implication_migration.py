# ================================
# migrations/implication_migration.py
# ================================
from .base_migration import BaseMigration


class ImplicationMigration(BaseMigration):
    def get_table_name(self) -> str:
        return "implication_queue"

    def get_table_schema(self) -> dict:
        return {
            'TableName': self.get_table_name(),
            'KeySchema': [
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'SK',
                    'AttributeType': 'S'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'Tags': [
                {
                    'Key': 'Environment',
                    'Value': 'production'
                },
                {
                    'Key': 'Service',
                    'Value': 'market-intelligence'
                },
                {
                    'Key': 'QueueType',
                    'Value': 'implication'
                }
            ]
        }