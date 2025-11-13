# FFES Sauna Home Assistant Integration

A Home Assistant integration for FFES Sauna controllers that provides comprehensive control and monitoring capabilities through Modbus TCP protocol.

## Features

### Entities Created

- **Climate Entity**: Complete sauna temperature control with HVAC modes (Off, Heat, Fan Only, Auto)
- **Switch Entities**: Control sauna light and auxiliary (AUX) functions
- **Sensor Entities**: Monitor temperature, humidity, status, profile, session time, ventilation time, aromatherapy, and humidity control
- **Select Entity**: Choose between different sauna profiles (Infrared, Dry, Wet, Ventilation, Steambath, etc.)

### Supported Operations

- Set target temperature (20-110°C)
- Start/stop heating
- Control ventilation
- Manage lighting and auxiliary functions
- Select sauna profiles
- Monitor current conditions
- Session time management

## Installation

### Method 1: Manual Installation

1. Copy the `ffes_sauna` folder to your Home Assistant `custom_components` directory:
   ```
   /config/custom_components/ffes_sauna/
   ```

2. Restart Home Assistant

3. Go to Configuration → Integrations → Add Integration

4. Search for "FFES Sauna" and select it

5. Enter your sauna's configuration:
   - **Host or IP Address**: The IP address or hostname of your sauna (default: `ffes.local`)
   - **Update Interval**: How often to poll the sauna for updates in seconds (default: 15, minimum: 5, maximum: 300)

### Method 2: HACS Installation

1. **Add Custom Repository**:
   - Open HACS in Home Assistant
   - Go to "Integrations"
   - Click the three dots menu → "Custom repositories"
   - Add this repository URL: `https://github.com/mattstasch/ffes-sauna-homeassistant`
   - Select "Integration" as the category
   - Click "Add"

2. **Install the Integration**:
   - Search for "FFES Sauna" in HACS
   - Click "Install"
   - Restart Home Assistant
   - Go to Configuration → Integrations → Add Integration
   - Search for "FFES Sauna" and configure

### Method 3: Git Clone Installation

```bash
cd /config/custom_components
git clone https://github.com/mattstasch/ffes-sauna-homeassistant.git
mv ffes-sauna-homeassistant/ffes_sauna ./
rm -rf ffes-sauna-homeassistant
```

Then restart Home Assistant and add the integration.

## Configuration

### Initial Setup

1. Ensure your FFES Sauna controller is connected to your network with Modbus TCP enabled
2. Verify Modbus TCP connectivity on port 502
3. The controller should respond to Modbus holding register reads

### Configuration Parameters

- **Host**: IP address or hostname of your sauna controller
  - Default: `ffes.local` (uses mDNS/zeroconf discovery)
  - Examples: `192.168.1.100`, `sauna.local`, `ffes.local`
  - Controller must have Modbus TCP enabled on port 502

- **Update Interval**: Polling frequency in seconds
  - Default: 15 seconds
  - Range: 5-300 seconds
  - Lower values provide more responsive updates but may increase network traffic

## Usage

### Climate Control

The main climate entity provides:
- **Temperature Control**: Set target temperature between 20-110°C
- **HVAC Modes**:
  - `Off`: Turn off sauna
  - `Heat`: Active heating mode
  - `Fan Only`: Ventilation mode
  - `Auto`: Standby mode

### Profile Selection

Use the Profile select entity to choose between:
1. **Infrared Sauna**: Traditional infrared heating
2. **Dry Sauna**: Classic dry heat sauna
3. **Wet Sauna**: Steam-enhanced sauna experience
4. **Ventilation**: Air circulation mode
5. **Steambath**: Full steam experience
6. **Infrared CPIR**: Specialized infrared mode
7. **Infrared MIX**: Mixed infrared heating

### Automation Examples

#### Basic Temperature Control
```yaml
automation:
  - alias: "Heat Sauna for Evening Session"
    trigger:
      platform: time
      at: "18:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.ffes_sauna
        data:
          temperature: 80
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.ffes_sauna
        data:
          hvac_mode: heat
```

#### Profile-Based Session
```yaml
automation:
  - alias: "Start Dry Sauna Session"
    trigger:
      platform: state
      entity_id: input_boolean.start_sauna_session
      to: 'on'
    action:
      - service: select.select_option
        target:
          entity_id: select.ffes_sauna_profile
        data:
          option: "Dry Sauna"
      - service: climate.set_temperature
        target:
          entity_id: climate.ffes_sauna
        data:
          temperature: 85
```

#### Safety Automation
```yaml
automation:
  - alias: "Sauna Safety Timeout"
    trigger:
      platform: state
      entity_id: sensor.ffes_sauna_session_time
      to: 120  # 2 hours in minutes
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.ffes_sauna
        data:
          hvac_mode: 'off'
      - service: notify.mobile_app_your_phone
        data:
          message: "Sauna automatically turned off after 2 hours"
```

## Entities Reference

### Climate
- `climate.ffes_sauna`: Main sauna climate control

### Switches
- `switch.ffes_sauna_light`: Sauna interior lighting
- `switch.ffes_sauna_aux`: Auxiliary functions

### Sensors
- `sensor.ffes_sauna_temperature`: Current temperature (°C)
- `sensor.ffes_sauna_humidity`: Current humidity (%)
- `sensor.ffes_sauna_status`: Operating status (off/heat/fan_only/auto)
- `sensor.ffes_sauna_profile`: Current sauna profile
- `sensor.ffes_sauna_session_time`: Session duration (minutes)
- `sensor.ffes_sauna_ventilation_time`: Ventilation time (minutes)
- `sensor.ffes_sauna_aromatherapy`: Aromatherapy level (%)
- `sensor.ffes_sauna_humidity_control`: Humidity control level (%)

### Select
- `select.ffes_sauna_profile`: Sauna profile selection

## Troubleshooting

### Connection Issues

1. **Cannot connect during setup**:
   - Verify the sauna controller is powered on and connected to the network
   - Check the IP address/hostname is correct
   - Ensure firewall allows Modbus TCP connections on port 502
   - Test Modbus connectivity using tools like `mbpoll` or `pymodbus`

2. **Integration goes unavailable**:
   - Check network connectivity to the sauna
   - Verify the sauna controller is responding
   - Check Home Assistant logs for specific error messages

### Data Issues

1. **Entities show unknown/unavailable**:
   - Check the sauna controller is responding to Modbus requests
   - Verify Modbus holding registers are accessible (addresses 1, 2, 4, 20)
   - Check integration logs for Modbus connection errors

2. **Updates are slow**:
   - Reduce the update interval in integration configuration
   - Check network latency to the sauna controller

### Logs

Enable debug logging by adding to `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.ffes_sauna: debug
```

## Modbus Reference

This integration uses Modbus TCP protocol to communicate with the sauna controller:

**Key Modbus Parameters:**
- **Unit ID**: 1
- **Port**: 502
- **Function Codes**: 3 (Read Holding Registers), 6 (Write Single Register)
- **Register Mapping**:
  - Address 1: Temperature Set Value
  - Address 2: Actual Temperature
  - Address 4: Sauna Profile
  - Address 20: Controller Status

**Register Addresses (0-based):**
- Temperature control: Register 1
- Current temperature: Register 2
- Profile selection: Register 4
- Status control: Register 20
- Session time: Register 5
- Ventilation time: Register 6
- Aromatherapy: Register 9
- Humidity control: Register 10

## Contributing

This integration is open source. Contributions, bug reports, and feature requests are welcome.

### Development Setup

1. Clone the repository
2. Install Home Assistant development environment
3. Link the integration to your development instance
4. Test with a real FFES Sauna controller

## License

This project is licensed under the MIT License.

## Disclaimer

This is an unofficial integration and is not affiliated with FFES. Use at your own risk. Always follow proper sauna safety guidelines and never leave a sauna unattended while in operation.