# Examples and templates

[← Back to the README](../README.md)

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
      - action: haapi.request
        target:
          entity_id: button.cat_facts_trigger
        response_variable: cat_fact
      - action: notify.mobile_app
        data:
          message: >
            {{ (cat_fact.body | from_json).fact }}
```

`haapi.request` waits for this call to finish and returns its response to `cat_fact`, so the notification always uses the fresh result without a fixed delay.

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
    "temperature": "{{ states('sensor.living_room_temperature') }}",
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

**📖 [Read the full Input Helpers guide](INPUT_HELPERS.md)** for:
- 5 detailed examples covering all input helper types
- Best practices and security considerations
- Complete workflow examples with automations and dashboards
