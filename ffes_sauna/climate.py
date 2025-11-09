"""Climate platform for FFES Sauna integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SAUNA_STATUS_MAP
from .coordinator import FFESSaunaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the FFES Sauna climate platform."""
    coordinator: FFESSaunaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([FFESSaunaClimate(coordinator)])


class FFESSaunaClimate(CoordinatorEntity[FFESSaunaCoordinator], ClimateEntity):
    """FFES Sauna climate entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.AUTO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )
    _attr_min_temp = 20
    _attr_max_temp = 110

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": "FFES Sauna",
            "manufacturer": "FFES",
            "model": f"Controller Model {coordinator.data.get('controllerModel', 'Unknown')}",
        }

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator.data.get("actualTemp")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self.coordinator.data.get("setTemp")

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self.coordinator.data.get("humidity")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current hvac mode."""
        status = self.coordinator.data.get("controllerStatus", 0)
        status_str = SAUNA_STATUS_MAP.get(status, "off")

        if status_str == "off":
            return HVACMode.OFF
        elif status_str == "heat":
            return HVACMode.HEAT
        elif status_str == "fan_only":
            return HVACMode.FAN_ONLY
        else:  # auto/standby
            return HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction:
        """Return current hvac action."""
        status = self.coordinator.data.get("controllerStatus", 0)
        status_str = SAUNA_STATUS_MAP.get(status, "off")

        if status_str == "off":
            return HVACAction.OFF
        elif status_str == "heat":
            return HVACAction.HEATING
        elif status_str == "fan_only":
            return HVACAction.FAN
        else:  # auto/standby
            return HVACAction.IDLE

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            status_value = 0
        elif hvac_mode == HVACMode.HEAT:
            status_value = 1
        elif hvac_mode == HVACMode.FAN_ONLY:
            status_value = 2
        else:  # AUTO
            status_value = 3

        success = await self.coordinator.async_send_command("status", status_value)
        if success:
            await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # For temperature changes, we need to start a session with current settings
        profile = self.coordinator.data.get("profile", 2)  # Default to Dry Sauna
        session_time = self.coordinator.data.get("sessionTime", 60)  # Default 1 hour
        ventilation_time = self.coordinator.data.get("ventilationTime", 15)  # Default 15 min
        aroma_value = self.coordinator.data.get("aromaValue", 0)
        humidity_value = self.coordinator.data.get("humidityValue", 0)

        # Convert session time from HHMM format to HH:MM string
        hours = session_time // 100 if session_time > 100 else 0
        minutes = session_time % 100 if session_time > 100 else session_time
        session_time_str = f"{hours:02d}:{minutes:02d}"

        # Convert ventilation time
        v_hours = ventilation_time // 100 if ventilation_time > 100 else 0
        v_minutes = ventilation_time % 100 if ventilation_time > 100 else ventilation_time
        ventilation_time_str = f"{v_hours:02d}:{v_minutes:02d}"

        success = await self.coordinator.async_send_command(
            "start_session",
            "",  # No direct value for start_session
            profile=profile,
            temperature=int(temperature),
            session_time=session_time_str,
            ventilation_time=ventilation_time_str,
            aroma_value=aroma_value,
            humidity_value=humidity_value,
        )

        if success:
            await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        data = self.coordinator.data
        return {
            "controller_model": data.get("controllerModel"),
            "profile": data.get("profile"),
            "session_time": data.get("sessionTime"),
            "ventilation_time": data.get("ventilationTime"),
            "aroma_value": data.get("aromaValue"),
            "humidity_value": data.get("humidityValue"),
        }