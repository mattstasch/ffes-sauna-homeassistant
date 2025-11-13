"""Config flow for FFES Sauna integration."""
from __future__ import annotations

import logging
from typing import Any

import asyncio
import socket
import voluptuous as vol
from concurrent.futures import ThreadPoolExecutor
import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

from homeassistant import config_entries
from homeassistant.components import zeroconf
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


def _resolve_host_sync(host: str, timeout: float = 5.0) -> str:
    """Resolve mDNS hostname to IP address synchronously with timeout."""
    if not host.endswith('.local'):
        return host

    original_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        # Try multiple resolution methods for better mDNS support
        try:
            # Method 1: Standard gethostbyname
            return socket.gethostbyname(host)
        except socket.gaierror:
            try:
                # Method 2: getaddrinfo with explicit family
                result = socket.getaddrinfo(host, None, socket.AF_INET)
                if result:
                    return result[0][4][0]
            except (socket.gaierror, IndexError):
                pass

        # If all methods fail, return original host
        _LOGGER.warning("Failed to resolve mDNS hostname %s, using as-is", host)
        return host

    finally:
        socket.setdefaulttimeout(original_timeout)


async def resolve_host(hass: HomeAssistant, host: str) -> str:
    """Resolve mDNS hostname to IP address if needed."""
    if not host.endswith('.local'):
        return host

    try:
        return await hass.async_add_executor_job(_resolve_host_sync, host, 5.0)
    except Exception as err:
        _LOGGER.warning("Error resolving mDNS hostname %s: %s", host, err)
        return host




async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect via Modbus."""
    host = data[CONF_HOST]
    resolved_host = await resolve_host(hass, host)

    # Test Modbus connection to the sauna
    client = AsyncModbusTcpClient(host=resolved_host, port=502, timeout=5)

    try:
        await client.connect()
        if not client.connected:
            raise CannotConnect("Cannot connect to Modbus server")

        # Test reading key registers that should always be available
        # Try CONTROLLER_STATUS register (address 20)
        response = await client.read_holding_registers(20, count=1, device_id=1)

        if isinstance(response, ExceptionResponse):
            raise CannotConnect(f"Modbus Exception: {response}")
        elif hasattr(response, 'isError') and response.isError():
            raise CannotConnect(f"Modbus Error: {response}")

        # Validate we can read at least one register
        if not response.registers:
            raise InvalidData("No data received from sauna")

        controller_status = response.registers[0]

        # Try reading actual temperature (address 2)
        temp_response = await client.read_holding_registers(2, count=1, device_id=1)
        if (not isinstance(temp_response, ExceptionResponse) and
            not (hasattr(temp_response, 'isError') and temp_response.isError())):
            actual_temp = temp_response.registers[0] if temp_response.registers else None
        else:
            actual_temp = None

        _LOGGER.info("FFES Sauna validation successful: Status=%s, Temp=%s",
                    controller_status, actual_temp)

    except ModbusException as err:
        raise CannotConnect(f"Modbus error: {err}")
    except Exception as err:
        raise CannotConnect(f"Unexpected error: {err}")
    finally:
        client.close()

    return {"title": f"FFES Sauna at {host}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FFES Sauna."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_device: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Note: Zeroconf discovery happens automatically when devices broadcast
        # This step is for manual configuration when automatic discovery doesn't work

        return await self.async_step_manual()

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        _LOGGER.debug("Zeroconf discovery: %s", discovery_info)

        # Filter IPv6 addresses - not supported
        if discovery_info.ip_address.version != 4:
            return self.async_abort(reason="ipv6_not_supported")

        hostname = discovery_info.hostname.rstrip(".")
        ip_address = str(discovery_info.ip_address)

        _LOGGER.info("Discovered FFES sauna via zeroconf at %s (%s)", hostname, ip_address)

        # Validate this is actually an FFES sauna by checking Modbus
        client = AsyncModbusTcpClient(host=ip_address, port=502, timeout=3)
        try:
            await client.connect()
            if not client.connected:
                return self.async_abort(reason="cannot_connect")

            # Test reading controller status register
            response = await client.read_holding_registers(20, count=1, device_id=1)
            if isinstance(response, ExceptionResponse) or (hasattr(response, 'isError') and response.isError()):
                return self.async_abort(reason="invalid_data")

            if not response.registers:
                return self.async_abort(reason="invalid_data")

        except Exception as err:
            _LOGGER.debug("Failed to validate discovered device via Modbus: %s", err)
            return self.async_abort(reason="cannot_connect")
        finally:
            client.close()

        # Use IP address as unique ID (more reliable than hostname)
        await self.async_set_unique_id(ip_address)
        self._abort_if_unique_id_configured()

        # Store discovery info for later use
        self._discovered_device = {
            "hostname": hostname,
            "ip_address": ip_address,
            "name": f"FFES Sauna ({hostname})"
        }

        # Set context for UI
        self.context.update({
            "title_placeholders": {"name": hostname},
            "configuration_url": f"http://{ip_address}",
        })

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user confirmation of discovered device."""
        if user_input is None:
            return self.async_show_form(
                step_id="zeroconf_confirm",
                data_schema=vol.Schema({
                    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                        vol.Coerce(int), vol.Range(min=5, max=300)
                    ),
                }),
                description_placeholders={
                    "hostname": self._discovered_device["hostname"],
                    "ip_address": self._discovered_device["ip_address"],
                },
            )

        # Create entry with discovered device info
        data = {
            CONF_HOST: self._discovered_device["ip_address"],  # Use IP address for reliability
            CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
        }

        return self.async_create_entry(
            title=self._discovered_device["name"],
            data=data,
        )


    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual configuration step."""
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
            step_id="manual", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidData(HomeAssistantError):
    """Error to indicate invalid data returned from sauna."""