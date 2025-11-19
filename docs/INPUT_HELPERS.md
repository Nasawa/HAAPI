# Using Input Helpers with HAAPI

HAAPI templates work seamlessly with all Home Assistant input helpers, enabling dynamic user-controlled API configurations without editing YAML files. This is especially powerful for creating user-friendly interfaces where non-technical users can control API parameters.

## Supported Input Helpers

- `input_text` - Text input for dynamic strings (city names, search queries, IDs)
- `input_number` - Numeric sliders/inputs for thresholds, limits, counts
- `input_select` - Dropdown selections for predefined options
- `input_boolean` - Toggle switches for enabling/disabling features
- `input_datetime` - Date/time pickers for scheduling

## Example 1: Dynamic City Weather API

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

## Example 2: Dynamic POST Data with input_number

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

## Example 3: Dynamic Endpoint Selection with input_select

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

## Example 4: Conditional API Calls with input_boolean

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

## Example 5: Complete Workflow - User Input to API Call

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

## Best Practices for Input Helpers with HAAPI

1. **Use meaningful names**: Make input helper names descriptive so templates are self-documenting
2. **Set sensible defaults**: Initialize input helpers with safe, working values
3. **Add icons**: Icons help users quickly identify input helpers in the UI
4. **Validate input**: Use `| int`, `| float`, `| urlencode` filters to ensure proper data types
5. **Provide feedback**: Create template sensors to display API results in user-friendly format
6. **Handle empty values**: Use default filters like `| default('fallback')` for optional inputs
7. **Create automations**: Auto-trigger API calls when critical input helpers change
8. **Group related helpers**: Use `group` or dashboard cards to organize related inputs

## Security Considerations

⚠️ **Important**: Input helpers are user-editable, so:

- Never use input helpers for sensitive data like API keys or passwords (use secrets or config flow instead)
- Validate and sanitize user input, especially when constructing URLs
- Use URL encoding filters (`| urlencode`) for user-provided strings in URLs
- Consider rate limiting API calls triggered by input helper changes
- Test with unexpected input (empty strings, special characters, extreme numbers)

---

[← Back to README](../README.md)
