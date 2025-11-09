"""Select platform for FFES Sauna integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SAUNA_PROFILES
from .coordinator import FFESSaunaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the FFES Sauna select platform."""
    coordinator: FFESSaunaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([FFESSaunaProfileSelect(coordinator)])


class FFESSaunaProfileSelect(CoordinatorEntity[FFESSaunaCoordinator], SelectEntity):
    """Profile select entity for FFES Sauna."""

    _attr_has_entity_name = True
    _attr_name = "Profile"
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the profile select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_profile"
        self._attr_options = list(SAUNA_PROFILES.values())
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": "FFES Sauna",
            "manufacturer": "FFES",
            "model": f"Controller Model {coordinator.data.get('controllerModel', 'Unknown')}",
        }

    @property
    def current_option(self) -> str | None:
        """Return the current selected profile."""
        profile_id = self.coordinator.data.get("profile")
        if profile_id is not None:
            return SAUNA_PROFILES.get(profile_id)
        return None

    async def async_select_option(self, option: str) -> None:
        """Select a profile option."""
        # Find the profile ID for the selected option
        profile_id = None
        for pid, name in SAUNA_PROFILES.items():
            if name == option:
                profile_id = pid
                break

        if profile_id is None:
            return

        # Get current session parameters or use defaults
        temperature = self.coordinator.data.get("setTemp", 80)
        session_time = self.coordinator.data.get("sessionTime", 60)
        ventilation_time = self.coordinator.data.get("ventilationTime", 15)
        aroma_value = self.coordinator.data.get("aromaValue", 0)
        humidity_value = self.coordinator.data.get("humidityValue", 0)

        # Convert times to HH:MM format
        if session_time >= 100:
            s_hours = session_time // 100
            s_minutes = session_time % 100
        else:
            s_hours = 0
            s_minutes = session_time

        if ventilation_time >= 100:
            v_hours = ventilation_time // 100
            v_minutes = ventilation_time % 100
        else:
            v_hours = 0
            v_minutes = ventilation_time

        session_time_str = f"{s_hours:02d}:{s_minutes:02d}"
        ventilation_time_str = f"{v_hours:02d}:{v_minutes:02d}"

        # Start a new session with the selected profile
        success = await self.coordinator.async_send_command(
            "start_session",
            "",
            profile=profile_id,
            temperature=temperature,
            session_time=session_time_str,
            ventilation_time=ventilation_time_str,
            aroma_value=aroma_value,
            humidity_value=humidity_value,
        )

        if success:
            await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "profile_id": self.coordinator.data.get("profile"),
            "available_profiles": SAUNA_PROFILES,
        }