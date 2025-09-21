import boto3
from botocore.exceptions import ClientError
import time
import os

# --- Configuration ---
# Use environment variables for table names in a production environment

REGION = os.environ.get('NAVINM_AWS_REGION', 'us-east-1')
CURR_ENV = os.environ.get('NAVINM_ENV', 'prod')  # 'local' for local testing
SUBSCRIPTIONS_TABLE_NAME = ''
CUSTOMERS_TABLE_NAME = ''


dynamodb_resource = None
customers_table = None  
subscriptions_table = None
# --- Initialization ---

def get_dynamodb_resource(env=''):
    if env == 'local':
        dynamodnb_local_endpoint = os.environ.get('NAVINM_DYNAMODB_LOCAL_ENDPOINT', 'http://localhost:8000')
        return boto3.resource('dynamodb', region_name=REGION,
                                endpoint_url=dynamodnb_local_endpoint, 
                                aws_access_key_id='anything',
                                aws_secret_access_key='anything')
    return boto3.resource('dynamodb', region_name=REGION)

def init():
    global dynamodb_resource, customers_table, subscriptions_table, CUSTOMERS_TABLE_NAME, SUBSCRIPTIONS_TABLE_NAME
    # Initialize the DynamoDB client
    dynamodb_resource = get_dynamodb_resource(CURR_ENV)

    CUSTOMERS_TABLE_NAME = os.environ.get('NAVINM_CUSTOMERS_TABLE_NAME', 'Customers')
    SUBSCRIPTIONS_TABLE_NAME = os.environ.get('NAVINM_SUBSCRIPTIONS_TABLE_NAME', 'Subscriptions')

    customers_table = dynamodb_resource.Table(CUSTOMERS_TABLE_NAME)
    subscriptions_table = dynamodb_resource.Table(SUBSCRIPTIONS_TABLE_NAME)
    print(f"Initialized DynamoDB resource in region {REGION} with tables: {CUSTOMERS_TABLE_NAME}, {SUBSCRIPTIONS_TABLE_NAME}")

# --- Shared Utilities (Transport Layer) ---

def create_customers_table(dynamodb_client):
    """
    Creates the Customers DynamoDB table.

    The primary key is 'customer_id', which will be a unique UUID
    for each customer.
    """
    try:
        table = dynamodb_client.create_table(
            TableName=CUSTOMERS_TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'customer_id',
                    'KeyType': 'HASH'  # Partition Key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'customer_id',
                    'AttributeType': 'S' # String
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"Creating table {CUSTOMERS_TABLE_NAME}...")
        table.wait_until_exists()
        print(f"Table {CUSTOMERS_TABLE_NAME} created successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"Table {CUSTOMERS_TABLE_NAME} already exists. Skipping creation.")
        else:
            print(f"Error creating table {CUSTOMERS_TABLE_NAME}: {e}")

def create_subscriptions_table(dynamodb_client):
    """
    Creates the Subscriptions DynamoDB table.

    The table uses a composite primary key:
    - 'customer_id' as the Partition Key (HASH) to group subscriptions by customer.
    - 'subscription_id' as the Sort Key (RANGE) to uniquely identify each subscription.

    It also creates a Global Secondary Index (GSI) on 'renewal_date' to allow
    efficient queries for subscriptions renewing on a specific date.
    """
    try:
        table = dynamodb_client.create_table(
            TableName=SUBSCRIPTIONS_TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'customer_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'subscription_id',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'customer_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'subscription_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'renewal_date',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'RenewalDateIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'renewal_date',
                            'KeyType': 'HASH'
                        },
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ]
        )
        print(f"Creating table {SUBSCRIPTIONS_TABLE_NAME}...")
        table.wait_until_exists()
        print(f"Table {SUBSCRIPTIONS_TABLE_NAME} created successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"Table {SUBSCRIPTIONS_TABLE_NAME} already exists. Skipping creation.")
        else:
            print(f"Error creating table {SUBSCRIPTIONS_TABLE_NAME}: {e}")

def lambda_handler(event, context):
    """
    Main Lambda handler function to create DynamoDB tables.
    """
    init()

    create_customers_table(dynamodb_resource)
    create_subscriptions_table(dynamodb_resource)

    return {
        'statusCode': 200,
        'body': 'DynamoDB tables creation process complete.'
    }

if __name__ == '__main__':
    # This block is for local testing. It won't run in the Lambda environment.
    # os.environ['AWS_REGION'] = 'us-east-1'
    # os.environ['CUSTOMERS_TABLE_NAME'] = 'CustomersTest'
    # os.environ['SUBSCRIPTIONS_TABLE_NAME'] = 'SubscriptionsTest'
    lambda_handler({}, {})
