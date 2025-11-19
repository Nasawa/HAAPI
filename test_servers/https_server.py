"""
HTTPS Echo Server for testing HAAPI SSL verification.

This server runs on HTTPS with a self-signed certificate to test
the verify_ssl configuration option in HAAPI.

Endpoints mirror the echo_server.py but use HTTPS on port 5002.
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)


@app.route(
    "/",
    defaults={"path": ""},
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
@app.route(
    "/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
)
def echo(path):
    """Echo endpoint that returns request details."""

    # Get request body
    body = None
    if request.data:
        try:
            body = request.get_json(force=True)
        except:
            body = request.data.decode("utf-8")

    # Build response
    response_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "method": request.method,
        "path": "/" + path if path else "/",
        "query_params": dict(request.args),
        "headers": dict(request.headers),
        "body": body,
        "remote_addr": request.remote_addr,
        "ssl_enabled": True,
    }

    return jsonify(response_data), 200


@app.route("/status/<int:code>")
def status_code(code):
    """Return a specific HTTP status code."""
    return jsonify({"message": f"Returning status code {code}", "code": code}), code


@app.route("/delay/<int:seconds>")
def delay(seconds):
    """Delay response by specified seconds (max 30)."""
    import time

    delay_time = min(seconds, 30)
    time.sleep(delay_time)
    return jsonify(
        {"message": f"Delayed for {delay_time} seconds", "delay": delay_time}
    ), 200


@app.route("/json")
def json_response():
    """Return a sample JSON response."""
    return jsonify(
        {
            "message": "Hello from HAAPI HTTPS test server!",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {"temperature": 23.5, "humidity": 65, "status": "ok"},
            "ssl_enabled": True,
        }
    )


if __name__ == "__main__":
    print("=" * 60)
    print("HAAPI HTTPS Echo Server")
    print("=" * 60)
    print("\nThis server uses a SELF-SIGNED SSL certificate.")
    print("Use this to test HAAPI's 'verify_ssl' configuration option.")
    print("\nEndpoints:")
    print("  GET/POST/PUT/DELETE/PATCH  https://localhost:5002/")
    print("                             (Echo all request details)")
    print("  GET                        https://localhost:5002/status/<code>")
    print("                             (Return specific status code)")
    print("  GET                        https://localhost:5002/delay/<seconds>")
    print("                             (Delay response)")
    print("  GET                        https://localhost:5002/json")
    print("                             (Return sample JSON)")
    print("\nIMPORTANT:")
    print("  - This server will fail with default HAAPI settings")
    print("  - Set 'Verify SSL Certificate' to FALSE in HAAPI config")
    print("  - You should see a warning in HA logs when SSL verify is disabled")
    print("\nStarting HTTPS server on https://localhost:5002")
    print("=" * 60)
    print()

    # Run with adhoc SSL context (generates self-signed cert on the fly)
    app.run(host="0.0.0.0", port=5002, debug=True, ssl_context="adhoc")
