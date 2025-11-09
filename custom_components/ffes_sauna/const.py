"""Constants for the FFES Sauna integration."""
from typing import Final

DOMAIN: Final = "ffes_sauna"

DEFAULT_HOST: Final = "ffes.local"
DEFAULT_SCAN_INTERVAL: Final = 15

CONF_SCAN_INTERVAL = "scan_interval"

SAUNA_STATUS_MAP: Final = {
    0: "off",
    1: "heat",
    2: "fan_only",
    3: "auto"
}

SAUNA_PROFILES: Final = {
    1: "Infrared Sauna",
    2: "Dry Sauna",
    3: "Wet Sauna",
    4: "Ventilation",
    5: "Steambath",
    6: "Infrared CPIR",
    7: "Infrared MIX"
}

ATTR_CONTROLLER_STATUS = "controller_status"
ATTR_CONTROLLER_MODEL = "controller_model"
ATTR_PROFILE = "profile"
ATTR_SESSION_TIME = "session_time"
ATTR_VENTILATION_TIME = "ventilation_time"
ATTR_AROMA_VALUE = "aroma_value"
ATTR_HUMIDITY_VALUE = "humidity_value"