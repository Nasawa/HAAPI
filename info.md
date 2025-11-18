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
- 3 Sensors (response code, fetch time, response body with headers)

## Example Use Cases

- Fetch jokes, quotes, or daily content from public APIs
- Log sensor data to external services
- Trigger webhooks and integrations
- Control third-party devices via their REST APIs
- Fetch data from custom web services

## Getting Started Example

Try the Chuck Norris Jokes API:
- **URL**: `https://api.chucknorris.io/jokes/random`
- **Method**: GET
- **Auth**: None

Then create a template sensor to display the joke:
```yaml
template:
  - sensor:
      - name: "Chuck Norris Joke"
        state: >
          {{ (state_attr('sensor.chuck_norris_jokes_response_body', 'response_body') | from_json).value }}
```

## Documentation

Full documentation and examples available in the [README](https://github.com/yourusername/haapi/blob/main/README.md).
