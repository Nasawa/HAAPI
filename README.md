# HAAPI - Home Assistant API Integration

A universal API integration framework for Home Assistant 2025.11+ where each "device" represents one API endpoint. Configure and trigger API calls with responses stored as entity states and attributes.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [HACS (Recommended)](#hacs-recommended)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)
  - [Step 1: Basic Configuration](#step-1-basic-configuration)
  - [Step 2: Authentication](#step-2-authentication)
- [Entities](#entities)
- [Usage Examples](#usage-examples)
- [Using Input Helpers](#using-input-helpers)
- [Template Support](#template-support)
- [Parsing JSON Responses](#parsing-json-responses)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)
- [Development](#development)
- [Translations](#translations)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)

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

## Using Input Helpers

HAAPI templates work seamlessly with all Home Assistant input helpers, enabling dynamic user-controlled API configurations without editing YAML files. This is especially powerful for creating user-friendly interfaces where non-technical users can control API parameters.

### Supported Input Helpers

- `input_text` - Text input for dynamic strings (city names, search queries, IDs)
- `input_number` - Numeric sliders/inputs for thresholds, limits, counts
- `input_select` - Dropdown selections for predefined options
- `input_boolean` - Toggle switches for enabling/disabling features
- `input_datetime` - Date/time pickers for scheduling

### Example 1: Dynamic City Weather API

Use `input_text` to allow users to change the city for weather queries via the UI.

**Step 1: Create Input Helper**

Add to your `configuration.yaml`:
```yaml
input_text:
  city_name:
    name: City Name
    initial: London
    icon: mdi:city
```

**Step 2: Configure HAAPI Endpoint**
- **Endpoint Name**: `Weather by City`
- **URL**: `https://api.weather.com/v3/wx/forecast/daily/5day?city={{ states('input_text.city_name') }}&format=json`
- **Method**: `GET`
- **Auth Type**: `api_key`
- **API Key**: `your_api_key_here`

**Step 3: Create Automation**
```yaml
automation:
  - alias: "Update Weather on City Change"
    trigger:
      - platform: state
        entity_id: input_text.city_name
    action:
      - delay: 1  # Brief delay to allow user to finish typing
      - service: button.press
        target:
          entity_id: button.weather_by_city_trigger
```

**Result**: Users can change the city in the UI, and the automation automatically triggers the API call with the new city name.

### Example 2: Dynamic POST Data with input_number

Use `input_number` for user-configurable thresholds or numeric parameters in API requests.

**Step 1: Create Input Helpers**
```yaml
input_number:
  temperature_threshold:
    name: Temperature Threshold
    min: 0
    max: 100
    step: 0.5
    initial: 22
    unit_of_measurement: "°C"
    icon: mdi:thermometer

  humidity_threshold:
    name: Humidity Threshold
    min: 0
    max: 100
    step: 1
    initial: 60
    unit_of_measurement: "%"
    icon: mdi:water-percent
```

**Step 2: Configure HAAPI Endpoint**
- **Endpoint Name**: `Alert Config`
- **URL**: `https://api.example.com/alerts/configure`
- **Method**: `POST`
- **Headers**:
  ```
  Content-Type: application/json
  ```
- **Body**:
  ```json
  {
    "temperature_threshold": {{ states('input_number.temperature_threshold') | float }},
    "humidity_threshold": {{ states('input_number.humidity_threshold') | int }},
    "current_temp": {{ states('sensor.living_room_temperature') | float }},
    "current_humidity": {{ states('sensor.living_room_humidity') | int }},
    "timestamp": "{{ now().isoformat() }}"
  }
  ```

**Step 3: Create Dashboard Card**
```yaml
type: entities
title: Alert Configuration
entities:
  - entity: input_number.temperature_threshold
  - entity: input_number.humidity_threshold
  - entity: button.alert_config_trigger
```

**Result**: Users adjust thresholds with sliders, then press the button to send updated configuration to the API.

### Example 3: Dynamic Endpoint Selection with input_select

Use `input_select` to let users choose between different API endpoints or data sources.

**Step 1: Create Input Helper**
```yaml
input_select:
  api_data_source:
    name: Data Source
    options:
      - production
      - staging
      - development
    initial: production
    icon: mdi:server-network

  report_type:
    name: Report Type
    options:
      - daily
      - weekly
      - monthly
      - yearly
    initial: daily
    icon: mdi:chart-line
```

**Step 2: Configure HAAPI Endpoint**
- **Endpoint Name**: `Analytics Report`
- **URL**: `https://{{ states('input_select.api_data_source') }}.api.example.com/reports/{{ states('input_select.report_type') }}`
- **Method**: `GET`
- **Auth Type**: `bearer`
- **Bearer Token**: `your_token_here`

**Result**: Users select environment and report type from dropdowns, dynamically changing both the subdomain and endpoint path.

### Example 4: Conditional API Calls with input_boolean

Use `input_boolean` to enable/disable features or include optional parameters.

**Step 1: Create Input Helper**
```yaml
input_boolean:
  include_debug_info:
    name: Include Debug Information
    initial: false
    icon: mdi:bug
```

**Step 2: Configure HAAPI Endpoint**
- **Endpoint Name**: `Status Report`
- **URL**: `https://api.example.com/status`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "device_id": "{{ state_attr('device_tracker.phone', 'id') }}",
    "status": "{{ states('sensor.system_status') }}"
    {% if is_state('input_boolean.include_debug_info', 'on') %}
    ,
    "debug": {
      "uptime": "{{ states('sensor.uptime') }}",
      "memory": "{{ states('sensor.memory_use_percent') }}",
      "cpu": "{{ states('sensor.processor_use_percent') }}"
    }
    {% endif %}
  }
  ```

**Result**: Debug information is only included in the API request when the toggle is enabled.

### Example 5: Complete Workflow - User Input to API Call

This example shows a complete workflow where a user updates multiple input helpers, then triggers an API call.

**Step 1: Create Input Helpers**
```yaml
input_text:
  search_query:
    name: Search Query
    initial: ""
    icon: mdi:magnify

input_number:
  max_results:
    name: Maximum Results
    min: 1
    max: 100
    initial: 10
    icon: mdi:numeric

input_select:
  search_category:
    name: Category
    options:
      - all
      - products
      - articles
      - users
    initial: all
    icon: mdi:filter
```

**Step 2: Configure HAAPI Endpoint**
- **Endpoint Name**: `Search API`
- **URL**: `https://api.example.com/search?q={{ states('input_text.search_query') | urlencode }}&category={{ states('input_select.search_category') }}&limit={{ states('input_number.max_results') | int }}`
- **Method**: `GET`

**Step 3: Create Dashboard**
```yaml
type: vertical-stack
cards:
  - type: entities
    title: Search Parameters
    entities:
      - entity: input_text.search_query
      - entity: input_select.search_category
      - entity: input_number.max_results
      - entity: button.search_api_trigger

  - type: markdown
    title: Last Search Results
    content: >
      **Status:** {{ states('sensor.search_api_response') }}
      
      **Results:** 
      {% set body = state_attr('sensor.search_api_response', 'response_body') %}
      {% if body %}
      {{ (body | from_json).results | length }} items found
      {% endif %}
```

**Result**: Users configure search parameters through the UI, press the trigger button, and see results - all without editing any configuration files.

### Best Practices for Input Helpers with HAAPI

1. **Use meaningful names**: Make input helper names descriptive so templates are self-documenting
2. **Set sensible defaults**: Initialize input helpers with safe, working values
3. **Add icons**: Icons help users quickly identify input helpers in the UI
4. **Validate input**: Use `| int`, `| float`, `| urlencode` filters to ensure proper data types
5. **Provide feedback**: Create template sensors to display API results in user-friendly format
6. **Handle empty values**: Use default filters like `| default('fallback')` for optional inputs
7. **Create automations**: Auto-trigger API calls when critical input helpers change
8. **Group related helpers**: Use `group` or dashboard cards to organize related inputs

### Security Considerations

⚠️ **Important**: Input helpers are user-editable, so:

- Never use input helpers for sensitive data like API keys or passwords (use secrets or config flow instead)
- Validate and sanitize user input, especially when constructing URLs
- Use URL encoding filters (`| urlencode`) for user-provided strings in URLs
- Consider rate limiting API calls triggered by input helper changes
- Test with unexpected input (empty strings, special characters, extreme numbers)

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
