"""Climate platform for Tuya mini-splits via MCP — heat and cool."""
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

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
    coordinator = data["coordinator"]
    devices = data.get("devices", {})

    entities = []
    climate_devices = devices.get("climate", [])
    _LOGGER.info("Setting up %d climate devices from config", len(climate_devices))
    for device_config in climate_devices:
        _LOGGER.info("Adding climate device: %s", device_config)
        entities.append(
            TuyaMcpClimate(
                coordinator=coordinator,
                device_id=device_config["id"],
                name=device_config["name"],
            )
        )

    _LOGGER.info("Adding %d climate entities to HA", len(entities))
    async_add_entities(entities)


class TuyaMcpClimate(CoordinatorEntity, ClimateEntity):
    """A climate entity that controls a mini-split via MCP."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_fan_modes = ["low", "medium", "high", "auto"]
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_min_temp = 60
    _attr_max_temp = 86

    def __init__(self, coordinator, device_id: str, name: str):
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"tuya_mcp_{device_id}"

    @property
    def available(self) -> bool:
        """Return True if coordinator has data for this device."""
        if not self.coordinator.last_update_success:
            return False
        data = self.coordinator.data or {}
        device = data.get(self._device_id)
        if device is None:
            return False
        # Device returned an error (e.g. connection failed)
        return "error" not in device

    def _handle_coordinator_update(self) -> None:
        """Process coordinator data into entity attributes."""
        data = self.coordinator.data or {}
        device = data.get(self._device_id)

        if device and "error" not in device:
            is_on = device.get("is_on", False)
            mode = device.get("mode")
            self._attr_current_temperature = device.get("current_temperature")
            self._attr_target_temperature = device.get("target_temperature")
            self._attr_fan_mode = device.get("fan_speed")

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

        super()._handle_coordinator_update()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            result = await self.coordinator.call_tool("set_power", {
                "deviceId": self._device_id,
                "state": "off",
            })
        else:
            if self._attr_hvac_mode == HVACMode.OFF:
                await self.coordinator.call_tool("set_power", {
                    "deviceId": self._device_id,
                    "state": "on",
                })

            mode = HVAC_MODE_REVERSE.get(hvac_mode, "heat")
            result = await self.coordinator.call_tool("set_mode", {
                "deviceId": self._device_id,
                "mode": mode,
            })

        if result and "error" not in result:
            self._attr_hvac_mode = hvac_mode
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            temp = kwargs[ATTR_TEMPERATURE]
            result = await self.coordinator.call_tool("set_temperature", {
                "deviceId": self._device_id,
                "temperature": temp,
            })
            if result and "error" not in result:
                self._attr_target_temperature = temp
                self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        result = await self.coordinator.call_tool("set_fan_speed", {
            "deviceId": self._device_id,
            "speed": fan_mode,
        })
        if result and "error" not in result:
            self._attr_fan_mode = fan_mode
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
