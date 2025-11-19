"""The HAAPI integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import template
from homeassistant.exceptions import TemplateError
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
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
    AUTH_BASIC,
    AUTH_BEARER,
    AUTH_API_KEY,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAAPI from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API caller instance
    api_caller = HaapiApiCaller(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = api_caller

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HaapiApiCaller:
    """Class to handle API calls and store responses."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the API caller."""
        self.hass = hass
        self.entry = entry
        self._last_response_code: int | None = None
        self._last_fetch_time: datetime | None = None
        self._last_response_body: str | None = None
        self._last_response_headers: dict[str, str] | None = None
        self._listeners: list = []

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
        auth_type = self.entry.data.get(CONF_AUTH_TYPE)

        if auth_type == AUTH_BEARER:
            token = self.entry.data.get(CONF_BEARER_TOKEN)
            if token:
                rendered_token = self._render_template(token)
                headers["Authorization"] = f"Bearer {rendered_token}"

        elif auth_type == AUTH_API_KEY:
            api_key = self.entry.data.get(CONF_API_KEY)
            if api_key:
                rendered_key = self._render_template(api_key)
                headers["X-API-Key"] = rendered_key

        return headers

    async def async_call_api(self) -> None:
        """Execute the API call."""
        url = self._render_template(self.entry.data[CONF_URL])
        method = self.entry.data[CONF_METHOD]
        headers = self._parse_headers(self.entry.data.get(CONF_HEADERS, ""))
        body = self._render_template(self.entry.data.get(CONF_BODY, ""))
        content_type = self.entry.data.get(CONF_CONTENT_TYPE)

        # Add authentication headers
        headers.update(self._get_auth_headers())

        # Add content type if body is present
        if body and content_type:
            headers["Content-Type"] = content_type

        # Prepare auth for basic auth
        auth = None
        if self.entry.data.get(CONF_AUTH_TYPE) == AUTH_BASIC:
            username = self.entry.data.get(CONF_USERNAME)
            password = self.entry.data.get(CONF_PASSWORD)
            if username and password:
                rendered_username = self._render_template(username)
                rendered_password = self._render_template(password)
                auth = aiohttp.BasicAuth(rendered_username, rendered_password)
                _LOGGER.debug("Using Basic Auth with username: %s", rendered_username)
            else:
                _LOGGER.warning(
                    "Basic Auth selected but username or password is missing"
                )

        _LOGGER.debug("Calling API: %s %s", method, url)

        try:
            async with async_timeout.timeout(30):
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=headers if headers else None,
                        data=body if body else None,
                        auth=auth,
                    ) as response:
                        self._last_response_code = response.status
                        self._last_fetch_time = dt_util.utcnow()
                        self._last_response_body = await response.text()
                        self._last_response_headers = dict(response.headers)

                        _LOGGER.info(
                            "API call completed: %s (status: %d)",
                            url,
                            response.status,
                        )

        except aiohttp.ClientError as err:
            _LOGGER.error("Error calling API %s: %s", url, err)
            self._last_response_code = 0
            self._last_fetch_time = dt_util.utcnow()
            self._last_response_body = str(err)
            self._last_response_headers = {}

        except Exception as err:
            _LOGGER.error("Unexpected error calling API %s: %s", url, err)
            self._last_response_code = 0
            self._last_fetch_time = dt_util.utcnow()
            self._last_response_body = str(err)
            self._last_response_headers = {}

        # Notify all entities of the update
        self._notify_listeners()
