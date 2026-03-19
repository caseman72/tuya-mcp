"""Tuya MCP Integration for Home Assistant."""
import logging
import os

import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT, CONF_MCP_HOST, CONF_MCP_PORT

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya MCP from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data.get(CONF_MCP_HOST, DEFAULT_HOST)
    port = entry.data.get(CONF_MCP_PORT, DEFAULT_PORT)

    devices = await hass.async_add_executor_job(load_devices)

    hass.data[DOMAIN][entry.entry_id] = {
        "host": host,
        "port": port,
        "devices": devices,
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
