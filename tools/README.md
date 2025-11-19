# HAAPI Tools

Utility scripts for HAAPI development and testing.

## setup_demo_endpoints.py

Automatically creates a comprehensive set of demo endpoints in your Home Assistant instance to showcase HAAPI's features.

### Features

The script creates 9 pre-configured endpoints demonstrating:
- **Simple GET Request** - Basic HTTP GET
- **POST with JSON Body** - POST with templated JSON data
- **Basic Authentication** - HTTP Basic auth with username/password
- **Bearer Token Authentication** - Bearer token in Authorization header
- **API Key Authentication** - API key in X-API-Key header
- **Custom Headers** - Multiple custom headers with templates
- **Retry Configuration** - Automatic retry on failures
- **Long Timeout** - Extended timeout configuration
- **Template Example** - Advanced Jinja2 templating showcase

### Usage

#### Interactive Mode (Recommended)

```bash
python tools/setup_demo_endpoints.py
```

The script will prompt you for:
- Home Assistant URL (default: http://localhost:8123)
- Long-lived access token
- Test server host (default: localhost)

#### Non-Interactive Mode

For scripting or automation:

```bash
python tools/setup_demo_endpoints.py \
  --ha-url http://localhost:8123 \
  --token YOUR_LONG_LIVED_ACCESS_TOKEN \
  --host localhost
```

### Prerequisites

1. **Home Assistant running** with HAAPI installed
2. **Long-lived access token**:
   - Go to your HA profile (click your name in bottom left)
   - Scroll to "Long-Lived Access Tokens"
   - Click "Create Token"
   - Copy the token (you won't see it again!)
3. **Test servers running** (optional but recommended):
   ```bash
   cd test_servers
   pip install -r requirements.txt
   python echo_server.py &      # Port 5000
   python auth_server.py &      # Port 5001
   ```

### Example Session

```bash
$ python tools/setup_demo_endpoints.py

======================================================================
  HAAPI Demo Endpoints Setup
======================================================================

ℹ Running in interactive mode

This script will create demo endpoints in your Home Assistant instance.
You'll need a long-lived access token from HA.

To create a token:
  1. Go to your HA profile (bottom left)
  2. Scroll to 'Long-Lived Access Tokens'
  3. Click 'Create Token'

Home Assistant URL [http://localhost:8123]:
Long-lived access token (hidden): ****
Test server host/IP [localhost]:

Verifying Connection
✓ Connected to Home Assistant at http://localhost:8123

Checking HAAPI Integration
✓ Found existing HAAPI entry: abc123

Creating Demo Endpoints
ℹ Adding 9 demo endpoints to HAAPI...

  Adding: Simple GET Request... ✓ Done
  Adding: POST with JSON Body... ✓ Done
  Adding: Basic Authentication... ✓ Done
  Adding: Bearer Token Authentication... ✓ Done
  Adding: API Key Authentication... ✓ Done
  Adding: Custom Headers... ✓ Done
  Adding: Retry Configuration... ✓ Done
  Adding: Long Timeout... ✓ Done
  Adding: Template Example... ✓ Done

Summary:
  Successfully created: 9/9 endpoints

✓ All demo endpoints created successfully!

Next Steps:
  1. Start the test servers:
     python test_servers/echo_server.py
     python test_servers/auth_server.py

  2. Go to Home Assistant → Settings → Devices & Services → HAAPI

  3. Try pressing the trigger buttons for different endpoints!

  4. Check the response sensors to see the results
```

### Troubleshooting

**"Failed to connect to Home Assistant"**
- Verify Home Assistant is running
- Check the URL is correct
- Ensure your access token is valid
- Try accessing the URL in a browser

**"Failed to create HAAPI entry"**
- Make sure HAAPI is installed in custom_components/
- Restart Home Assistant and try again
- Check Home Assistant logs for errors

**"Some endpoints failed to create"**
- Check Home Assistant logs for specific errors
- Verify the test servers are accessible at the specified host
- Try creating one endpoint manually through the UI to test

### Security Notes

- **Keep your access token secure** - it has full access to your HA instance
- The script only creates config entries, it doesn't modify files
- Test servers use weak passwords - **never expose them to the internet**
- Review created endpoints before triggering them in production

### What It Does

The script uses Home Assistant's REST API to:
1. Check if HAAPI is already configured
2. Create an initial HAAPI integration entry if needed
3. Use the options flow to add each demo endpoint
4. Configure authentication and other settings for each endpoint

All operations go through HA's proper config flow - no direct file manipulation.
