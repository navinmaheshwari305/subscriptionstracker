import json
import boto3
import os
import uuid
import datetime

# --- Configuration ---
CUSTOMERS_TABLE_NAME, SUBSCRIPTIONS_TABLE_NAME = '', ''
REGION = os.environ.get('NAVINM_AWS_REGION', 'us-east-1')
CURR_ENV = os.environ.get('NAVINM_ENV', 'prod')  # 'local' for local testing

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

# --- Shared Utilities (Transport Layer) ---
def respond(status_code, body):
    """
    Helper function to create a standardized API Gateway response.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'  # Adjust for production
        },
        'body': json.dumps(body, default=str)
    }

# --- Customer Data Layer (DL) ---
def dl_create_customer(item):
    """Inserts a new customer item into the DynamoDB table."""
    customers_table.put_item(Item=item)

def dl_get_customer(customer_id):
    """Retrieves a single customer by ID."""
    response = customers_table.get_item(Key={'customer_id': customer_id})
    return response.get('Item')

def dl_list_customers():
    """Lists all customers from the table (inefficient for large tables)."""
    response = customers_table.scan()
    return response.get('Items', [])

def dl_update_customer(key, update_expression, expression_attribute_values, expression_attribute_names):
    """Updates a customer item in the table."""
    customers_table.update_item(
        Key=key,
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ExpressionAttributeNames=expression_attribute_names
    )

def dl_delete_customer(customer_id):
    """Deletes a customer item from the table."""
    response = customers_table.delete_item(Key={'customer_id': customer_id}, ReturnValues='ALL_OLD')
    return response.get('Attributes')

# --- Subscription Data Layer (DL) ---
def dl_create_subscription(item):
    """Inserts a new subscription item into the DynamoDB table."""
    subscriptions_table.put_item(Item=item)

def dl_get_subscription(customer_id, subscription_id):
    """Retrieves a single subscription by customer and subscription ID."""
    response = subscriptions_table.get_item(Key={'customer_id': customer_id, 'subscription_id': subscription_id})
    return response.get('Item')

def dl_list_subscriptions(customer_id):
    """Lists all subscriptions for a given customer."""
    response = subscriptions_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('customer_id').eq(customer_id)
    )
    return response.get('Items', [])

def dl_update_subscription(key, update_expression, expression_attribute_values, expression_attribute_names):
    """Updates a subscription item in the table."""
    subscriptions_table.update_item(
        Key=key,
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ExpressionAttributeNames=expression_attribute_names
    )

def dl_delete_subscription(customer_id, subscription_id):
    """Deletes a subscription item from the table."""
    response = subscriptions_table.delete_item(Key={'customer_id': customer_id, 'subscription_id': subscription_id}, ReturnValues='ALL_OLD')
    return response.get('Attributes')

# --- Customer Business Logic (BL) ---
def bl_create_customer(data):
    """Business logic for creating a customer, including data validation."""
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return respond(400, {'message': 'Missing required fields: name, email, or password'})

    customer_id = str(uuid.uuid4())
    created_date = datetime.datetime.now().isoformat()
    item = {'customer_id': customer_id, 'name': name, 'email': email, 'password': password, 'created_date': created_date}
    
    dl_create_customer(item)
    return respond(201, {'message': 'Customer created successfully', 'customer_id': customer_id})

def bl_update_customer(customer_id, data):
    """Business logic for updating a customer."""
    update_expression_parts = []
    expression_attribute_values = {}
    expression_attribute_names = {}
    
    if 'name' in data:
        update_expression_parts.append('#n = :name')
        expression_attribute_values[':name'] = data['name']
        expression_attribute_names['#n'] = 'name'
    if 'email' in data:
        update_expression_parts.append('#e = :email')
        expression_attribute_values[':e'] = data['email']
        expression_attribute_names['#e'] = 'email'
    if 'password' in data:
        update_expression_parts.append('#p = :password')
        expression_attribute_values[':p'] = data['password']
        expression_attribute_names['#p'] = 'password'

    if not update_expression_parts:
        return respond(400, {'message': 'No fields provided for update'})
        
    update_expression = 'SET ' + ', '.join(update_expression_parts)
    dl_update_customer(
        key={'customer_id': customer_id},
        update_expression=update_expression,
        expression_attribute_values=expression_attribute_values,
        expression_attribute_names=expression_attribute_names
    )
    return respond(200, {'message': 'Customer updated successfully'})

# --- Subscription Business Logic (BL) ---
def bl_create_subscription(customer_id, data):
    """Business logic for creating a subscription."""
    name = data.get('name')
    category = data.get('category')
    renewal_frequency = data.get('renewal_frequency')
    renewal_date = data.get('renewal_date')
    cost = data.get('cost')
    start_date = data.get('start_date')

    if not all([name, category, renewal_frequency, renewal_date, cost, start_date]):
        return respond(400, {'message': 'Missing required fields for subscription'})
    
    subscription_id = str(uuid.uuid4())
    item = {
        'customer_id': customer_id,
        'subscription_id': subscription_id,
        'name': name,
        'category': category,
        'renewal_frequency': renewal_frequency,
        'renewal_date': renewal_date,
        'cost': cost,
        'start_date': start_date
    }
    
    dl_create_subscription(item)
    return respond(201, {'message': 'Subscription created successfully', 'subscription_id': subscription_id})

def bl_update_subscription(customer_id, subscription_id, data):
    """Business logic for updating a subscription."""
    update_expression_parts = []
    expression_attribute_values = {}
    expression_attribute_names = {}

    if 'name' in data:
        update_expression_parts.append('#n = :name')
        expression_attribute_values[':name'] = data['name']
        expression_attribute_names['#n'] = 'name'
    if 'category' in data:
        update_expression_parts.append('category = :category')
        expression_attribute_values[':category'] = data['category']
    if 'renewal_frequency' in data:
        update_expression_parts.append('renewal_frequency = :renewal_frequency')
        expression_attribute_values[':renewal_frequency'] = data['renewal_frequency']
    if 'renewal_date' in data:
        update_expression_parts.append('renewal_date = :renewal_date')
        expression_attribute_values[':renewal_date'] = data['renewal_date']
    if 'cost' in data:
        update_expression_parts.append('cost = :cost')
        expression_attribute_values[':cost'] = data['cost']
    if 'start_date' in data:
        update_expression_parts.append('start_date = :start_date')
        expression_attribute_values[':start_date'] = data['start_date']

    if not update_expression_parts:
        return respond(400, {'message': 'No fields provided for update'})

    update_expression = 'SET ' + ', '.join(update_expression_parts)
    dl_update_subscription(
        key={'customer_id': customer_id, 'subscription_id': subscription_id},
        update_expression=update_expression,
        expression_attribute_values=expression_attribute_values,
        expression_attribute_names=expression_attribute_names
    )
    return respond(200, {'message': 'Subscription updated successfully'})

# --- Main Lambda Handler (Transport Layer) ---
def lambda_handler(event, context):
    """
    Main Lambda handler to route requests based on HTTP method and path.
    """
    init()

    print("Received event:", json.dumps(event))
    http_method = event.get('httpMethod')
    path = event.get('path', '')
    path_parameters = event.get('pathParameters', {})
    
    customer_id = path_parameters.get('customer_id')
    subscription_id = path_parameters.get('subscription_id')
    
    try:
        if path == '/customers':
            if http_method == 'POST':
                data = json.loads(event.get('body', '{}'))
                return bl_create_customer(data)
            elif http_method == 'GET':
                return respond(200, {'customers': dl_list_customers()})
        
        elif path.startswith('/customers/') and customer_id:
            if http_method == 'GET':
                item = dl_get_customer(customer_id)
                return respond(200, item) if item else respond(404, {'message': 'Customer not found'})
            elif http_method == 'PUT':
                data = json.loads(event.get('body', '{}'))
                return bl_update_customer(customer_id, data)
            elif http_method == 'DELETE':
                deleted_item = dl_delete_customer(customer_id)
                return respond(200, {'message': 'Customer deleted successfully'}) if deleted_item else respond(404, {'message': 'Customer not found'})

        elif path.startswith('/customers/') and path.endswith('/subscriptions'):
            if http_method == 'POST':
                data = json.loads(event.get('body', '{}'))
                return bl_create_subscription(customer_id, data)
            elif http_method == 'GET':
                subscriptions = dl_list_subscriptions(customer_id)
                return respond(200, {'subscriptions': subscriptions})

        elif path.startswith('/customers/') and '/subscriptions/' in path and subscription_id:
            if http_method == 'GET':
                item = dl_get_subscription(customer_id, subscription_id)
                return respond(200, item) if item else respond(404, {'message': 'Subscription not found'})
            elif http_method == 'PUT':
                data = json.loads(event.get('body', '{}'))
                return bl_update_subscription(customer_id, subscription_id, data)
            elif http_method == 'DELETE':
                deleted_item = dl_delete_subscription(customer_id, subscription_id)
                return respond(200, {'message': 'Subscription deleted successfully'}) if deleted_item else respond(404, {'message': 'Subscription not found'})

        return respond(405, {'message': 'Method not allowed for this path'})

    except json.JSONDecodeError:
        return respond(400, {'message': 'Invalid JSON body'})
    except Exception as e:
        print(f"Error: {e}")
        return respond(500, {'message': 'Internal server error'})