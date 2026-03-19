# tuya-mcp

MCP server for Tuya-based mini-split climate control with Home Assistant integration. Uses [@caseman72/tuya-api](https://github.com/caseman72/tuya-api) for local LAN device communication — no cloud dependency.

## Installation

```bash
npm install
```

## Configuration

### 1. Device credentials

Create `.tuya-devices.json` with your device configs (see [tuya-api](https://github.com/caseman72/tuya-api) for setup):

```json
[
  {
    "id": "DEVICE_ID",
    "name": "Living Room",
    "key": "LOCAL_KEY",
    "ip": "192.168.1.100",
    "version": "3.4",
    "dps": { "power": "1", "target_temp": "24", "current_temp": "23", "mode": "4", "fan_speed": "5", "temp_unit": "19" },
    "temp_scale": 10
  }
]
```

### 2. Server config (optional)

```bash
cp config.example.json config.json
```

## Usage

```bash
# Stdio mode (for Claude Code / mcp-proxy)
npm start

# Add to Claude Code
claude mcp add tuya-mcp -- node /path/to/tuya-mcp/src/index.js
```

### Home Assistant

Run via `mcp-proxy` to expose HTTP/SSE:

```bash
mcp-proxy --port 8082 -- node src/index.js
```

Copy `custom_components/tuya_mcp/` to your HA `custom_components/` directory and create `devices.yaml` from the example.

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_devices` | List all configured devices |
| `get_status` | Get temperature, mode, fan speed |
| `get_all_statuses` | Get status of all devices at once |
| `set_power` | Turn on/off |
| `set_temperature` | Set target temperature (°F) |
| `set_mode` | Set mode: heat or cool |
| `set_fan_speed` | Set fan: low, medium, high, auto |
| `scan_device` | Read all raw DPS values |

## License

MIT
