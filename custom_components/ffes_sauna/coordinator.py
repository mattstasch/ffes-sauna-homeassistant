"""Data coordinator for FFES Sauna."""
from __future__ import annotations

import asyncio
import logging
import socket
from datetime import timedelta
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, CONF_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class FFESSaunaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Data coordinator for FFES Sauna."""

    def __init__(self, hass: HomeAssistant, host: str, scan_interval: int = DEFAULT_SCAN_INTERVAL) -> None:
        """Initialize coordinator."""
        self.host = host
        self._resolved_host = None
        self._modbus_client = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    def _resolve_host_sync(self, host: str, timeout: float = 5.0) -> str:
        """Resolve mDNS hostname to IP address synchronously with timeout."""
        # If it's already an IP address, return as-is
        try:
            socket.inet_aton(host)
            return host  # Valid IPv4 address
        except socket.error:
            pass

        # If it's not a .local hostname, return as-is
        if not host.endswith('.local'):
            return host

        original_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            # Try multiple resolution methods for better mDNS support
            try:
                # Method 1: Standard gethostbyname
                resolved = socket.gethostbyname(host)
                _LOGGER.debug("Resolved %s to %s via gethostbyname", host, resolved)
                return resolved
            except socket.gaierror:
                try:
                    # Method 2: getaddrinfo with explicit family
                    result = socket.getaddrinfo(host, None, socket.AF_INET)
                    if result:
                        resolved = result[0][4][0]
                        _LOGGER.debug("Resolved %s to %s via getaddrinfo", host, resolved)
                        return resolved
                except (socket.gaierror, IndexError):
                    pass

            # If all methods fail, return original host
            _LOGGER.warning("Failed to resolve mDNS hostname %s, using as-is", host)
            return host

        finally:
            socket.setdefaulttimeout(original_timeout)

    async def _get_resolved_host(self) -> str:
        """Get resolved host, caching the result."""
        if self._resolved_host is None:
            try:
                self._resolved_host = await self.hass.async_add_executor_job(
                    self._resolve_host_sync, self.host, 5.0
                )
            except Exception as err:
                _LOGGER.warning("Error resolving mDNS hostname %s: %s", self.host, err)
                self._resolved_host = self.host
        return self._resolved_host

    async def _get_modbus_client(self) -> AsyncModbusTcpClient:
        """Get Modbus client, creating if needed."""
        if self._modbus_client is None:
            resolved_host = await self._get_resolved_host()
            self._modbus_client = AsyncModbusTcpClient(host=resolved_host, port=502, timeout=5)

        if not self._modbus_client.connected:
            await self._modbus_client.connect()

        return self._modbus_client

    async def _read_holding_register(self, client: AsyncModbusTcpClient, address: int, count: int = 1) -> Any:
        """Read holding register with fallback for different pymodbus versions."""
        try:
            return await client.read_holding_registers(address, count=count)
        except TypeError:
            return await client.read_holding_registers(address, count, unit=1)

    async def _write_register(self, client: AsyncModbusTcpClient, address: int, value: int) -> Any:
        """Write register with fallback for different pymodbus versions."""
        try:
            return await client.write_register(address, value)
        except TypeError:
            return await client.write_register(address, value, unit=1)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from sauna via Modbus."""
        try:
            client = await self._get_modbus_client()

            # Read key registers based on our successful tests
            # Unit ID = 1, Function Code = 3 (Holding Registers), 0-based addressing
            register_map = {
                1: "setTemp",                # TEMPERATURE_SET_VALUE
                2: "actualTemp",             # TEMP1_ACTUAL_VALUE
                4: "profile",                # SAUNA_PROFILE
                20: "controllerStatus",      # CONTROLLER_STATUS
                # Try additional registers that might be available
                5: "sessionTime",            # SESSION_TIME
                6: "ventilationTime",        # VENTILATION_TIME
                9: "aromaValue",             # AROMA_SET_VALUE
                10: "humidityValue",         # VAPORIZER_HUMIDITY_SET_VALUE
                11: "errorCode",             # ERROR_CODE
                15: "humidity",              # HUMIDITY_ACTUAL_VALUE
            }

            data = {}

            for reg_addr, key in register_map.items():
                try:
                    response = await self._read_holding_register(client, reg_addr, 1)
                    if (not isinstance(response, ExceptionResponse) and
                        not (hasattr(response, 'isError') and response.isError())):
                        value = response.registers[0] if response.registers else 0
                        data[key] = value
                        _LOGGER.debug("Register %d (%s): %s", reg_addr, key, value)
                    else:
                        _LOGGER.debug("Register %d (%s) failed: %s", reg_addr, key, response)
                except Exception as reg_err:
                    _LOGGER.debug("Register %d (%s) error: %s", reg_addr, key, reg_err)

            # Ensure we have minimum required data
            if 'controllerStatus' not in data or 'actualTemp' not in data:
                raise UpdateFailed("Missing required sauna data")

            # Add computed fields for compatibility with existing entities
            data['light'] = False  # Not available via Modbus
            data['aux'] = False    # Not available via Modbus
            data['controllerModel'] = 2  # Default value

            _LOGGER.debug("Sauna Modbus data: %s", data)
            return data

        except ModbusException as err:
            raise UpdateFailed(f"Modbus error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_send_command(self, action: str, value: str | int, **kwargs) -> bool:
        """Send command to sauna via Modbus."""
        try:
            client = await self._get_modbus_client()

            # Map HTTP actions to Modbus register writes
            if action == "set_temp":
                # Write to TEMPERATURE_SET_VALUE register (address 1)
                response = await self._write_register(client, 1, int(value))
            elif action == "set_profile":
                # Write to SAUNA_PROFILE register (address 4)
                response = await self._write_register(client, 4, int(value))
            elif action == "start_session":
                # Set multiple registers for session start
                # First set session time (address 5)
                session_time = kwargs.get("time", 1800)  # Default 30 minutes
                await self._write_register(client, 5, int(session_time))

                # Set profile if provided
                profile = kwargs.get("profile", 2)
                await self._write_register(client, 4, int(profile))

                # Set temperature
                await self._write_register(client, 1, int(value))

                # Set aroma if provided
                aroma = kwargs.get("aroma", 0)
                await self._write_register(client, 9, int(aroma))

                # Set humidity if provided
                humidity = kwargs.get("humidity", 0)
                await self._write_register(client, 10, int(humidity))

                # Start session by setting controller status to HEAT (1)
                response = await self._write_register(client, 20, 1)

            elif action == "stop_session":
                # Stop session by setting controller status to OFF (0)
                response = await self._write_register(client, 20, 0)
            elif action == "set_controller_status":
                # Directly set controller status
                response = await self._write_register(client, 20, int(value))
            else:
                _LOGGER.error("Unknown action: %s", action)
                return False

            # Check response
            if isinstance(response, ExceptionResponse):
                _LOGGER.error("Modbus command failed: %s", response)
                return False
            elif hasattr(response, 'isError') and response.isError():
                _LOGGER.error("Modbus command error: %s", response)
                return False

            _LOGGER.debug("Modbus command successful: %s = %s", action, value)
            return True

        except Exception as err:
            _LOGGER.error("Error sending Modbus command: %s", err)
            return False

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        if self._modbus_client:
            self._modbus_client.close()