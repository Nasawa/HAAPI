# HAAPI - Home Assistant API Integration

A universal API integration framework for Home Assistant 2025.11+ where each "device" represents one API endpoint. Configure and trigger API calls with responses stored as entity states and attributes.

## Features

- **Simple & Flexible**: One device = one API endpoint
- **Template Support**: Use Jinja2 templates in URLs, headers, and request bodies
- **Multiple Auth Types**: None, Basic, Bearer Token, or API Key authentication
- **Response Storage**: Capture HTTP status codes, response bodies, and headers
- **Modern HA Standards**: Built with config flow and proper entity platforms

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add this repository URL with category "Integration"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/haapi` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **HAAPI**
4. Follow the configuration steps:

### Step 1: Basic Configuration

- **Endpoint Name**: A unique identifier for this endpoint (e.g., "Cat Facts")
- **URL**: The API endpoint URL (supports Jinja2 templates)
- **HTTP Method**: GET, POST, PUT, DELETE, or PATCH
- **Headers**: Optional headers in `Key: Value` format, one per line
- **Body**: Optional request body (for POST/PUT/PATCH)
- **Content-Type**: Content type for the request (default: `application/json`)

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
  - `url`: The configured URL (with templates)
  - `request_headers`: Configured headers (raw, non-templated)
  - `request_body`: Configured body (raw, non-templated)
  - `content_type`: Content-Type header

### 3. Sensor: `{endpoint_name} Response`
- **State**: HTTP status code (200, 404, 500, etc.)
- **Attributes**:
  - `response_body`: Full response body content
  - `response_headers`: Response headers as a dictionary

*Note: Home Assistant automatically tracks when sensor states change via `last_changed` and `last_updated` attributes.*

## Usage Examples

### Example 1: Cat Facts API

**Configuration:**
- Endpoint Name: `Cat Facts`
- URL: `https://catfact.ninja/fact`
- Method: `GET`
- Auth Type: `none`

**Usage:**
1. Press the "Cat Facts Trigger" button
2. Check "Cat Facts Response" sensor (should be 200)
3. View the cat fact in "Cat Facts Response" attributes

**Automation Example:**
```yaml
automation:
  - alias: "Daily Cat Fact"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: button.press
        target:
          entity_id: button.cat_facts_trigger
      - delay: 2
      - service: notify.mobile_app
        data:
          message: >
            {{ (state_attr('sensor.cat_facts_response', 'response_body') | from_json).fact }}
```

### Example 2: POST with Template

**Configuration:**
- Endpoint Name: `Temperature Logger`
- URL: `https://api.example.com/log`
- Method: `POST`
- Headers:
  ```
  Content-Type: application/json
  ```
- Body:
  ```json
  {
    "temperature": {{ states('sensor.living_room_temperature') }},
    "timestamp": "{{ now().isoformat() }}"
  }
  ```
- Auth Type: `bearer`
- Bearer Token: `your_api_token_here`

### Example 3: Dynamic URL with Template

**Configuration:**
- Endpoint Name: `Weather API`
- URL: `https://api.weather.com/v1/location/{{ states('input_text.city_name') }}/forecast`
- Method: `GET`
- Auth Type: `api_key`
- API Key: `your_api_key`

## Template Support

You can use Jinja2 templates in:
- URLs
- Headers (values)
- Request body
- Authentication credentials

**Available template variables:**
- All Home Assistant states: `{{ states('sensor.temperature') }}`
- Time functions: `{{ now() }}`, `{{ utcnow() }}`
- State attributes: `{{ state_attr('sensor.weather', 'humidity') }}`
- And all other Home Assistant template functions

## Parsing JSON Responses

HAAPI stores raw response bodies. To parse JSON responses, create template sensors:

```yaml
template:
  - sensor:
      - name: "Cat Fact Text"
        state: >
          {{ (state_attr('sensor.cat_facts_response', 'response_body') | from_json).fact }}
```

## Troubleshooting

### Check Logs
Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.haapi: debug
```

### Common Issues

1. **Templates not rendering**: Ensure your template syntax is correct
2. **Authentication failing**: Verify credentials and auth type
3. **Connection errors**: Check URL accessibility from your HA instance

## Testing

HAAPI includes test servers to help you validate the integration locally without needing external APIs.

### Quick Start

```bash
cd test_servers
pip install -r requirements.txt

# Start the echo server (port 5000)
python echo_server.py

# Or start the authentication server (port 5001)
python auth_server.py
```

### Test Servers

#### 1. Echo Server (Port 5000)

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

#### 2. Authentication Server (Port 5001)

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

### Testing Workflows

1. **Basic Functionality Test:**
   - Start the echo server
   - Configure an endpoint pointing to `http://localhost:5000/`
   - Press the trigger button
   - Verify the response code is 200
   - Check the response body attributes contain your headers and body

2. **Template Testing:**
   - Use Home Assistant states in your templates
   - Test with: `{"temp": {{ states('sensor.temperature') | default(20) }}}`
   - Verify templates render correctly in the echoed response

3. **Authentication Testing:**
   - Start the auth server
   - Configure endpoints for each auth type
   - Verify successful authentication (200) vs failed (401)

4. **Error Handling:**
   - Test with `http://localhost:5000/status/404`
   - Test with `http://localhost:5000/status/500`
   - Verify HAAPI handles errors gracefully

See [`test_servers/README.md`](test_servers/README.md) for detailed documentation, advanced testing scenarios, and troubleshooting tips.

## Development

This integration follows the YAGNI (You Aren't Gonna Need It) philosophy - keeping things simple and focused on core functionality.

### Project Structure
```
custom_components/haapi/
├── __init__.py          # Integration setup & API caller
├── button.py            # Button entity platform
├── config_flow.py       # Configuration flow
├── const.py             # Constants
├── manifest.json        # Integration manifest
├── sensor.py            # Sensor entity platform
├── strings.json         # UI strings
└── translations/
    ├── en.json          # English translations
    ├── es.json          # Spanish translations (AI-generated)
    ├── fr.json          # French translations (AI-generated)
    └── de.json          # German translations (AI-generated)
```

## Translations

HAAPI is available in multiple languages:

- **English** (en) - Native
- **Spanish** (es) - ⚠️ AI-generated, needs review
- **French** (fr) - ⚠️ AI-generated, needs review
- **German** (de) - ⚠️ AI-generated, needs review

### Help Improve Translations

The Spanish, French, and German translations were generated by AI and may contain errors or unnatural phrasing. **Native speakers are needed to review and improve these translations!**

If you're a native speaker of any of these languages, please:

1. Review the translation file in `custom_components/haapi/translations/`
2. Fix any errors, awkward phrasing, or technical terminology issues
3. Submit a Pull Request with your improvements

### Adding New Languages

To add a new language:

1. Copy `custom_components/haapi/translations/en.json` to a new file with your language code (e.g., `it.json` for Italian)
2. Translate all text values (keep all keys in English)
3. Keep placeholder variables like `{endpoint_name}` unchanged
4. Test the translation in Home Assistant
5. Submit a Pull Request

Your contributions help make HAAPI accessible to users worldwide!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Credits

Created for Home Assistant 2025.11+

Tested with [Cat Facts API](https://catfact.ninja/)
