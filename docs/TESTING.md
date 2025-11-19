# Testing HAAPI

HAAPI includes test servers to help you validate the integration locally without needing external APIs.

## Quick Start

```bash
cd test_servers
pip install -r requirements.txt

# Start the echo server (port 5000)
python echo_server.py

# Or start the authentication server (port 5001)
python auth_server.py
```

## Test Servers

### 1. Echo Server (Port 5000)

A development server that echoes back all request details, perfect for testing HAAPI functionality.

**Key Endpoints:**
- `GET/POST/PUT/DELETE/PATCH http://localhost:5000/` - Echo all request details
- `GET http://localhost:5000/status/<code>` - Test specific HTTP status codes
- `GET http://localhost:5000/delay/<seconds>` - Test delayed responses
- `GET http://localhost:5000/json` - Sample JSON response

**Example Configuration:**
```yaml
Endpoint Name: Local Echo Test
URL: http://localhost:5000/test
Method: POST
Headers:
  X-Test-Header: TestValue
Body:
  {"message": "Hello from HAAPI", "timestamp": "{{ now().isoformat() }}"}
```

### 2. Authentication Server (Port 5001)

Test all authentication methods supported by HAAPI.

**Test Credentials:**
- **Basic Auth:** username=`testuser`, password=`testpass`
- **Bearer Token:** `test-bearer-token-12345`
- **API Key:** `test-api-key-67890`

**Endpoints:**
- `GET http://localhost:5001/` - Show all available endpoints and credentials
- `GET http://localhost:5001/auth/basic` - Test Basic authentication
- `GET http://localhost:5001/auth/bearer` - Test Bearer token
- `GET http://localhost:5001/auth/apikey` - Test API key
- `GET http://localhost:5001/auth/any` - Accepts any auth method

**Example Configuration (Basic Auth):**
```yaml
Endpoint Name: Auth Test
URL: http://localhost:5001/auth/basic
Method: GET
Authentication Type: Basic
Username: testuser
Password: testpass
```

## Testing Workflows

### 1. Basic Functionality Test
- Start the echo server
- Configure an endpoint pointing to `http://localhost:5000/`
- Press the trigger button
- Verify the response code is 200
- Check the response body attributes contain your headers and body

### 2. Template Testing
- Use Home Assistant states in your templates
- Test with: `{"temp": {{ states('sensor.temperature') | default(20) }}}`
- Verify templates render correctly in the echoed response

### 3. Authentication Testing
- Start the auth server
- Configure endpoints for each auth type
- Verify successful authentication (200) vs failed (401)

### 4. Error Handling
- Test with `http://localhost:5000/status/404`
- Test with `http://localhost:5000/status/500`
- Verify HAAPI handles errors gracefully

## Advanced Testing

See [`test_servers/README.md`](../test_servers/README.md) for:
- Detailed test server documentation
- Advanced testing scenarios
- Troubleshooting tips
- Custom test endpoint creation

---

[← Back to README](../README.md)
