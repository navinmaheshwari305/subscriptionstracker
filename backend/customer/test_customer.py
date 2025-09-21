import pytest
import uuid
from unittest.mock import patch, MagicMock
import customer
import os
import boto3
import json

do_mock = False
customer_table_name = "Customers"
subscription_table_name = "Subscriptions"   

@pytest.fixture(autouse=True)
def patch_init_tables(monkeypatch):
    if do_mock:
        # Patch the init function to avoid real DynamoDB calls
        monkeypatch.setattr(customer, "init", lambda: None)
        monkeypatch.setattr(customer, "customers_table", MagicMock())
        monkeypatch.setattr(customer, "subscriptions_table", MagicMock())
    else:
        # Use the real init function to create tables in local DynamoDB
        from backend.db.lambda_handler import init, lambda_handler
        # Set unique table names for each test run to avoid conflicts
        
        os.environ['NAVINM_CUSTOMERS_TABLE_NAME'] =  customer_table_name+ str(uuid.uuid4())
        os.environ['NAVINM_SUBSCRIPTIONS_TABLE_NAME'] =  subscription_table_name + str(uuid.uuid4())
        init()
        lambda_handler(None, None)

        customer.init()

# --- Customer Tests ---

def test_list_tables():
    if do_mock:
        return []
    else:
        tables = customer.dynamodb_resource.meta.client.list_tables()['TableNames']
        print(json.dumps(tables, indent=2))
        assert isinstance(tables, list)
        assert len(tables) >= 0
        

def test_create_customer_success(monkeypatch):
    data = {'name': 'John', 'email': 'john@example.com', 'password': 'pass'}
    event = {
        'httpMethod': 'POST',
        'path': '/customers',
        'body': '{"name": "John", "email": "john@example.com", "password": "pass"}',
        'pathParameters': {}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_create_customer", lambda item: None)
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 201
    assert 'customer_id' in response['body']

def test_create_customer_missing_fields():
    event = {
        'httpMethod': 'POST',
        'path': '/customers',
        'body': '{"name": "John"}',
        'pathParameters': {}
    }
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 400

def test_get_customer_success(monkeypatch):
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'GET',
        'path': f'/customers/{customer_id}',
        'pathParameters': {'customer_id': customer_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_get_customer", lambda cid: {'customer_id': cid, 'name': 'John'})
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 200
    assert 'John' in response['body']

def test_get_customer_not_found(monkeypatch):
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'GET',
        'path': f'/customers/{customer_id}',
        'pathParameters': {'customer_id': customer_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_get_customer", lambda cid: None)
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 404

def test_update_customer_success(monkeypatch):
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'PUT',
        'path': f'/customers/{customer_id}',
        'body': '{"name": "Jane"}',
        'pathParameters': {'customer_id': customer_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_update_customer", lambda **kwargs: None)
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 200

def test_update_customer_no_fields():
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'PUT',
        'path': f'/customers/{customer_id}',
        'body': '{}',
        'pathParameters': {'customer_id': customer_id}
    }
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 400

def test_delete_customer_success(monkeypatch):
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'DELETE',
        'path': f'/customers/{customer_id}',
        'pathParameters': {'customer_id': customer_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_delete_customer", lambda cid: {'customer_id': cid})
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 200

def test_delete_customer_not_found(monkeypatch):
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'DELETE',
        'path': f'/customers/{customer_id}',
        'pathParameters': {'customer_id': customer_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_delete_customer", lambda cid: None)
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 404

def test_list_customers(monkeypatch):
    event = {
        'httpMethod': 'GET',
        'path': '/customers',
        'pathParameters': {}
    }
    if do_mock:
            
            monkeypatch.setattr(customer, "dl_list_customers", lambda: [{'customer_id': '1', 'name': 'John'}])
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 200
    assert 'customers' in response['body']

# --- Subscription Tests ---

def test_create_subscription_success(monkeypatch):
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'POST',
        'path': f'/customers/{customer_id}/subscriptions',
        'body': '{"name": "Netflix", "category": "Entertainment", "renewal_frequency": "Monthly", "renewal_date": "2025-10-01", "cost": 10, "start_date": "2025-09-01"}',
        'pathParameters': {'customer_id': customer_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_create_subscription", lambda item: None)
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 201
    assert 'subscription_id' in response['body']

def test_create_subscription_missing_fields():
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'POST',
        'path': f'/customers/{customer_id}/subscriptions',
        'body': '{"name": "Netflix"}',
        'pathParameters': {'customer_id': customer_id}
    }
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 400

def test_get_subscription_success(monkeypatch):
    customer_id = str(uuid.uuid4())
    subscription_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'GET',
        'path': f'/customers/{customer_id}/subscriptions/{subscription_id}',
        'pathParameters': {'customer_id': customer_id, 'subscription_id': subscription_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_get_subscription", lambda cid, sid: {'subscription_id': sid, 'name': 'Netflix'})
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 200
    assert 'Netflix' in response['body']

def test_get_subscription_not_found(monkeypatch):
    customer_id = str(uuid.uuid4())
    subscription_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'GET',
        'path': f'/customers/{customer_id}/subscriptions/{subscription_id}',
        'pathParameters': {'customer_id': customer_id, 'subscription_id': subscription_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_get_subscription", lambda cid, sid: None)
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 404

def test_update_subscription_success(monkeypatch):
    customer_id = str(uuid.uuid4())
    subscription_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'PUT',
        'path': f'/customers/{customer_id}/subscriptions/{subscription_id}',
        'body': '{"name": "Prime"}',
        'pathParameters': {'customer_id': customer_id, 'subscription_id': subscription_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_update_subscription", lambda **kwargs: None)
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 200

def test_update_subscription_no_fields():
    customer_id = str(uuid.uuid4())
    subscription_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'PUT',
        'path': f'/customers/{customer_id}/subscriptions/{subscription_id}',
        'body': '{}',
        'pathParameters': {'customer_id': customer_id, 'subscription_id': subscription_id}
    }
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 400

def test_delete_subscription_success(monkeypatch):
    customer_id = str(uuid.uuid4())
    subscription_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'DELETE',
        'path': f'/customers/{customer_id}/subscriptions/{subscription_id}',
        'pathParameters': {'customer_id': customer_id, 'subscription_id': subscription_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_delete_subscription", lambda cid, sid: {'subscription_id': sid})
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 200

def test_delete_subscription_not_found(monkeypatch):
    customer_id = str(uuid.uuid4())
    subscription_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'DELETE',
        'path': f'/customers/{customer_id}/subscriptions/{subscription_id}',
        'pathParameters': {'customer_id': customer_id, 'subscription_id': subscription_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_delete_subscription", lambda cid, sid: None)
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 404

def test_list_subscriptions(monkeypatch):
    customer_id = str(uuid.uuid4())
    event = {
        'httpMethod': 'GET',
        'path': f'/customers/{customer_id}/subscriptions',
        'pathParameters': {'customer_id': customer_id}
    }
    if do_mock:
            monkeypatch.setattr(customer, "dl_list_subscriptions", lambda cid: [{'subscription_id': '1', 'name': 'Netflix'}])
    response = customer.lambda_handler(event, None)
    assert response['statusCode'] == 200
    assert 'subscriptions' in response['body']