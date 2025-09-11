from .base_migration import BaseMigration

class RequestAcceptanceMigration(BaseMigration):
    def get_table_name(self) -> str:
        return "request_queue_acceptance_queue"

    def get_table_schema(self) -> dict:
        return {
            'TableName': self.get_table_name(),
            'KeySchema': [
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'  # Sort key
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
            'BillingMode': 'PAY_PER_REQUEST',  # On-demand billing
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
                    'Value': 'request-acceptance'
                }
            ]
        }