# Configuration reference

[← Back to the README](../README.md)

## Configuration

Setup has two parts: create a HAAPI instance once, then add your endpoints to it.

**Create the instance**

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **HAAPI**
4. Give the instance a **Name** (e.g., "Production APIs") and submit

An instance is just a container for endpoints. Most setups only need one.

**Add an endpoint**

1. On the HAAPI integration page, click the gear icon (**Configure**) on your instance
2. Choose **Add New Endpoint**
3. Fill in the two steps below

The same **Configure** menu has **Edit Endpoint** and **Remove Endpoint** for later changes. Each endpoint you add appears as its own device.

### Step 1: Basic Configuration

- **Endpoint Name**: A unique identifier for this endpoint (e.g., "Cat Facts")
- **URL**: The API endpoint URL (supports Jinja2 templates)
- **HTTP Method**: GET, POST, PUT, DELETE, or PATCH
- **Headers**: Optional headers in `Key: Value` format, one per line
- **Body**: Optional request body (for POST/PUT/PATCH)
- **Content-Type**: Content type for the request (default: `application/json`)
- **Timeout**: Request timeout in seconds (1-300, default: 10)
- **Verify SSL Certificate**: Enable/disable SSL certificate verification (default: enabled)
- **Max Response Size**: Maximum response body size in bytes (0-10000000, default: 10240/10KB, 0 = unlimited)
- **Number of Retries**: Retry attempts for failed requests (0-5, default: 0)
- **Retry Delay**: Delay in seconds between retry attempts (1-60, default: 1)

### Step 2: Authentication

- **Authentication Type**: Choose from:
  - `none`: No authentication
  - `basic`: HTTP Basic authentication (username + password)
  - `bearer`: Bearer token authentication
  - `api_key`: API Key sent as `X-API-Key` header
- Fill in the relevant fields based on your auth type

## Entities

Each configured endpoint creates a device with the following entities:

### 1. Button: `{endpoint_name} Trigger`
- Press this button to trigger the API call

### 2. Sensor: `{endpoint_name} Request`
- **State**: HTTP method (GET, POST, PUT, DELETE, PATCH)
- **Attributes**:
  - `url`: The configured URL (with templates), without credentials or query string
  - `content_type`: Content-Type header
  - `timeout`: Configured timeout in seconds
  - `verify_ssl`: SSL certificate verification enabled/disabled
  - `max_response_size`: Maximum response body size in bytes
  - `retries`: Number of retry attempts configured
  - `retry_delay`: Delay in seconds between retry attempts

### 3. Sensor: `{endpoint_name} Response`
- **State**: HTTP status code (200, 404, 500, etc.)
- **Attributes**:
  - `response_body`: Response body content (may be truncated if exceeds max_response_size)
  - `response_headers`: Response headers as a dictionary
  - `truncated`: Boolean indicating if response was truncated due to size limit

*Note: Home Assistant automatically tracks when sensor states change via `last_changed` and `last_updated` attributes.*
