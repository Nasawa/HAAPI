# HAAPI - Home Assistant API Integration

A universal API integration framework for Home Assistant 2025.11+ where each "device" represents one API endpoint. Configure and trigger API calls with responses stored as entity states and attributes.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [Usage](#usage)
  - [Quick Start Examples](#quick-start-examples)
  - [Template Support](#template-support)
  - [Parsing JSON Responses](#parsing-json-responses)
  - [Using Input Helpers](#using-input-helpers)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)
- [Development](#development)
- [Translations](#translations)
- [Contributing](#contributing)

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
- **Timeout**: Request timeout in seconds (1-300, default: 10)

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
  - `timeout`: Configured timeout in seconds

### 3. Sensor: `{endpoint_name} Response`
- **State**: HTTP status code (200, 404, 500, etc.)
- **Attributes**:
  - `response_body`: Full response body content
  - `response_headers`: Response headers as a dictionary

*Note: Home Assistant automatically tracks when sensor states change via `last_changed` and `last_updated` attributes.*

## Usage

### Quick Start Examples

#### Example 1: Cat Facts API

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

#### Example 2: POST with Template

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

#### Example 3: Dynamic URL with Template

**Configuration:**
- Endpoint Name: `Weather API`
- URL: `https://api.weather.com/v1/location/{{ states('input_text.city_name') }}/forecast`
- Method: `GET`
- Auth Type: `api_key`
- API Key: `your_api_key`

### Template Support

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

### Parsing JSON Responses

HAAPI stores raw response bodies. To parse JSON responses, create template sensors:

```yaml
template:
  - sensor:
      - name: "Cat Fact Text"
        state: >
          {{ (state_attr('sensor.cat_facts_response', 'response_body') | from_json).fact }}
```

### Using Input Helpers

HAAPI templates work seamlessly with all Home Assistant input helpers (`input_text`, `input_number`, `input_select`, `input_boolean`, `input_datetime`), enabling dynamic user-controlled API configurations without editing YAML files.

**Quick Example:**
```yaml
# configuration.yaml
input_text:
  city_name:
    name: City Name
    initial: London

# HAAPI endpoint URL
https://api.weather.com/forecast?city={{ states('input_text.city_name') | urlencode }}
```

**📖 [Read the full Input Helpers guide](docs/INPUT_HELPERS.md)** for:
- 5 detailed examples covering all input helper types
- Best practices and security considerations
- Complete workflow examples with automations and dashboards

## Troubleshooting

<details>
<summary><strong>Click to expand troubleshooting guide</strong></summary>

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

</details>

## Testing

HAAPI includes test servers for local validation without external APIs.

**Quick Start:**
```bash
cd test_servers
pip install -r requirements.txt
python echo_server.py      # Port 5000 - Echo server
python auth_server.py      # Port 5001 - Auth testing
```

**📖 [Read the full Testing guide](docs/TESTING.md)** for:
- Detailed test server documentation
- Testing workflows and best practices
- Authentication testing examples

## Development

This integration follows the YAGNI (You Aren't Gonna Need It) philosophy - keeping things simple and focused on core functionality.

<details>
<summary><strong>Project Structure</strong></summary>

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

docs/
├── INPUT_HELPERS.md     # Comprehensive input helper guide
└── TESTING.md           # Testing documentation

test_servers/
├── echo_server.py       # Local testing server
├── auth_server.py       # Authentication testing server
└── README.md            # Test server documentation
```

</details>

## Translations

<details>
<summary><strong>Available Languages & Contributing</strong></summary>

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

</details>

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Credits

Created for Home Assistant 2025.11+

Tested with [Cat Facts API](https://catfact.ninja/)
