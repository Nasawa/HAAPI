"""Constants for the HAAPI integration."""

DOMAIN = "haapi"
STORAGE_VERSION = 1
STORAGE_KEY = "haapi_responses"

# Configuration keys
CONF_ENDPOINTS = "endpoints"
CONF_ENDPOINT_ID = "id"
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
CONF_TIMEOUT = "timeout"
CONF_VERIFY_SSL = "verify_ssl"
CONF_MAX_RESPONSE_SIZE = "max_response_size"
CONF_RETRIES = "retries"
CONF_RETRY_DELAY = "retry_delay"

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
DEFAULT_TIMEOUT = 10
DEFAULT_VERIFY_SSL = True
DEFAULT_MAX_RESPONSE_SIZE = 10240  # 10KB (0 = unlimited)
DEFAULT_RETRIES = 0  # No retries by default
DEFAULT_RETRY_DELAY = 1  # 1 second between retries

# Entity types
SENSOR_REQUEST = "request"
SENSOR_RESPONSE = "response"

# Attributes
ATTR_RESPONSE_BODY = "response_body"
ATTR_RESPONSE_HEADERS = "response_headers"
ATTR_REQUEST_HEADERS = "request_headers"
ATTR_REQUEST_BODY = "request_body"
ATTR_URL = "url"
ATTR_METHOD = "method"
ATTR_CONTENT_TYPE = "content_type"
ATTR_TIMEOUT = "timeout"
ATTR_VERIFY_SSL = "verify_ssl"
ATTR_MAX_RESPONSE_SIZE = "max_response_size"
ATTR_TRUNCATED = "truncated"
ATTR_RETRIES = "retries"
ATTR_RETRY_DELAY = "retry_delay"
