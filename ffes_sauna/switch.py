"""Switch platform for FFES Sauna integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FFESSaunaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the FFES Sauna switch platform."""
    coordinator: FFESSaunaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([
        FFESSaunaLightSwitch(coordinator),
        FFESSaunaAuxSwitch(coordinator),
    ])


class FFESSaunaSwitchBase(CoordinatorEntity[FFESSaunaCoordinator], SwitchEntity):
    """Base class for FFES Sauna switches."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FFESSaunaCoordinator, switch_type: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._switch_type = switch_type
        self._attr_unique_id = f"{coordinator.host}_{switch_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": "FFES Sauna",
            "manufacturer": "FFES",
            "model": f"Controller Model {coordinator.data.get('controllerModel', 'Unknown')}",
        }


class FFESSaunaLightSwitch(FFESSaunaSwitchBase):
    """Light switch for FFES Sauna."""

    _attr_name = "Light"
    _attr_icon = "mdi:lightbulb"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the light switch."""
        super().__init__(coordinator, "light")

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self.coordinator.data.get("light", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        success = await self.coordinator.async_send_command("light", "1")
        if success:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        success = await self.coordinator.async_send_command("light", "0")
        if success:
            await self.coordinator.async_request_refresh()


class FFESSaunaAuxSwitch(FFESSaunaSwitchBase):
    """AUX switch for FFES Sauna."""

    _attr_name = "AUX"
    _attr_icon = "mdi:power-socket-eu"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the AUX switch."""
        super().__init__(coordinator, "aux")

    @property
    def is_on(self) -> bool:
        """Return true if the AUX is on."""
        return self.coordinator.data.get("aux", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the AUX on."""
        success = await self.coordinator.async_send_command("aux", "1")
        if success:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the AUX off."""
        success = await self.coordinator.async_send_command("aux", "0")
        if success:
            await self.coordinator.async_request_refresh()