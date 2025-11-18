# HAAPI Test Servers

Test servers for validating the HAAPI Home Assistant integration. These servers echo back request details and support various authentication methods.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Servers

### 1. Echo Server (Port 5000)

A simple server that echoes back all request details including headers and body content.

**Start the server:**
```bash
python echo_server.py
```

**Endpoints:**

- `GET/POST/PUT/DELETE/PATCH http://localhost:5000/` - Echo all request details
- `GET/POST/PUT/DELETE/PATCH http://localhost:5000/<any-path>` - Echo with custom path
- `GET http://localhost:5000/status/<code>` - Return specific HTTP status code
- `GET http://localhost:5000/delay/<seconds>` - Delay response (max 30 seconds)
- `GET http://localhost:5000/json` - Return sample JSON data

**Example HAAPI Configuration:**
```yaml
Endpoint Name: Echo Test
URL: http://localhost:5000/
Method: POST
Headers:
  X-Custom-Header: MyValue
  Content-Type: application/json
Body:
  {"test": "data"}
```

### 2. Authentication Server (Port 5001)

Tests different authentication methods supported by HAAPI.

**Start the server:**
```bash
python auth_server.py
```

**Test Credentials:**
- **Basic Auth:** username=`testuser`, password=`testpass`
- **Bearer Token:** `test-bearer-token-12345`
- **API Key:** `test-api-key-67890` (via X-API-Key header)

**Endpoints:**

- `GET http://localhost:5001/` - Show server info and credentials
- `GET/POST http://localhost:5001/auth/basic` - Requires Basic Auth
- `GET/POST http://localhost:5001/auth/bearer` - Requires Bearer Token
- `GET/POST http://localhost:5001/auth/apikey` - Requires API Key
- `GET/POST http://localhost:5001/auth/any` - Accepts any auth method

**Example HAAPI Configurations:**

**Basic Auth:**
```yaml
Endpoint Name: Basic Auth Test
URL: http://localhost:5001/auth/basic
Method: GET
Authentication Type: Basic
Username: testuser
Password: testpass
```

**Bearer Token:**
```yaml
Endpoint Name: Bearer Token Test
URL: http://localhost:5001/auth/bearer
Method: GET
Authentication Type: Bearer
Bearer Token: test-bearer-token-12345
```

**API Key:**
```yaml
Endpoint Name: API Key Test
URL: http://localhost:5001/auth/apikey
Method: GET
Authentication Type: API Key
API Key: test-api-key-67890
```

## Testing with HAAPI

1. Start one or both servers
2. In Home Assistant, go to Settings → Devices & Services → Add Integration → HAAPI
3. Configure an endpoint using the examples above
4. Press the Trigger button to test
5. Check the sensor entities for response details

## Response Format

The echo server returns JSON with the following structure:

```json
{
  "timestamp": "2025-11-18T12:00:00Z",
  "method": "POST",
  "path": "/test",
  "query_params": {},
  "headers": {
    "Content-Type": "application/json",
    "X-Custom-Header": "MyValue"
  },
  "body": {
    "test": "data"
  },
  "remote_addr": "127.0.0.1"
}
```

## Advanced Testing

### Test Templates

You can test Jinja2 templates in HAAPI by using Home Assistant state values:

```yaml
URL: http://localhost:5000/temperature
Body: |
  {
    "sensor": "living_room",
    "temperature": {{ states('sensor.living_room_temperature') }},
    "timestamp": "{{ now().isoformat() }}"
  }
```

### Test Different HTTP Methods

Configure multiple endpoints with different HTTP methods to test:
- GET - Retrieve data
- POST - Create data
- PUT - Update data
- DELETE - Delete data
- PATCH - Partial update

### Test Error Handling

Use the status code endpoint to test error handling:
```
http://localhost:5000/status/404  (Not Found)
http://localhost:5000/status/500  (Server Error)
http://localhost:5000/status/401  (Unauthorized)
```

## Troubleshooting

**Connection Refused:**
- Make sure the server is running
- Check that the port is not already in use
- If running in Docker/VM, ensure proper network configuration

**Authentication Fails:**
- Verify credentials match the test credentials shown when server starts
- Check that authentication headers are being sent correctly
- Use the `/` endpoint on auth server to see valid credentials

**Templates Not Working:**
- Ensure proper Jinja2 syntax
- Check Home Assistant logs for template errors
- Test templates in Developer Tools → Template first
