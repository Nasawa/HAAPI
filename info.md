# HAAPI - Home Assistant API Integration

A universal API integration framework for Home Assistant where each "device" represents one API endpoint.

## Quick Start

1. Install HAAPI through HACS or manually
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "HAAPI"
5. Configure your first API endpoint

## Key Features

- **One Device = One Endpoint**: Simple and organized
- **Jinja2 Templates**: Dynamic URLs, headers, and body content
- **Multiple Auth Methods**: Basic, Bearer, API Key, or None
- **Full Response Capture**: Status codes, headers, and body content
- **Button Trigger**: Manual API calls with a button press
- **Perfect for Automations**: Integrate any REST API into your Home Assistant workflows

## Entities Created

Each endpoint creates:
- 1 Button (to trigger the API call)
- 2 Sensors (request configuration, response data)

## Example Use Cases

- Fetch jokes, quotes, or daily content from public APIs
- Log sensor data to external services
- Trigger webhooks and integrations
- Control third-party devices via their REST APIs
- Fetch data from custom web services

## Getting Started Example

Try the Cat Facts API:
- **URL**: `https://catfact.ninja/fact`
- **Method**: GET
- **Auth**: None

Then create a template sensor to display the fact:
```yaml
template:
  - sensor:
      - name: "Cat Fact"
        state: >
          {{ (state_attr('sensor.cat_facts_response', 'response_body') | from_json).fact }}
```

## Documentation

Full documentation and examples available in the [README](https://github.com/Nasawa/HAAPI/blob/main/README.md).
