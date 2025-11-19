"""
Simple Echo Server for testing HAAPI integration.

This server accepts all HTTP methods (GET, POST, PUT, DELETE, PATCH)
and echoes back the request details including headers and body content.
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
            "message": "Hello from HAAPI test server!",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {"temperature": 23.5, "humidity": 65, "status": "ok"},
        }
    )


if __name__ == "__main__":
    print("=" * 60)
    print("HAAPI Echo Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  GET/POST/PUT/DELETE/PATCH  http://localhost:5000/")
    print("                             (Echo all request details)")
    print("  GET                        http://localhost:5000/status/<code>")
    print("                             (Return specific status code)")
    print("  GET                        http://localhost:5000/delay/<seconds>")
    print("                             (Delay response)")
    print("  GET                        http://localhost:5000/json")
    print("                             (Return sample JSON)")
    print("\nStarting server on http://localhost:5000")
    print("=" * 60)
    print()

    app.run(host="0.0.0.0", port=5000, debug=True)
