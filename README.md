# Kospel PPE4.M — Home Assistant Integration

Custom integration for the **Kospel PPE4.M** electric instantaneous water heater with WiFi module.


## Features

- **Water heater entity** with target temperature control and profile switching (TEMP 1/2/3)
- **Live sensors**: inlet/outlet temperature, flow rate, power (kW), heating stage, active setpoint
- **Binary sensors**: heating active, water flowing, power limited, temperature locked, error/warning states
- **Energy statistics**: today, yesterday, week, month, year, and lifetime (kWh)
- **Water statistics**: today, yesterday, week, month, year, and lifetime (L)
- **Error/warning decoding**: all 11 error codes (E01–E11) and 17 warning codes (W01–W17) decoded with descriptions from the official manual
- **Dynamic temperature limits**: min/max automatically read from the device (respects NORMAL 60°C / SHOWER 55°C mode and LCD TEMP MAX setting)
- **Profile temperature sliders**: adjust Profile 1/2/3 temperatures

## Installation

### HACS (recommended)
1. Add this repository as a custom repository in HACS
2. Install "Kospel PPE4.M Water Heater"
3. Restart Home Assistant
4. Go to Settings → Integrations → Add → search "Kospel"

### Manual
1. Copy `custom_components/kospel_ppe4/` to your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via Settings → Integrations

## Configuration

Enter the IP address of your PPE4.M device. The device must be on the same network as Home Assistant. Recommended: assign a static DHCP lease to the device.

**Options**: Polling interval (default 10 seconds, configurable 5–300s).

## Entities Created

| Entity | Type | Description |
|---|---|---|
| Water Heater | `water_heater` | Main control: target temperature + profile switching |
| Inlet Temperature | `sensor` | Cold water inlet (°C) |
| Outlet Temperature | `sensor` | Hot water outlet (°C) |
| Active Setpoint | `sensor` | Currently active temperature target (°C) |
| Flow Rate | `sensor` | Water flow (l/min) |
| Power | `sensor` | Current power consumption (kW) |
| Selected Power | `sensor` | Configured power level (kW) |
| Heating Stage | `sensor` | Number of active heating stages |
| Heating | `binary_sensor` | ON when actively heating |
| Water Flowing | `binary_sensor` | ON when water is flowing |
| Power Limited | `binary_sensor` | ON when device can't reach target at max power |
| Temperature Locked | `binary_sensor` | ON when setpoint at profile/max boundary |
| Error | `binary_sensor` | ON when a critical error is active |
| Warning | `binary_sensor` | ON when a warning is active |
| Active Errors | `sensor` | Decoded error codes (e.g. "E02: Inlet sensor failure") |
| Active Warnings | `sensor` | Decoded warning codes |
| Energy Today/Week/Month/Year/Lifetime | `sensor` | Energy consumption (kWh) |
| Water Today/Week/Month/Year/Lifetime | `sensor` | Water consumption (L) |
| Profile 1/2/3 Temperature | `number` | Adjustable profile setpoints (°C) |

## API Reference

See the complete [API Reference document](Kospel_PPE4M_API_Reference.md) for full register mappings.
Please feel free to contribute by updating the register mapping in case you find some errors.

## Notes

- The device has **no authentication** — anyone on the local network can control it. Isolate on a dedicated VLAN.
- The firmware expects all 5 config registers written together (`1390`–`1394`). This integration handles that automatically.
- Error codes E01 and E11 indicate dangerous conditions (triac/control failure) — the device LCD displays "Power Off" and the user should **immediately disconnect power**.
