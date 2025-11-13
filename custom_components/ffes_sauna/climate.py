"""Climate platform for FFES Sauna integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SAUNA_STATUS_MAP, SAUNA_PROFILES
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
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_min_temp = 20
    _attr_max_temp = 110
    _attr_preset_modes = [PRESET_NONE] + list(SAUNA_PROFILES.values())

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

    @property
    def preset_mode(self) -> str:
        """Return current preset mode."""
        profile = self.coordinator.data.get("profile")
        if profile and profile in SAUNA_PROFILES:
            return SAUNA_PROFILES[profile]
        return PRESET_NONE

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

        success = await self.coordinator.async_send_command("set_controller_status", status_value)
        if success:
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the sauna on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Turn the sauna off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # Try simple temperature command first
        success = await self.coordinator.async_send_command("set_temp", int(temperature))
        if success:
            await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode (sauna profile)."""
        if preset_mode == PRESET_NONE:
            return

        # Find profile number for the given preset name
        profile_id = None
        for pid, pname in SAUNA_PROFILES.items():
            if pname == preset_mode:
                profile_id = pid
                break

        if profile_id is None:
            return

        success = await self.coordinator.async_send_command("set_profile", profile_id)
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