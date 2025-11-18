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

- **Endpoint Name**: A unique identifier for this endpoint (e.g., "Chuck Norris Jokes")
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

### 2. Sensor: `{endpoint_name} Response Code`
- **State**: HTTP status code (200, 404, 500, etc.)
- **Attributes**:
  - `url`: The configured URL
  - `method`: The HTTP method used

### 3. Sensor: `{endpoint_name} Last Fetch Time`
- **State**: Timestamp of the last API call
- **Device Class**: timestamp

### 4. Sensor: `{endpoint_name} Response Body`
- **State**: Timestamp of last fetch (to avoid state size limits)
- **Attributes**:
  - `response_body`: Full response body content
  - `response_headers`: Response headers as a dictionary

## Usage Examples

### Example 1: Chuck Norris Jokes API

**Configuration:**
- Endpoint Name: `Chuck Norris Jokes`
- URL: `https://api.chucknorris.io/jokes/random`
- Method: `GET`
- Auth Type: `none`

**Usage:**
1. Press the "Chuck Norris Jokes Trigger" button
2. Check "Chuck Norris Jokes Response Code" sensor (should be 200)
3. View the joke in "Chuck Norris Jokes Response Body" attributes

**Automation Example:**
```yaml
automation:
  - alias: "Daily Chuck Norris Joke"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: button.press
        target:
          entity_id: button.chuck_norris_jokes_trigger
      - delay: 2
      - service: notify.mobile_app
        data:
          message: >
            {{ state_attr('sensor.chuck_norris_jokes_response_body', 'response_body') }}
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
      - name: "Chuck Norris Joke Text"
        state: >
          {{ state_attr('sensor.chuck_norris_jokes_response_body', 'response_body') | from_json | attr('value') }}
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
    └── en.json          # English translations
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Credits

Created for Home Assistant 2025.11+

Tested with [Chuck Norris Jokes API](https://api.chucknorris.io/)
