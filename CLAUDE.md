# FFES Sauna Home Assistant Integration - Claude Context

## Project Overview
This is a **Home Assistant custom integration** for FFES Sauna controllers that provides local network communication with sauna devices.

**Key Features:**
- **Local Modbus TCP communication** with FFES sauna controllers
- Automatic device discovery via **zeroconf/mDNS**
- Climate control, switches, sensors, and select entities
- Real-time sauna status monitoring and control

## Architecture

### Core Components
1. **Config Flow** (`config_flow.py`) - Device setup and discovery
2. **Coordinator** (`coordinator.py`) - Data fetching and command sending
3. **Climate** (`climate.py`) - Temperature control interface
4. **Switches** (`switch.py`) - On/off controls
5. **Sensors** (`sensor.py`) - Status monitoring
6. **Select** (`select.py`) - Profile selection

### Integration Type
- **Domain**: `ffes_sauna`
- **Type**: `hub` (local polling)
- **Communication**: Modbus TCP over local network
- **Discovery**: Zeroconf automatic discovery + manual fallback

## Recent Major Improvements

### ✅ Modbus TCP Conversion (2025-11-13)
**Major Change**: Converted entire integration from HTTP API to **Modbus TCP** communication.

**Why the change**:
- HTTP API became unreliable/deprecated on device firmware
- Modbus TCP provides more direct, reliable communication
- Better real-time performance and stability

**Implementation Details**:
- **Protocol**: Modbus TCP on port 502
- **Unit ID**: 1
- **Function Code**: 3 (Holding Registers)
- **Address Format**: 0-based (REG[1] = address 1)
- **Key Registers**: 1 (temp set), 2 (temp actual), 4 (profile), 20 (status)

**Register Mapping**:
```
Address 1:  TEMPERATURE_SET_VALUE    -> setTemp
Address 2:  TEMP1_ACTUAL_VALUE       -> actualTemp
Address 4:  SAUNA_PROFILE            -> profile
Address 20: CONTROLLER_STATUS        -> controllerStatus
Address 5:  SESSION_TIME             -> sessionTime
Address 9:  AROMA_SET_VALUE          -> aromaValue
Address 10: VAPORIZER_HUMIDITY_SET_VALUE -> humidityValue
```

**Changes Made**:
- `coordinator.py`: Complete rewrite using pymodbus AsyncModbusTcpClient
- `config_flow.py`: Replaced HTTP validation with Modbus register reads
- `manifest.json`: Updated requirements from aiohttp to pymodbus>=3.0.0
- Discovery: Added `_modbus._tcp.local.` service type

### ✅ Zeroconf Discovery Implementation (2025-11-09)
**Problem Solved**: Manual mDNS resolution was unreliable and error-prone.

**Solution Implemented**:
- Added proper zeroconf service discovery following HA patterns
- Automatic device discovery when saunas broadcast services
- Reliable IP address storage instead of hostname resolution

**Key Changes**:
- `manifest.json`: Added zeroconf dependency and service types (`_http._tcp.local.`, `_ffes._tcp.local.`)
- `config_flow.py`: Implemented `async_step_zeroconf()` with IPv6 filtering and device validation
- `coordinator.py`: Enhanced mDNS resolution with multiple methods and IP address detection
- `strings.json`: Added zeroconf confirmation UI

### Discovery Flow
1. **Automatic**: Zeroconf broadcasts are automatically detected by HA
2. **Validation**: Integration validates device via `/sauna-data` endpoint
3. **Confirmation**: User confirms discovered device with hostname/IP display
4. **Storage**: Reliable IP address stored in config (not hostname)
5. **Fallback**: Manual configuration available if auto-discovery fails

## File Structure & Key Locations

```
custom_components/ffes_sauna/
├── __init__.py              # Integration setup and coordinator initialization
├── manifest.json            # Dependencies, zeroconf services, requirements
├── config_flow.py          # Setup flow with zeroconf + manual config
├── coordinator.py          # HTTP API communication and mDNS resolution
├── climate.py              # Temperature control entity
├── switch.py               # On/off control entities
├── sensor.py               # Status monitoring entities
├── select.py               # Profile selection entity
├── const.py                # Constants and configuration defaults
└── strings.json            # UI text for config flow steps
```

## API Communication

### Endpoints
- **Status**: `GET http://{host}/sauna-data` - Current state and temperatures
- **Control**: `POST http://{host}/sauna-control` - Send commands

### Data Structure
**Status Response** (`/sauna-data`):
```json
{
  "controllerStatus": 0-3,     # 0=off, 1=heat, 2=fan_only, 3=auto
  "actualTemp": 25,            # Current temperature
  "targetTemp": 80,            # Target temperature
  "profile": 1-7,              # Sauna profile (1=Infrared, 2=Dry, etc.)
  "sessionTime": 1800,         # Session time in seconds
  "ventilationTime": 300,      # Ventilation time in seconds
  "aromaValue": 5,             # Aroma intensity
  "humidityValue": 50          # Humidity percentage
}
```

**Control Request** (`/sauna-control`):
```
Content-Type: application/x-www-form-urlencoded
action=set_temp&value=85
action=start_session&value=1800&profile=2&aroma=5&humidity=60
```

## Configuration Patterns

### Zeroconf Discovery (Preferred)
- HA automatically detects broadcasting devices
- User confirms with device details shown
- IP address stored directly for reliability

### Manual Configuration (Fallback)
- User enters hostname/IP manually
- Supports both IP addresses and `.local` hostnames
- Robust mDNS resolution with multiple fallback methods

### Config Data Structure
```python
{
    CONF_HOST: "192.168.1.100",        # IP address or hostname
    CONF_SCAN_INTERVAL: 15             # Update interval in seconds
}
```

## Network Resolution Strategy

### mDNS Handling (`coordinator.py`)
1. **IP Detection**: Check if host is already an IP address → use directly
2. **Hostname Check**: If not `.local` → use as-is
3. **mDNS Resolution**: Try `gethostbyname()` then `getaddrinfo()` with timeout
4. **Caching**: Cache resolved IP addresses to avoid repeated lookups
5. **Graceful Fallback**: Use original hostname if resolution fails

### Error Handling
- Connection timeouts: 10 seconds for operations, 5 seconds for discovery
- DNS resolution timeouts: 5 seconds with fallback to original hostname
- HTTP errors: Proper status code checking and logging
- Invalid data: Validation of expected sauna API response structure

## Development Guidelines

### Testing Commands
- **Lint**: Check README or search codebase for lint command
- **Type Check**: Check README or search codebase for typecheck command
- **Tests**: Check README or search codebase for test command

### Code Patterns
- Always use `async_get_clientsession(hass)` for HTTP requests
- Use `hass.async_add_executor_job()` for blocking operations
- Follow HA entity naming conventions
- Implement proper unique IDs (use IP addresses for zeroconf discoveries)
- Add comprehensive logging with appropriate levels (debug, info, warning, error)

### Common Issues & Solutions

#### mDNS Resolution Failures
- **Symptom**: "Failed to resolve mDNS hostname" warnings
- **Cause**: Usually hostname stored instead of IP address from zeroconf
- **Solution**: Ensure zeroconf discovery stores IP address, not hostname

#### Discovery Not Working
- **Check**: Device is broadcasting the correct zeroconf service types
- **Check**: Network allows multicast/broadcast traffic
- **Check**: Home Assistant can reach the device on HTTP port

#### Connection Timeouts
- **Check**: Device is actually accessible on the network
- **Check**: Firewall settings on both HA and device
- **Check**: Device HTTP server is responding correctly

## Constants & Defaults

### Configuration
- **Default Host**: `ffes.local`
- **Default Scan Interval**: 15 seconds
- **Scan Interval Range**: 5-300 seconds

### Sauna Status Mappings
```python
SAUNA_STATUS_MAP = {
    0: "off",
    1: "heat",
    2: "fan_only",
    3: "auto"
}

SAUNA_PROFILES = {
    1: "Infrared Sauna",
    2: "Dry Sauna",
    3: "Wet Sauna",
    4: "Ventilation",
    5: "Steambath",
    6: "Infrared CPIR",
    7: "Infrared MIX"
}
```

## Future Development Notes

### Potential Enhancements
- Add support for multiple sauna zones if FFES controllers support it
- Implement WebSocket connection for real-time updates
- Add support for additional FFES controller models
- Implement device diagnostics for troubleshooting

### Known Limitations
- Only supports IPv4 addresses (IPv6 filtered out in zeroconf)
- HTTP-only communication (no HTTPS support)
- Polling-based updates (no push notifications from device)

---
*Last Updated: 2025-11-09 - After implementing zeroconf discovery and fixing mDNS resolution issues*