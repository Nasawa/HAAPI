"""
Authentication Test Server for testing HAAPI integration.

This server tests different authentication methods:
- Basic Auth
- Bearer Token
- API Key
"""
from flask import Flask, request, jsonify
from functools import wraps
import base64

app = Flask(__name__)

# Test credentials
VALID_USERNAME = 'testuser'
VALID_PASSWORD = 'testpass'
VALID_BEARER_TOKEN = 'test-bearer-token-12345'
VALID_API_KEY = 'test-api-key-67890'


def check_basic_auth():
    """Check if Basic Auth credentials are valid."""
    auth = request.authorization
    print(f"[DEBUG] Basic Auth check - Authorization: {auth}")
    if auth:
        print(f"[DEBUG] Username: {auth.username}, Password: {auth.password}")
        print(f"[DEBUG] Expected - Username: {VALID_USERNAME}, Password: {VALID_PASSWORD}")
        if auth.username == VALID_USERNAME and auth.password == VALID_PASSWORD:
            print("[DEBUG] ✓ Authentication successful")
            return True
        else:
            print("[DEBUG] ✗ Authentication failed - wrong credentials")
    else:
        print("[DEBUG] ✗ No authorization header found")
    return False


def check_bearer_token():
    """Check if Bearer token is valid."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        return token == VALID_BEARER_TOKEN
    return False


def check_api_key():
    """Check if API key is valid."""
    api_key = request.headers.get('X-API-Key', '')
    return api_key == VALID_API_KEY


@app.route('/auth/basic', methods=['GET', 'POST', 'PUT', 'DELETE'])
def basic_auth():
    """Endpoint requiring Basic authentication."""
    if check_basic_auth():
        return jsonify({
            'message': 'Basic authentication successful!',
            'username': request.authorization.username,
            'method': request.method
        }), 200

    return jsonify({
        'error': 'Authentication required',
        'hint': f'Use username: {VALID_USERNAME}, password: {VALID_PASSWORD}'
    }), 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}


@app.route('/auth/bearer', methods=['GET', 'POST', 'PUT', 'DELETE'])
def bearer_auth():
    """Endpoint requiring Bearer token authentication."""
    if check_bearer_token():
        return jsonify({
            'message': 'Bearer token authentication successful!',
            'method': request.method
        }), 200

    return jsonify({
        'error': 'Authentication required',
        'hint': f'Use Bearer token: {VALID_BEARER_TOKEN}'
    }), 401


@app.route('/auth/apikey', methods=['GET', 'POST', 'PUT', 'DELETE'])
def apikey_auth():
    """Endpoint requiring API key authentication."""
    if check_api_key():
        return jsonify({
            'message': 'API key authentication successful!',
            'method': request.method
        }), 200

    return jsonify({
        'error': 'Authentication required',
        'hint': f'Use X-API-Key header: {VALID_API_KEY}'
    }), 401


@app.route('/auth/any', methods=['GET', 'POST', 'PUT', 'DELETE'])
def any_auth():
    """Endpoint accepting any authentication method."""
    if check_basic_auth():
        auth_type = 'Basic Auth'
        username = request.authorization.username
    elif check_bearer_token():
        auth_type = 'Bearer Token'
        username = None
    elif check_api_key():
        auth_type = 'API Key'
        username = None
    else:
        return jsonify({
            'error': 'Authentication required',
            'accepted_methods': ['Basic', 'Bearer', 'API Key'],
            'hints': {
                'basic': f'username: {VALID_USERNAME}, password: {VALID_PASSWORD}',
                'bearer': f'token: {VALID_BEARER_TOKEN}',
                'apikey': f'X-API-Key: {VALID_API_KEY}'
            }
        }), 401

    response = {
        'message': 'Authentication successful!',
        'auth_type': auth_type,
        'method': request.method
    }
    if username:
        response['username'] = username

    return jsonify(response), 200


@app.route('/')
def index():
    """Show available endpoints."""
    return jsonify({
        'message': 'HAAPI Authentication Test Server',
        'endpoints': {
            '/auth/basic': 'Basic authentication',
            '/auth/bearer': 'Bearer token authentication',
            '/auth/apikey': 'API key authentication',
            '/auth/any': 'Any authentication method'
        },
        'credentials': {
            'basic': {
                'username': VALID_USERNAME,
                'password': VALID_PASSWORD
            },
            'bearer': {
                'token': VALID_BEARER_TOKEN
            },
            'apikey': {
                'header': 'X-API-Key',
                'key': VALID_API_KEY
            }
        }
    })


if __name__ == '__main__':
    print("=" * 60)
    print("HAAPI Authentication Test Server")
    print("=" * 60)
    print("\nTest Credentials:")
    print(f"  Basic Auth:   username={VALID_USERNAME}, password={VALID_PASSWORD}")
    print(f"  Bearer Token: {VALID_BEARER_TOKEN}")
    print(f"  API Key:      {VALID_API_KEY}")
    print("\nEndpoints:")
    print("  /auth/basic   - Requires Basic Auth")
    print("  /auth/bearer  - Requires Bearer Token")
    print("  /auth/apikey  - Requires API Key (X-API-Key header)")
    print("  /auth/any     - Accepts any auth method")
    print("\nStarting server on http://localhost:5001")
    print("=" * 60)
    print()

    app.run(host='0.0.0.0', port=5001, debug=True)
