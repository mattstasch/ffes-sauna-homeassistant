"""Config flow for FFES Sauna integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import asyncio
import socket
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_HOST, DEFAULT_SCAN_INTERVAL, DOMAIN, CONF_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=300)
        ),
    }
)


async def resolve_host(host: str) -> str:
    """Resolve mDNS hostname to IP address if needed."""
    if host.endswith('.local'):
        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            # If mDNS resolution fails, try the original host
            return host
    return host


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    resolved_host = await hass.async_add_executor_job(resolve_host, host)

    # Test connection to the sauna
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(f"http://{resolved_host}/sauna-data") as response:
                if response.status != 200:
                    raise CannotConnect(f"HTTP {response.status}")

                data = await response.json()

                # Validate we got expected sauna data structure
                if "controllerStatus" not in data or "actualTemp" not in data:
                    raise InvalidData("Response missing required fields")

        except asyncio.TimeoutError:
            raise CannotConnect("Connection timeout")
        except aiohttp.ClientError as err:
            raise CannotConnect(f"Connection error: {err}")
        except Exception as err:
            raise CannotConnect(f"Unexpected error: {err}")

    return {"title": f"FFES Sauna at {host}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FFES Sauna."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidData:
                errors["base"] = "invalid_data"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidData(HomeAssistantError):
    """Error to indicate invalid data returned from sauna."""