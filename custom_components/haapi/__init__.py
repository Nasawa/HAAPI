"""The HAAPI integration."""

from __future__ import annotations

import asyncio
import logging
import ssl
from datetime import datetime
from typing import Any

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import template
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import TemplateError
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    STORAGE_VERSION,
    STORAGE_KEY,
    CONF_ENDPOINTS,
    CONF_ENDPOINT_ID,
    CONF_ENDPOINT_NAME,
    CONF_URL,
    CONF_METHOD,
    CONF_HEADERS,
    CONF_BODY,
    CONF_CONTENT_TYPE,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_BEARER_TOKEN,
    CONF_API_KEY,
    CONF_AUTH_TYPE,
    CONF_TIMEOUT,
    CONF_VERIFY_SSL,
    CONF_MAX_RESPONSE_SIZE,
    CONF_RETRIES,
    CONF_RETRY_DELAY,
    AUTH_BASIC,
    AUTH_BEARER,
    AUTH_API_KEY,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    DEFAULT_MAX_RESPONSE_SIZE,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAAPI from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create storage for persistent response data
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
    stored_data = await store.async_load() or {}

    # Create coordinator for this integration entry
    coordinator = HaapiCoordinator(hass, entry, store, stored_data)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


class HaapiCoordinator:
    """Coordinator to manage multiple endpoint API callers."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: Store,
        stored_data: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.store = store
        self._api_callers: dict[str, HaapiApiCaller] = {}

        # Create API caller for each endpoint
        endpoints = entry.options.get(CONF_ENDPOINTS, entry.data.get(CONF_ENDPOINTS, []))
        for endpoint_config in endpoints:
            endpoint_id = endpoint_config[CONF_ENDPOINT_ID]
            endpoint_data = stored_data.get(endpoint_id, {})
            api_caller = HaapiApiCaller(hass, endpoint_config, endpoint_data, self._save_data)
            self._api_callers[endpoint_id] = api_caller

    def get_api_caller(self, endpoint_id: str) -> HaapiApiCaller | None:
        """Get API caller for a specific endpoint."""
        return self._api_callers.get(endpoint_id)

    def get_all_endpoints(self) -> list[dict[str, Any]]:
        """Get all endpoint configurations."""
        return self.entry.options.get(CONF_ENDPOINTS, self.entry.data.get(CONF_ENDPOINTS, []))

    async def _save_data(self) -> None:
        """Save all endpoint response data to storage."""
        data_to_save = {}
        for endpoint_id, api_caller in self._api_callers.items():
            data_to_save[endpoint_id] = {
                "last_response_code": api_caller.last_response_code,
                "last_response_body": api_caller.last_response_body,
                "last_response_headers": api_caller.last_response_headers,
                "last_fetch_time": api_caller.last_fetch_time.isoformat() if api_caller.last_fetch_time else None,
                "truncated": api_caller.truncated,
            }
        await self.store.async_save(data_to_save)


class HaapiApiCaller:
    """Class to handle API calls and store responses for a single endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        endpoint_config: dict[str, Any],
        stored_data: dict[str, Any],
        save_callback,
    ) -> None:
        """Initialize the API caller."""
        self.hass = hass
        self.endpoint_config = endpoint_config
        self._save_callback = save_callback

        # Restore from stored data or initialize
        self._last_response_code: int | None = stored_data.get("last_response_code")
        self._last_response_body: str | None = stored_data.get("last_response_body")
        self._last_response_headers: dict[str, str] | None = stored_data.get("last_response_headers")
        self._truncated: bool = stored_data.get("truncated", False)

        # Parse datetime if available
        last_fetch_str = stored_data.get("last_fetch_time")
        self._last_fetch_time: datetime | None = (
            dt_util.parse_datetime(last_fetch_str) if last_fetch_str else None
        )

        self._listeners: list = []

    @property
    def endpoint_id(self) -> str:
        """Return the endpoint ID."""
        return self.endpoint_config[CONF_ENDPOINT_ID]

    @property
    def endpoint_name(self) -> str:
        """Return the endpoint name."""
        return self.endpoint_config[CONF_ENDPOINT_NAME]

    @property
    def last_response_code(self) -> int | None:
        """Return the last response code."""
        return self._last_response_code

    @property
    def last_fetch_time(self) -> datetime | None:
        """Return the last fetch time."""
        return self._last_fetch_time

    @property
    def last_response_body(self) -> str | None:
        """Return the last response body."""
        return self._last_response_body

    @property
    def last_response_headers(self) -> dict[str, str] | None:
        """Return the last response headers."""
        return self._last_response_headers

    @property
    def truncated(self) -> bool:
        """Return whether the last response was truncated."""
        return self._truncated

    def add_listener(self, listener) -> None:
        """Add a listener for updates."""
        self._listeners.append(listener)

    def _notify_listeners(self) -> None:
        """Notify all listeners of updates."""
        for listener in self._listeners:
            listener()

    def _render_template(self, template_str: str) -> str:
        """Render a Jinja2 template."""
        if not template_str:
            return ""

        try:
            tpl = template.Template(template_str, self.hass)
            return tpl.async_render()
        except TemplateError as err:
            _LOGGER.error("Error rendering template: %s", err)
            return template_str

    def _parse_headers(self, headers_str: str) -> dict[str, str]:
        """Parse headers from string format."""
        headers = {}
        if not headers_str:
            return headers

        # Render template first
        rendered = self._render_template(headers_str)

        # Parse headers (format: "Key1: Value1\nKey2: Value2")
        for line in rendered.split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        return headers

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers based on auth type."""
        headers = {}
        auth_type = self.endpoint_config.get(CONF_AUTH_TYPE)

        if auth_type == AUTH_BEARER:
            token = self.endpoint_config.get(CONF_BEARER_TOKEN)
            if token:
                rendered_token = self._render_template(token)
                headers["Authorization"] = f"Bearer {rendered_token}"

        elif auth_type == AUTH_API_KEY:
            api_key = self.endpoint_config.get(CONF_API_KEY)
            if api_key:
                rendered_key = self._render_template(api_key)
                headers["X-API-Key"] = rendered_key

        return headers

    async def async_call_api(self) -> None:
        """Execute the API call."""
        url = self._render_template(self.endpoint_config[CONF_URL])
        method = self.endpoint_config[CONF_METHOD]
        headers = self._parse_headers(self.endpoint_config.get(CONF_HEADERS, ""))
        body = self._render_template(self.endpoint_config.get(CONF_BODY, ""))
        content_type = self.endpoint_config.get(CONF_CONTENT_TYPE)

        # Add authentication headers
        headers.update(self._get_auth_headers())

        # Add content type if body is present
        if body and content_type:
            headers["Content-Type"] = content_type

        # Prepare auth for basic auth
        auth = None
        if self.endpoint_config.get(CONF_AUTH_TYPE) == AUTH_BASIC:
            username = self.endpoint_config.get(CONF_USERNAME)
            password = self.endpoint_config.get(CONF_PASSWORD)
            if username and password:
                rendered_username = self._render_template(username)
                rendered_password = self._render_template(password)
                auth = aiohttp.BasicAuth(rendered_username, rendered_password)
                _LOGGER.debug("Using Basic Auth with username: %s", rendered_username)
            else:
                _LOGGER.warning(
                    "Basic Auth selected but username or password is missing"
                )

        # Get timeout from config
        timeout = self.endpoint_config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        # Get SSL verification setting
        verify_ssl = self.endpoint_config.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

        # Get retry configuration
        retries = self.endpoint_config.get(CONF_RETRIES, DEFAULT_RETRIES)
        retry_delay = self.endpoint_config.get(CONF_RETRY_DELAY, DEFAULT_RETRY_DELAY)

        # Create SSL context
        ssl_context = None
        if not verify_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            _LOGGER.warning(
                "SSL verification disabled for %s - use with caution!",
                url
            )

        _LOGGER.debug(
            "Calling API: %s %s (timeout: %ss, SSL verify: %s, retries: %d)",
            method, url, timeout, verify_ssl, retries
        )

        # Retry loop
        last_exception = None
        for attempt in range(retries + 1):
            if attempt > 0:
                _LOGGER.info(
                    "Retry attempt %d/%d for %s after %ds delay",
                    attempt, retries, self.endpoint_name, retry_delay
                )
                await asyncio.sleep(retry_delay)

            try:
                async with async_timeout.timeout(timeout):
                    connector = aiohttp.TCPConnector(ssl=ssl_context if ssl_context else True)
                    async with aiohttp.ClientSession(connector=connector) as session:
                        async with session.request(
                            method=method,
                            url=url,
                            headers=headers if headers else None,
                            data=body if body else None,
                            auth=auth,
                        ) as response:
                            self._last_response_code = response.status
                            self._last_fetch_time = dt_util.utcnow()
                            response_body = await response.text()
                            self._last_response_headers = dict(response.headers)

                            # Check if response needs truncation
                            max_size = self.endpoint_config.get(CONF_MAX_RESPONSE_SIZE, DEFAULT_MAX_RESPONSE_SIZE)
                            original_size = len(response_body)

                            if max_size > 0 and original_size > max_size:
                                # Truncate and add explicit message in response
                                truncate_message = f"\n\n[TRUNCATED: Response size {original_size:,} bytes exceeds limit of {max_size:,} bytes. {original_size - max_size:,} bytes removed.]"
                                available_space = max_size - len(truncate_message)
                                if available_space > 0:
                                    self._last_response_body = response_body[:available_space] + truncate_message
                                else:
                                    # If message won't fit, just truncate at max_size
                                    self._last_response_body = response_body[:max_size]
                                self._truncated = True
                                _LOGGER.warning(
                                    "Response body truncated for %s: %d bytes -> %d bytes (limit: %d bytes)",
                                    self.endpoint_name, original_size, len(self._last_response_body), max_size
                                )
                            else:
                                self._last_response_body = response_body
                                self._truncated = False

                            _LOGGER.info(
                                "API call completed: %s (status: %d)",
                                url,
                                response.status,
                            )

                            # Don't retry on client errors (4xx) or successful responses
                            if response.status < 500:
                                break

                            # Server error - retry if we have attempts left
                            if attempt < retries:
                                _LOGGER.warning(
                                    "Server error %d for %s, will retry",
                                    response.status, self.endpoint_name
                                )
                                continue
                            else:
                                # Last attempt with server error
                                break

            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                last_exception = err
                _LOGGER.warning(
                    "Error calling API %s (attempt %d/%d): %s",
                    url, attempt + 1, retries + 1, err
                )

                # If this is the last attempt, set error response
                if attempt >= retries:
                    _LOGGER.error("All retry attempts failed for %s: %s", url, err)
                    self._last_response_code = 0
                    self._last_fetch_time = dt_util.utcnow()
                    self._last_response_body = str(err)
                    self._last_response_headers = {}
                    self._truncated = False
                # Otherwise continue to next retry
                continue

            except Exception as err:
                # Don't retry on unexpected errors
                _LOGGER.error("Unexpected error calling API %s: %s", url, err)
                self._last_response_code = 0
                self._last_fetch_time = dt_util.utcnow()
                self._last_response_body = str(err)
                self._last_response_headers = {}
                self._truncated = False
                break

        # Save response data to storage
        await self._save_callback()

        # Notify all entities of the update
        self._notify_listeners()
