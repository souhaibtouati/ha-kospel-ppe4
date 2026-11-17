"""Binary sensor platform for Kospel PPE4.M."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import KospelData, KospelDataCoordinator
from .entity import KospelEntity


@dataclass(frozen=True, kw_only=True)
class KospelBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[KospelData], bool | None]


BINARY_SENSORS: tuple[KospelBinarySensorDescription, ...] = (
    KospelBinarySensorDescription(
        key="heating",
        name="Heating",
        icon="mdi:fire",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda d: d.is_heating,
    ),
    KospelBinarySensorDescription(
        key="power_limited",
        name="Power Limited",
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.is_power_limited,
    ),
    KospelBinarySensorDescription(
        key="temperature_locked",
        name="Temperature Locked",
        icon="mdi:lock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.is_temp_locked,
    ),
    KospelBinarySensorDescription(
        key="has_errors",
        name="Error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.has_errors,
    ),
    KospelBinarySensorDescription(
        key="has_warnings",
        name="Warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.has_warnings,
    ),
    KospelBinarySensorDescription(
        key="water_flowing",
        name="Water Flowing",
        icon="mdi:water",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.flow_rate is not None and d.flow_rate > 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KospelDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KospelBinarySensor(coordinator, desc) for desc in BINARY_SENSORS
    )


class KospelBinarySensor(KospelEntity, BinarySensorEntity):
    entity_description: KospelBinarySensorDescription

    def __init__(
        self,
        coordinator: KospelDataCoordinator,
        description: KospelBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
