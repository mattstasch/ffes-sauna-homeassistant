# Sauna Control Panel API Documentation

This document describes the API endpoints used by the sauna control interface.

## Base URL
All API endpoints are relative to the web server root.

## Endpoints

### 1. GET /sauna-data

**Description**: Retrieves current sauna status, settings, and sensor data.

**Method**: GET

**Response Format**: JSON

**Response Fields**:
- `controllerStatus` (number): Current controller status (0=OFF, 1=HEATING, 2=VENTILATION, 3=STANDBY)
- `light` (boolean): Light state (true=ON, false=OFF)
- `aux` (boolean): AUX state (true=ON, false=OFF)
- `controllerModel` (number): Controller model identifier
- `actualTemp` (number): Current temperature in Celsius
- `humidity` (number): Current humidity percentage
- `setTemp` (number, optional): Set temperature in Celsius
- `profile` (number, optional): Selected sauna profile (1-7)
- `sessionTime` (number, optional): Session time in HHMM format
- `ventilationTime` (number, optional): Ventilation time in HHMM format
- `aromaValue` (number, optional): Aromatherapy percentage (0-100)
- `humidityValue` (number, optional): Humidity/vaporizer percentage (0-100)

**Example Response**:
```json
{
  "controllerStatus": 1,
  "light": true,
  "aux": false,
  "controllerModel": 1,
  "actualTemp": 75,
  "humidity": 45,
  "setTemp": 80,
  "profile": 1,
  "sessionTime": 130,
  "ventilationTime": 15,
  "aromaValue": 50,
  "humidityValue": 60
}
```

**Real Example Response**:
```json
{
  "controllerStatus": 3,
  "actualTemp": 29,
  "setTemp": 95,
  "humidity": 0,
  "profile": 2,
  "sessionTime": 40,
  "ventilationTime": 0,
  "aromaValue": 0,
  "humidityValue": 0,
  "light": false,
  "aux": false,
  "controllerModel": 2
}
```

**Response Interpretation**:
- **controllerStatus**: 3 = STANDBY (sauna is in standby mode)
- **actualTemp**: 29°C (current measured temperature)
- **setTemp**: 95°C (target temperature setting)
- **humidity**: 0% (current humidity reading)
- **profile**: 2 = Dry Sauna (selected sauna profile)
- **sessionTime**: 40 = 00:40 (40 minutes session time in MM format)
- **ventilationTime**: 0 = 00:00 (no ventilation time set)
- **aromaValue**: 0% (aromatherapy disabled)
- **humidityValue**: 0% (humidity/vaporizer disabled)
- **light**: false (sauna light is OFF)
- **aux**: false (auxiliary function is OFF)
- **controllerModel**: 2 (controller hardware model identifier)

**Usage**: Called automatically every 5 seconds to update the UI and on page load.

---

### 2. POST /sauna-control

**Description**: Controls sauna operations including status changes, lighting, auxiliary functions, and session management.

**Method**: POST

**Content-Type**: application/x-www-form-urlencoded

**Request Parameters**:

#### Status Control
- `action=status`
- `value` (number): Status value (0=OFF, 1=HEATING, 2=VENTILATION, 3=STANDBY)

#### Light Control
- `action=light`
- `value` (string): "1" for ON, "0" for OFF

#### AUX Control
- `action=aux`
- `value` (string): "1" for ON, "0" for OFF

#### Session Start
- `action=start_session`
- `profile` (string): Sauna profile ID (1-7)
  - 1: Infrared Sauna
  - 2: Dry Sauna
  - 3: Wet Sauna
  - 4: Ventilation
  - 5: Steambath
  - 6: Infrared CPIR
  - 7: Infrared MIX
- `temperature` (string): Target temperature in Celsius (20-110)
- `session_time` (string): Session duration in HH:MM format
- `ventilation_time` (string): Ventilation duration in HH:MM format
- `aroma_value` (string): Aromatherapy percentage (0-100)
- `humidity_value` (string): Humidity/vaporizer percentage (0-100)

**Response Format**: JSON

**Response Fields**:
- `success` (boolean): Indicates if the operation was successful
- `message` (string, optional): Error message if success is false

**Example Requests**:

1. Set status to heating:
```
POST /sauna-control
Content-Type: application/x-www-form-urlencoded

action=status&value=1
```

2. Turn on light:
```
POST /sauna-control
Content-Type: application/x-www-form-urlencoded

action=light&value=1
```

3. Start a session:
```
POST /sauna-control
Content-Type: application/x-www-form-urlencoded

action=start_session&profile=1&temperature=80&session_time=01:30&ventilation_time=00:15&aroma_value=50&humidity_value=60
```

**Example Response**:
```json
{
  "success": true
}
```

**Error Response Example**:
```json
{
  "success": false,
  "message": "Invalid temperature value"
}
```

## Error Handling

The client-side code handles errors by:
- Displaying alert dialogs for user-facing errors
- Logging errors to console for data loading failures
- Preserving current state if API calls fail

## Data Update Frequency

- Initial data load: On page load (DOMContentLoaded event)
- Periodic updates: Every 5 seconds via setInterval
- Immediate updates: After successful control operations