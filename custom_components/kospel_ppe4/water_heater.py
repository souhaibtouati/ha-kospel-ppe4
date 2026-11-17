"""Water heater platform for Kospel PPE4.M."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TEMP_MAX, TEMP_MIN, TEMP_STEP
from .coordinator import KospelDataCoordinator
from .entity import KospelEntity

_LOGGER = logging.getLogger(__name__)

# Profile names matching the LCD: TEMP 1, TEMP 2, TEMP 3
PROFILE_MODES = ["Profile 1", "Profile 2", "Profile 3"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KospelDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KospelWaterHeater(coordinator)])


class KospelWaterHeater(KospelEntity, WaterHeaterEntity):
    """Representation of the Kospel PPE4.M water heater."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = TEMP_STEP
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
    )
    _enable_turn_on_off_backwards_compat = False

    def __init__(self, coordinator: KospelDataCoordinator) -> None:
        super().__init__(coordinator, "water_heater")
        self._attr_name = None  # Use device name

    @property
    def min_temp(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.temp_min
        return TEMP_MIN

    @property
    def max_temp(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.temp_max
        return TEMP_MAX

    @property
    def operation_list(self) -> list[str]:
        return PROFILE_MODES

    @property
    def current_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        data = self.coordinator.data
        if data.is_heating and data.outlet_temp is not None:
            return data.outlet_temp
        if data.outlet_temp is not None and data.outlet_temp > 0:
            return data.outlet_temp
        return data.inlet_temp

    @property
    def target_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.target_temp

    @property
    def current_operation(self) -> str | None:
        """Determine which profile is active based on matching target temp."""
        data = self.coordinator.data
        if data is None or data.target_temp is None:
            return None
        target = data.target_temp
        profiles = {
            "Profile 1": data.profile1_temp,
            "Profile 2": data.profile2_temp,
            "Profile 3": data.profile3_temp,
        }
        for name, temp in profiles.items():
            if temp is not None and abs(temp - target) < 0.5:
                return name
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        data = self.coordinator.data
        if data is None:
            return attrs

        if data.inlet_temp is not None:
            attrs["inlet_temperature"] = data.inlet_temp
        if data.outlet_temp is not None:
            attrs["outlet_temperature"] = data.outlet_temp
        if data.flow_rate is not None:
            attrs["flow_rate_l_min"] = data.flow_rate
        if data.power_kw is not None:
            attrs["power_kw"] = data.power_kw
        if data.selected_power_kw is not None:
            attrs["selected_power_kw"] = data.selected_power_kw
        if data.heating_stage is not None:
            attrs["heating_stage"] = data.heating_stage
        attrs["is_heating"] = data.is_heating
        attrs["is_power_limited"] = data.is_power_limited
        if data.profile1_temp is not None:
            attrs["profile_1"] = data.profile1_temp
        if data.profile2_temp is not None:
            attrs["profile_2"] = data.profile2_temp
        if data.profile3_temp is not None:
            attrs["profile_3"] = data.profile3_temp
        if data.active_errors:
            attrs["errors"] = data.active_errors
        if data.active_warnings:
            attrs["warnings"] = data.active_warnings

        return attrs

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return

        data = self.coordinator.data
        temp = max(self.min_temp, min(self.max_temp, float(temp)))
        _LOGGER.info("Setting PPE4.M target temperature to %.1f°C", temp)

        current = data.raw_temp_settings if data else None
        await self.coordinator.client.async_set_target_temperature(temp, current)
        await self.coordinator.async_request_refresh()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Switch to a profile by setting the target to that profile's temperature."""
        data = self.coordinator.data
        if data is None:
            return

        profile_temps = {
            "Profile 1": data.profile1_temp,
            "Profile 2": data.profile2_temp,
            "Profile 3": data.profile3_temp,
        }
        temp = profile_temps.get(operation_mode)
        if temp is not None:
            _LOGGER.info(
                "Switching to %s (%.1f°C)", operation_mode, temp
            )
            current = data.raw_temp_settings
            await self.coordinator.client.async_set_target_temperature(temp, current)
            await self.coordinator.async_request_refresh()
