"""Climate platform for Tuya mini-splits via MCP — heat and cool."""
import logging
import json
import asyncio
from datetime import timedelta

import aiohttp

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)

HVAC_MODE_MAP = {
    "cool": HVACMode.COOL,
    "heat": HVACMode.HEAT,
    "off": HVACMode.OFF,
}

HVAC_MODE_REVERSE = {v: k for k, v in HVAC_MODE_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya MCP climate entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    devices = data.get("devices", {})
    host = data["host"]
    port = data["port"]

    entities = []
    climate_devices = devices.get("climate", [])
    _LOGGER.info("Setting up %d climate devices from config", len(climate_devices))
    for device_config in climate_devices:
        _LOGGER.info("Adding climate device: %s", device_config)
        entities.append(
            TuyaMcpClimate(
                device_id=device_config["id"],
                name=device_config["name"],
                host=host,
                port=port,
            )
        )

    _LOGGER.info("Adding %d climate entities to HA", len(entities))
    async_add_entities(entities)


class TuyaMcpClimate(ClimateEntity):
    """A climate entity that controls a mini-split via MCP."""

    _attr_should_poll = True
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_fan_modes = ["low", "medium", "high", "auto"]
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_min_temp = 60
    _attr_max_temp = 86

    def __init__(self, device_id: str, name: str, host: str, port: int):
        """Initialize the climate entity."""
        self._device_id = device_id
        self._attr_name = name
        self._host = host
        self._port = port
        self._attr_unique_id = f"tuya_mcp_{device_id}"

        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_hvac_mode = None
        self._attr_fan_mode = None
        self._is_online = None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._is_online is None:
            return True
        return self._is_online

    async def async_added_to_hass(self) -> None:
        """Fetch initial state when entity is added to HA."""
        await super().async_added_to_hass()
        self.async_schedule_update_ha_state(True)

    async def _call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool via HTTP/SSE using aiohttp."""
        base_url = f"http://{self._host}:{self._port}"

        _LOGGER.debug("Calling MCP tool %s with %s", tool_name, arguments)

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{base_url}/sse") as sse_resp:
                    session_id = None

                    async for line in sse_resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data:'):
                            data = line[5:].strip()
                            if data.startswith('/messages/'):
                                if 'session_id=' in data:
                                    session_id = data.split('session_id=')[1]
                                    break
                            else:
                                try:
                                    parsed = json.loads(data)
                                    if isinstance(parsed, dict):
                                        endpoint = parsed.get('endpoint', '')
                                        if 'session_id=' in endpoint:
                                            session_id = endpoint.split('session_id=')[1]
                                            break
                                except json.JSONDecodeError:
                                    continue

                    if not session_id:
                        _LOGGER.error("Failed to get MCP session ID")
                        return None

                    messages_url = f"{base_url}/messages/?session_id={session_id}"

                    init_request = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "ha-tuya-mcp", "version": "1.0.0"}
                        }
                    }

                    async with session.post(messages_url, json=init_request) as init_resp:
                        if init_resp.status != 202:
                            _LOGGER.error("MCP initialize failed: %s", await init_resp.text())
                            return None

                    await asyncio.sleep(0.1)

                    notif_request = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized"
                    }
                    async with session.post(messages_url, json=notif_request) as notif_resp:
                        pass

                    tool_request = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": arguments
                        }
                    }

                    async with session.post(messages_url, json=tool_request) as tool_resp:
                        if tool_resp.status != 202:
                            _LOGGER.error("MCP tool call failed: %s", await tool_resp.text())
                            return None

                    async for line in sse_resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data:'):
                            try:
                                data = json.loads(line[5:].strip())
                                if isinstance(data, dict) and data.get('id') == 2:
                                    result = data.get('result', {})
                                    content = result.get('content', [])
                                    for item in content:
                                        if item.get('type') == 'text':
                                            return json.loads(item.get('text', '{}'))
                                    return result
                            except json.JSONDecodeError:
                                continue

                    return None

        except asyncio.TimeoutError:
            _LOGGER.error("MCP tool call timed out")
            return None
        except Exception as e:
            _LOGGER.error("MCP tool call failed: %s", e)
            return None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            result = await self._call_tool("set_power", {
                "deviceId": self._device_id,
                "state": "off"
            })
        else:
            # Turn on first if currently off
            if self._attr_hvac_mode == HVACMode.OFF:
                await self._call_tool("set_power", {
                    "deviceId": self._device_id,
                    "state": "on"
                })

            mode = HVAC_MODE_REVERSE.get(hvac_mode, "heat")
            result = await self._call_tool("set_mode", {
                "deviceId": self._device_id,
                "mode": mode
            })

        if result and "error" not in result:
            self._attr_hvac_mode = hvac_mode
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            temp = kwargs[ATTR_TEMPERATURE]
            result = await self._call_tool("set_temperature", {
                "deviceId": self._device_id,
                "temperature": temp
            })
            if result and "error" not in result:
                self._attr_target_temperature = temp
                self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        result = await self._call_tool("set_fan_speed", {
            "deviceId": self._device_id,
            "speed": fan_mode
        })
        if result and "error" not in result:
            self._attr_fan_mode = fan_mode
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Fetch the current state."""
        result = await self._call_tool("get_status", {
            "deviceId": self._device_id
        })
        if result and "error" not in result:
            self._is_online = result.get("is_on") is not None

            is_on = result.get("is_on", False)
            mode = result.get("mode")
            self._attr_current_temperature = result.get("current_temperature")
            self._attr_target_temperature = result.get("target_temperature")
            self._attr_fan_mode = result.get("fan_speed")

            if not is_on:
                self._attr_hvac_mode = HVACMode.OFF
            elif mode:
                self._attr_hvac_mode = HVAC_MODE_MAP.get(mode, HVACMode.OFF)
            else:
                self._attr_hvac_mode = HVACMode.OFF

            _LOGGER.debug(
                "Updated %s: temp=%s, mode=%s, target=%s, fan=%s",
                self._attr_name,
                self._attr_current_temperature,
                self._attr_hvac_mode,
                self._attr_target_temperature,
                self._attr_fan_mode,
            )
