"""Data coordinator for FFES Sauna."""
from __future__ import annotations

import asyncio
import logging
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
        self._session = aiohttp.ClientSession()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from sauna."""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"http://{self.host}/sauna-data") as response:
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
            data = {"action": action, "value": str(value)}

            # Add additional parameters for session start
            if action == "start_session":
                for key, val in kwargs.items():
                    data[key] = str(val)

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"http://{self.host}/sauna-control",
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