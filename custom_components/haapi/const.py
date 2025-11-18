"""Constants for the HAAPI integration."""

DOMAIN = "haapi"

# Configuration keys
CONF_ENDPOINT_NAME = "endpoint_name"
CONF_URL = "url"
CONF_METHOD = "method"
CONF_HEADERS = "headers"
CONF_BODY = "body"
CONF_CONTENT_TYPE = "content_type"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_BEARER_TOKEN = "bearer_token"
CONF_API_KEY = "api_key"
CONF_AUTH_TYPE = "auth_type"

# HTTP Methods
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]

# Auth types
AUTH_NONE = "none"
AUTH_BASIC = "basic"
AUTH_BEARER = "bearer"
AUTH_API_KEY = "api_key"
AUTH_TYPES = [AUTH_NONE, AUTH_BASIC, AUTH_BEARER, AUTH_API_KEY]

# Default values
DEFAULT_METHOD = "GET"
DEFAULT_CONTENT_TYPE = "application/json"
DEFAULT_AUTH_TYPE = AUTH_NONE

# Entity types
SENSOR_RESPONSE_CODE = "response_code"
SENSOR_FETCH_TIME = "fetch_time"
SENSOR_RESPONSE_BODY = "response_body"

# Attributes
ATTR_RESPONSE_BODY = "response_body"
ATTR_RESPONSE_HEADERS = "response_headers"
ATTR_REQUEST_HEADERS = "request_headers"
ATTR_REQUEST_BODY = "request_body"
ATTR_URL = "url"
ATTR_METHOD = "method"
