import customer
from flask import Flask, jsonify, request

# Create a Flask application instance
app = Flask(__name__)

# Define the root endpoint
@app.route('/')
def home():
    return "Welcome to the API test server!"


# Define an endpoint to create a new task
@app.route('/test_api', methods=['POST'])
def create_task():
    # Check if the request body is valid
    if not request.json or 'title' not in request.json:
        return jsonify({'error': 'Invalid request body'}), 400
    
    # Create a new task item
    new_task = {
        'id': len(tasks) + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    
    # Add the new task to our list
    tasks.append(new_task)
    
    return jsonify({'task': new_task}), 201

"""
event = {
        'httpMethod': 'POST',
        'path': '/customers',
        'body': '{"name": "John", "email": "john@example.com", "password": "pass"}',
        'pathParameters': {}
    }
"""

if __name__ == "__main__":
    app.run(debug=True, port=5000)