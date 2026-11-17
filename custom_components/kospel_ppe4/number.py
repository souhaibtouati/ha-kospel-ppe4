"""Number platform for Kospel PPE4.M — profile temperature setpoints."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TEMP_MAX, TEMP_MIN, TEMP_STEP
from .coordinator import KospelData, KospelDataCoordinator
from .entity import KospelEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class KospelNumberDescription(NumberEntityDescription):
    value_fn: Callable[[KospelData], float | None]
    profile_num: int  # 1, 2, or 3


NUMBER_DESCRIPTIONS: tuple[KospelNumberDescription, ...] = (
    KospelNumberDescription(
        key="profile1_setpoint",
        name="Profile 1 Temperature",
        icon="mdi:numeric-1-circle",
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=TEMP_STEP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.profile1_temp,
        profile_num=1,
    ),
    KospelNumberDescription(
        key="profile2_setpoint",
        name="Profile 2 Temperature",
        icon="mdi:numeric-2-circle",
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=TEMP_STEP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.profile2_temp,
        profile_num=2,
    ),
    KospelNumberDescription(
        key="profile3_setpoint",
        name="Profile 3 Temperature",
        icon="mdi:numeric-3-circle",
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=TEMP_STEP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.profile3_temp,
        profile_num=3,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KospelDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KospelNumber(coordinator, desc) for desc in NUMBER_DESCRIPTIONS
    )


class KospelNumber(KospelEntity, NumberEntity):
    entity_description: KospelNumberDescription

    def __init__(
        self,
        coordinator: KospelDataCoordinator,
        description: KospelNumberDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_min_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.temp_min
        return TEMP_MIN

    @property
    def native_max_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.temp_max
        return TEMP_MAX

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data
        current = data.raw_temp_settings if data else None
        await self.coordinator.client.async_set_profile_temperature(
            self.entity_description.profile_num, value, current
        )
        await self.coordinator.async_request_refresh()
