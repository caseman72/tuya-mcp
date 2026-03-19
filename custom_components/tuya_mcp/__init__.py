"""Tuya MCP Integration for Home Assistant."""
import logging
import json
import os
import asyncio
from datetime import timedelta

import aiohttp
import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT, CONF_MCP_HOST, CONF_MCP_PORT

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE]
SCAN_INTERVAL = timedelta(seconds=30)


async def _mcp_call_tool(host: str, port: int, tool_name: str, arguments: dict) -> dict | None:
    """Call an MCP tool via HTTP/SSE. Single session, single handshake."""
    base_url = f"http://{host}:{port}"

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{base_url}/sse") as sse_resp:
                session_id = None

                async for line in sse_resp.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data.startswith("/messages/"):
                            if "session_id=" in data:
                                session_id = data.split("session_id=")[1]
                                break
                        else:
                            try:
                                parsed = json.loads(data)
                                if isinstance(parsed, dict):
                                    endpoint = parsed.get("endpoint", "")
                                    if "session_id=" in endpoint:
                                        session_id = endpoint.split("session_id=")[1]
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
                        "clientInfo": {"name": "ha-tuya-mcp", "version": "1.0.0"},
                    },
                }

                async with session.post(messages_url, json=init_request) as init_resp:
                    if init_resp.status != 202:
                        _LOGGER.error("MCP initialize failed: %s", await init_resp.text())
                        return None

                await asyncio.sleep(0.1)

                notif_request = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
                async with session.post(messages_url, json=notif_request):
                    pass

                tool_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                }

                async with session.post(messages_url, json=tool_request) as tool_resp:
                    if tool_resp.status != 202:
                        _LOGGER.error("MCP tool call failed: %s", await tool_resp.text())
                        return None

                async for line in sse_resp.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:].strip())
                            if isinstance(data, dict) and data.get("id") == 2:
                                result = data.get("result", {})
                                content = result.get("content", [])
                                for item in content:
                                    if item.get("type") == "text":
                                        return json.loads(item.get("text", "{}"))
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


class TuyaMcpCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches all device statuses in a single MCP call."""

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        super().__init__(
            hass,
            _LOGGER,
            name="tuya_mcp",
            update_interval=SCAN_INTERVAL,
        )
        self._host = host
        self._port = port

    async def _async_update_data(self) -> dict[str, dict]:
        """Fetch all statuses via one get_all_statuses call."""
        result = await _mcp_call_tool(self._host, self._port, "get_all_statuses", {})

        if result is None:
            raise UpdateFailed("get_all_statuses returned no data")

        devices = result.get("devices", [])
        # Key by device ID for fast lookup
        return {d["id"]: d for d in devices if "id" in d}

    async def call_tool(self, tool_name: str, arguments: dict) -> dict | None:
        """Proxy for command calls (set_power, set_mode, etc.)."""
        return await _mcp_call_tool(self._host, self._port, tool_name, arguments)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya MCP from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data.get(CONF_MCP_HOST, DEFAULT_HOST)
    port = entry.data.get(CONF_MCP_PORT, DEFAULT_PORT)

    devices = await hass.async_add_executor_job(load_devices)

    coordinator = TuyaMcpCoordinator(hass, host, port)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "host": host,
        "port": port,
        "devices": devices,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def load_devices() -> dict:
    """Load devices from devices.yaml."""
    devices_file = os.path.join(os.path.dirname(__file__), "devices.yaml")
    _LOGGER.info("Loading devices from: %s", devices_file)
    try:
        with open(devices_file, "r") as f:
            devices = yaml.safe_load(f) or {}
            _LOGGER.info("Loaded devices: %s", devices)
            return devices
    except Exception as e:
        _LOGGER.error("Failed to load devices.yaml: %s", e)
        return {}
