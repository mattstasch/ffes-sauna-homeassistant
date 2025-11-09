"""Sensor platform for FFES Sauna integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
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
    """Set up the FFES Sauna sensor platform."""
    coordinator: FFESSaunaCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([
        FFESSaunaTemperatureSensor(coordinator),
        FFESSaunaHumiditySensor(coordinator),
        FFESSaunaStatusSensor(coordinator),
        FFESSaunaProfileSensor(coordinator),
        FFESSaunaSessionTimeSensor(coordinator),
        FFESSaunaVentilationTimeSensor(coordinator),
        FFESSaunaAromaSensor(coordinator),
        FFESSaunaHumidityValueSensor(coordinator),
    ])


class FFESSaunaSensorBase(CoordinatorEntity[FFESSaunaCoordinator], SensorEntity):
    """Base class for FFES Sauna sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FFESSaunaCoordinator, sensor_type: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{coordinator.host}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": "FFES Sauna",
            "manufacturer": "FFES",
            "model": f"Controller Model {coordinator.data.get('controllerModel', 'Unknown')}",
        }


class FFESSaunaTemperatureSensor(FFESSaunaSensorBase):
    """Temperature sensor for FFES Sauna."""

    _attr_name = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, "temperature")

    @property
    def native_value(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator.data.get("actualTemp")


class FFESSaunaHumiditySensor(FFESSaunaSensorBase):
    """Humidity sensor for FFES Sauna."""

    _attr_name = "Humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:water-percent"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the humidity sensor."""
        super().__init__(coordinator, "humidity")

    @property
    def native_value(self) -> int | None:
        """Return the current humidity."""
        return self.coordinator.data.get("humidity")


class FFESSaunaStatusSensor(FFESSaunaSensorBase):
    """Status sensor for FFES Sauna."""

    _attr_name = "Status"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the status sensor."""
        super().__init__(coordinator, "status")

    @property
    def native_value(self) -> str:
        """Return the current status."""
        status = self.coordinator.data.get("controllerStatus", 0)
        return SAUNA_STATUS_MAP.get(status, "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Return additional state attributes."""
        return {
            "controller_status_code": self.coordinator.data.get("controllerStatus", 0)
        }


class FFESSaunaProfileSensor(FFESSaunaSensorBase):
    """Profile sensor for FFES Sauna."""

    _attr_name = "Profile"
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the profile sensor."""
        super().__init__(coordinator, "profile")

    @property
    def native_value(self) -> str | None:
        """Return the current profile."""
        profile = self.coordinator.data.get("profile")
        if profile is not None:
            return SAUNA_PROFILES.get(profile, f"Unknown ({profile})")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Return additional state attributes."""
        return {
            "profile_id": self.coordinator.data.get("profile")
        }


class FFESSaunaSessionTimeSensor(FFESSaunaSensorBase):
    """Session time sensor for FFES Sauna."""

    _attr_name = "Session Time"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the session time sensor."""
        super().__init__(coordinator, "session_time")

    @property
    def native_value(self) -> int | None:
        """Return the session time in minutes."""
        session_time = self.coordinator.data.get("sessionTime")
        if session_time is not None:
            # Convert from HHMM format to minutes
            if session_time >= 100:
                hours = session_time // 100
                minutes = session_time % 100
                return hours * 60 + minutes
            else:
                return session_time
        return None

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Return additional state attributes."""
        return {
            "session_time_raw": self.coordinator.data.get("sessionTime")
        }


class FFESSaunaVentilationTimeSensor(FFESSaunaSensorBase):
    """Ventilation time sensor for FFES Sauna."""

    _attr_name = "Ventilation Time"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the ventilation time sensor."""
        super().__init__(coordinator, "ventilation_time")

    @property
    def native_value(self) -> int | None:
        """Return the ventilation time in minutes."""
        ventilation_time = self.coordinator.data.get("ventilationTime")
        if ventilation_time is not None:
            # Convert from HHMM format to minutes
            if ventilation_time >= 100:
                hours = ventilation_time // 100
                minutes = ventilation_time % 100
                return hours * 60 + minutes
            else:
                return ventilation_time
        return None

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Return additional state attributes."""
        return {
            "ventilation_time_raw": self.coordinator.data.get("ventilationTime")
        }


class FFESSaunaAromaSensor(FFESSaunaSensorBase):
    """Aroma sensor for FFES Sauna."""

    _attr_name = "Aromatherapy"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:flower"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the aroma sensor."""
        super().__init__(coordinator, "aroma")

    @property
    def native_value(self) -> int | None:
        """Return the aroma value."""
        return self.coordinator.data.get("aromaValue")


class FFESSaunaHumidityValueSensor(FFESSaunaSensorBase):
    """Humidity value sensor for FFES Sauna."""

    _attr_name = "Humidity Control"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: FFESSaunaCoordinator) -> None:
        """Initialize the humidity value sensor."""
        super().__init__(coordinator, "humidity_control")

    @property
    def native_value(self) -> int | None:
        """Return the humidity control value."""
        return self.coordinator.data.get("humidityValue")