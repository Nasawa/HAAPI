#!/usr/bin/env python3
"""
Setup Demo Endpoints for HAAPI

This script creates a comprehensive set of test endpoints in your Home Assistant
instance to demonstrate HAAPI's functionality. It uses the Home Assistant REST API
to programmatically configure the integration.

Usage:
    Interactive mode:
        python setup_demo_endpoints.py

    Non-interactive mode:
        python setup_demo_endpoints.py --ha-url http://localhost:8123 --token YOUR_TOKEN --host localhost
"""

import argparse
import sys
import requests
import json
from typing import Optional
from getpass import getpass


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a colored header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")


def print_success(text: str) -> None:
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print an error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print an info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def get_input(prompt: str, default: Optional[str] = None) -> str:
    """Get user input with optional default value"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    value = input(prompt).strip()
    return value if value else (default or "")


def find_haapi_entry(ha_url: str, token: str) -> Optional[str]:
    """Find existing HAAPI Demo config entry (not just any HAAPI entry)"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{ha_url}/api/config/config_entries/entry", headers=headers)
        response.raise_for_status()

        entries = response.json()
        for entry in entries:
            # Only look for entries specifically titled "HAAPI Demo"
            if entry.get("domain") == "haapi" and entry.get("title") == "HAAPI Demo":
                return entry.get("entry_id")

        return None
    except Exception as e:
        print_error(f"Failed to check for existing HAAPI entries: {e}")
        return None


def create_haapi_entry(ha_url: str, token: str) -> Optional[str]:
    """Create initial HAAPI config entry"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print_info("Creating initial HAAPI integration entry...")

    # Start config flow
    try:
        response = requests.post(
            f"{ha_url}/api/config/config_entries/flow",
            headers=headers,
            json={"handler": "haapi"}
        )
        response.raise_for_status()
        flow_data = response.json()
        flow_id = flow_data.get("flow_id")

        if not flow_id:
            print_error("Failed to start config flow")
            return None

        # Complete the initial setup with a name
        response = requests.post(
            f"{ha_url}/api/config/config_entries/flow/{flow_id}",
            headers=headers,
            json={"name": "HAAPI Demo"}
        )
        response.raise_for_status()
        result = response.json()

        if result.get("type") == "create_entry":
            # The response structure has the full entry data in 'result'
            # We need to extract just the entry_id string from it
            if isinstance(result, dict) and "entry_id" in result:
                # Flat structure: {type: "create_entry", entry_id: "...", ...}
                entry_id_value = result["entry_id"]
            elif isinstance(result, dict) and "result" in result:
                # Nested structure: {type: "create_entry", result: {entry_id: "...", ...}}
                entry_data = result["result"]
                if isinstance(entry_data, dict):
                    entry_id_value = entry_data.get("entry_id")
                elif isinstance(entry_data, str):
                    entry_id_value = entry_data
                else:
                    entry_id_value = None
            else:
                entry_id_value = None

            if not entry_id_value or not isinstance(entry_id_value, str):
                print_error(f"Could not extract entry_id string from result: {result}")
                return None

            print_success(f"Created HAAPI entry: {entry_id_value}")
            return entry_id_value
        else:
            print_error(f"Unexpected flow result: {result.get('type')}")
            return None

    except Exception as e:
        print_error(f"Failed to create HAAPI entry: {e}")
        return None


def add_endpoint(ha_url: str, token: str, entry_id: str, endpoint_config: dict) -> bool:
    """Add a single endpoint to HAAPI"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        # Start options flow
        response = requests.post(
            f"{ha_url}/api/config/config_entries/options/flow",
            headers=headers,
            json={"handler": entry_id}
        )
        response.raise_for_status()
        flow_data = response.json()
        flow_id = flow_data.get("flow_id")
        print(f"\n    DEBUG: Started flow {flow_id}")
        print(f"    DEBUG: Flow data: {flow_data}")

        # Select "add_endpoint" from menu
        response = requests.post(
            f"{ha_url}/api/config/config_entries/options/flow/{flow_id}",
            headers=headers,
            json={"next_step_id": "add_endpoint"}
        )
        response.raise_for_status()
        step_data = response.json()
        print(f"    DEBUG: After selecting add_endpoint: {step_data}")

        # Prepare endpoint config (remove auth for now)
        auth_config = endpoint_config.pop("auth", {"auth_type": "none"})

        # Provide endpoint configuration
        print(f"    DEBUG: Sending endpoint config: {endpoint_config}")
        response = requests.post(
            f"{ha_url}/api/config/config_entries/options/flow/{flow_id}",
            headers=headers,
            json=endpoint_config
        )

        # Check response before raising
        if not response.ok:
            error_detail = response.text
            print(f"    DEBUG: Error response: {error_detail}")
            response.raise_for_status()

        auth_step_data = response.json()
        print(f"    DEBUG: After endpoint config: {auth_step_data}")

        # Provide auth configuration
        print(f"    DEBUG: Sending auth config: {auth_config}")
        response = requests.post(
            f"{ha_url}/api/config/config_entries/options/flow/{flow_id}",
            headers=headers,
            json=auth_config
        )

        if not response.ok:
            error_detail = response.text
            print(f"    DEBUG: Error response: {error_detail}")
            response.raise_for_status()

        result = response.json()
        print(f"    DEBUG: Final result: {result}")

        if result.get("type") == "create_entry":
            return True
        else:
            print_error(f"Unexpected result type: {result.get('type')}")
            return False

    except requests.exceptions.HTTPError as e:
        print_error(f"HTTP Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"    Response: {e.response.text}")
        return False
    except Exception as e:
        print_error(f"Failed to add endpoint '{endpoint_config.get('endpoint_name', 'unknown')}': {e}")
        import traceback
        traceback.print_exc()
        return False


def create_demo_endpoints(ha_url: str, token: str, entry_id: str, test_host: str) -> None:
    """Create all demo endpoints"""

    endpoints = [
        {
            "name": "Simple GET Request",
            "config": {
                "endpoint_name": "Echo GET",
                "url": f"http://{test_host}:5000/echo",
                "method": "GET",
                "headers": "",
                "body": "",
                "content_type": "application/json",
                "timeout": 10,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 0,
                "retry_delay": 1,
                "auth": {"auth_type": "none"}
            }
        },
        {
            "name": "POST with JSON Body",
            "config": {
                "endpoint_name": "Echo POST",
                "url": f"http://{test_host}:5000/echo",
                "method": "POST",
                "headers": "Content-Type: application/json",
                "body": '{"message": "Hello from HAAPI!", "timestamp": "{{ now().isoformat() }}"}',
                "content_type": "application/json",
                "timeout": 10,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 0,
                "retry_delay": 1,
                "auth": {"auth_type": "none"}
            }
        },
        {
            "name": "Basic Authentication",
            "config": {
                "endpoint_name": "Basic Auth Test",
                "url": f"http://{test_host}:5001/auth/basic",
                "method": "GET",
                "headers": "",
                "body": "",
                "content_type": "application/json",
                "timeout": 10,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 0,
                "retry_delay": 1,
                "auth": {
                    "auth_type": "basic",
                    "username": "testuser",
                    "password": "testpass"
                }
            }
        },
        {
            "name": "Bearer Token Authentication",
            "config": {
                "endpoint_name": "Bearer Token Test",
                "url": f"http://{test_host}:5001/auth/bearer",
                "method": "GET",
                "headers": "",
                "body": "",
                "content_type": "application/json",
                "timeout": 10,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 0,
                "retry_delay": 1,
                "auth": {
                    "auth_type": "bearer",
                    "bearer_token": "test-bearer-token-12345"
                }
            }
        },
        {
            "name": "API Key Authentication",
            "config": {
                "endpoint_name": "API Key Test",
                "url": f"http://{test_host}:5001/auth/apikey",
                "method": "GET",
                "headers": "",
                "body": "",
                "content_type": "application/json",
                "timeout": 10,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 0,
                "retry_delay": 1,
                "auth": {
                    "auth_type": "api_key",
                    "api_key": "test-api-key-67890"
                }
            }
        },
        {
            "name": "Custom Headers",
            "config": {
                "endpoint_name": "Custom Headers",
                "url": f"http://{test_host}:5000/echo",
                "method": "GET",
                "headers": "X-Custom-Header: CustomValue\nX-Request-ID: {{ now().timestamp() | int }}",
                "body": "",
                "content_type": "application/json",
                "timeout": 10,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 0,
                "retry_delay": 1,
                "auth": {"auth_type": "none"}
            }
        },
        {
            "name": "Retry Configuration",
            "config": {
                "endpoint_name": "Retry Example",
                "url": f"http://{test_host}:5000/echo",
                "method": "GET",
                "headers": "",
                "body": "",
                "content_type": "application/json",
                "timeout": 5,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 3,
                "retry_delay": 2,
                "auth": {"auth_type": "none"}
            }
        },
        {
            "name": "Long Timeout",
            "config": {
                "endpoint_name": "Long Timeout",
                "url": f"http://{test_host}:5000/echo",
                "method": "GET",
                "headers": "",
                "body": "",
                "content_type": "application/json",
                "timeout": 30,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 0,
                "retry_delay": 1,
                "auth": {"auth_type": "none"}
            }
        },
        {
            "name": "Template Example",
            "config": {
                "endpoint_name": "Template Demo",
                "url": f"http://{test_host}:5000/echo?time={{{{ now().strftime('%H:%M:%S') }}}}",
                "method": "POST",
                "headers": "X-Timestamp: {{ now().isoformat() }}",
                "body": '{"current_time": "{{ now().strftime(\'%Y-%m-%d %H:%M:%S\') }}", "unix_timestamp": {{ now().timestamp() | int }}}',
                "content_type": "application/json",
                "timeout": 10,
                "verify_ssl": True,
                "max_response_size": 10240,
                "retries": 0,
                "retry_delay": 1,
                "auth": {"auth_type": "none"}
            }
        }
    ]

    print_header("Creating Demo Endpoints")
    print_info(f"Adding {len(endpoints)} demo endpoints to HAAPI...")

    success_count = 0
    for endpoint in endpoints:
        print(f"\n  Adding: {endpoint['name']}...", end=" ")
        if add_endpoint(ha_url, token, entry_id, endpoint["config"]):
            print_success("Done")
            success_count += 1
        else:
            print_error("Failed")

    print(f"\n{Colors.BOLD}Summary:{Colors.END}")
    print(f"  Successfully created: {Colors.GREEN}{success_count}{Colors.END}/{len(endpoints)} endpoints")

    if success_count == len(endpoints):
        print_success("\n✓ All demo endpoints created successfully!")
    elif success_count > 0:
        print_error(f"\n⚠ Some endpoints failed to create. Check the logs above.")
    else:
        print_error("\n✗ Failed to create any endpoints.")


def main():
    parser = argparse.ArgumentParser(
        description="Setup demo endpoints for HAAPI integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive mode:
    python setup_demo_endpoints.py

  Non-interactive mode:
    python setup_demo_endpoints.py --ha-url http://localhost:8123 \\
                                    --token YOUR_TOKEN \\
                                    --host localhost
        """
    )

    parser.add_argument(
        "--ha-url",
        help="Home Assistant URL (default: http://localhost:8123)"
    )
    parser.add_argument(
        "--token",
        help="Home Assistant long-lived access token"
    )
    parser.add_argument(
        "--host",
        help="Test server host/IP address (default: localhost)"
    )

    args = parser.parse_args()

    # Print banner
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}  HAAPI Demo Endpoints Setup{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}\n")

    # Get configuration (interactive or from args)
    if args.ha_url and args.token and args.host:
        ha_url = args.ha_url.rstrip('/')
        token = args.token
        test_host = args.host
        print_info("Running in non-interactive mode")
    else:
        print_info("Running in interactive mode")
        print("\nThis script will create demo endpoints in your Home Assistant instance.")
        print("You'll need a long-lived access token from HA.")
        print("\nTo create a token:")
        print("  1. Go to your HA profile (bottom left)")
        print("  2. Scroll to 'Long-Lived Access Tokens'")
        print("  3. Click 'Create Token'\n")

        ha_url = get_input("Home Assistant URL", args.ha_url or "http://localhost:8123").rstrip('/')
        token = args.token or getpass("Long-lived access token (hidden): ")
        test_host = get_input("Test server host/IP", args.host or "localhost")

    if not token:
        print_error("Access token is required!")
        sys.exit(1)

    # Verify connection
    print_header("Verifying Connection")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{ha_url}/api/", headers=headers, timeout=5)
        response.raise_for_status()
        print_success(f"Connected to Home Assistant at {ha_url}")
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to connect to Home Assistant: {e}")
        print_info("Please check:")
        print("  - Home Assistant is running")
        print("  - The URL is correct")
        print("  - The access token is valid")
        sys.exit(1)

    # Find or create HAAPI entry
    print_header("Checking HAAPI Integration")
    entry_id = find_haapi_entry(ha_url, token)

    if entry_id:
        print_success(f"Found existing HAAPI entry: {entry_id}")
    else:
        print_info("HAAPI not configured yet, creating initial entry...")
        entry_id = create_haapi_entry(ha_url, token)

        if not entry_id:
            print_error("Failed to create HAAPI integration entry")
            sys.exit(1)

    # Create demo endpoints
    create_demo_endpoints(ha_url, token, entry_id, test_host)

    # Print next steps
    print(f"\n{Colors.BOLD}{Colors.CYAN}Next Steps:{Colors.END}")
    print(f"  1. Start the test servers:")
    print(f"     {Colors.YELLOW}python test_servers/echo_server.py{Colors.END}")
    print(f"     {Colors.YELLOW}python test_servers/auth_server.py{Colors.END}")
    print(f"\n  2. Go to Home Assistant → Settings → Devices & Services → HAAPI")
    print(f"\n  3. Try pressing the trigger buttons for different endpoints!")
    print(f"\n  4. Check the response sensors to see the results\n")


if __name__ == "__main__":
    main()
