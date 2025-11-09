"""Data coordinator for FFES Sauna."""
from __future__ import annotations

import asyncio
import logging
import socket
from datetime import timedelta
from typing import Any

import aiohttp

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
        self._session = aiohttp.ClientSession()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    def _resolve_host_sync(self, host: str, timeout: float = 5.0) -> str:
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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from sauna."""
        try:
            resolved_host = await self._get_resolved_host()
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"http://{resolved_host}/sauna-data") as response:
                    if response.status != 200:
                        raise UpdateFailed(f"HTTP {response.status}")

                    data = await response.json()
                    _LOGGER.debug("Sauna data: %s", data)
                    return data

        except asyncio.TimeoutError as err:
            raise UpdateFailed("Connection timeout") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_send_command(self, action: str, value: str | int, **kwargs) -> bool:
        """Send command to sauna."""
        try:
            resolved_host = await self._get_resolved_host()
            data = {"action": action, "value": str(value)}

            # Add additional parameters for session start
            if action == "start_session":
                for key, val in kwargs.items():
                    data[key] = str(val)

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"http://{resolved_host}/sauna-control",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as response:
                    if response.status != 200:
                        _LOGGER.error("Command failed with HTTP %s", response.status)
                        return False

                    result = await response.json()
                    success = result.get("success", False)

                    if not success:
                        _LOGGER.error("Command failed: %s", result.get("message", "Unknown error"))

                    return success

        except Exception as err:
            _LOGGER.error("Error sending command: %s", err)
            return False

    async def async_close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()