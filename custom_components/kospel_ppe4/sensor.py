"""Sensor platform for Kospel PPE4.M."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import KospelData, KospelDataCoordinator
from .entity import KospelEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class KospelSensorDescription(SensorEntityDescription):
    value_fn: Callable[[KospelData], Any]


def _format_datetime(d: KospelData) -> str | None:
    if d.dt_year and d.dt_month and d.dt_day:
        h = d.dt_hour or 0
        m = d.dt_minute or 0
        s = d.dt_second or 0
        return f"{d.dt_year:04d}-{d.dt_month:02d}-{d.dt_day:02d} {h:02d}:{m:02d}:{s:02d}"
    return None


def _format_errors(d: KospelData) -> str | None:
    if d.active_errors:
        return "; ".join(d.active_errors)
    return "None"


def _format_warnings(d: KospelData) -> str | None:
    if d.active_warnings:
        return "; ".join(d.active_warnings)
    return "None"


SENSORS: tuple[KospelSensorDescription, ...] = (
    # ---- Live Temperatures ----
    KospelSensorDescription(
        key="inlet_temperature",
        name="Inlet Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.inlet_temp,
    ),
    KospelSensorDescription(
        key="outlet_temperature",
        name="Outlet Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.outlet_temp,
    ),
    KospelSensorDescription(
        key="current_setpoint",
        name="Active Setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:thermometer-lines",
        suggested_display_precision=1,
        value_fn=lambda d: d.current_setpoint,
    ),

    # ---- Flow / Power ----
    KospelSensorDescription(
        key="flow_rate",
        name="Flow Rate",
        native_unit_of_measurement="l/min",
        icon="mdi:water-pump",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.flow_rate,
    ),
    KospelSensorDescription(
        key="power_kw",
        name="Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.power_kw,
    ),
    KospelSensorDescription(
        key="selected_power_kw",
        name="Selected Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        icon="mdi:lightning-bolt",
        suggested_display_precision=0,
        value_fn=lambda d: d.selected_power_kw,
    ),
    KospelSensorDescription(
        key="heating_stage",
        name="Heating Stage",
        icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.heating_stage,
    ),

    # ---- Energy Statistics ----
    KospelSensorDescription(
        key="energy_today",
        name="Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda d: d.energy_today_kwh,
    ),
    KospelSensorDescription(
        key="energy_yesterday",
        name="Energy Yesterday",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.energy_yesterday_kwh,
    ),
    KospelSensorDescription(
        key="energy_week",
        name="Energy This Week",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda d: d.energy_week_kwh,
    ),
    KospelSensorDescription(
        key="energy_month",
        name="Energy This Month",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda d: d.energy_month_kwh,
    ),
    KospelSensorDescription(
        key="energy_year",
        name="Energy This Year",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda d: d.energy_year_kwh,
    ),
    KospelSensorDescription(
        key="energy_lifetime",
        name="Energy Lifetime",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        icon="mdi:counter",
        value_fn=lambda d: d.energy_lifetime_kwh,
    ),

    # ---- Water Statistics ----
    KospelSensorDescription(
        key="water_today",
        name="Water Today",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: d.water_today_l,
    ),
    KospelSensorDescription(
        key="water_yesterday",
        name="Water Yesterday",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.water_yesterday_l,
    ),
    KospelSensorDescription(
        key="water_week",
        name="Water This Week",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: d.water_week_l,
    ),
    KospelSensorDescription(
        key="water_month",
        name="Water This Month",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: d.water_month_l,
    ),
    KospelSensorDescription(
        key="water_year",
        name="Water This Year",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: d.water_year_l,
    ),
    KospelSensorDescription(
        key="water_lifetime",
        name="Water Lifetime",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        icon="mdi:counter",
        value_fn=lambda d: d.water_lifetime_l,
    ),

    # ---- Diagnostics ----
    KospelSensorDescription(
        key="device_datetime",
        name="Device Date/Time",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_format_datetime,
    ),
    KospelSensorDescription(
        key="active_errors",
        name="Active Errors",
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_format_errors,
    ),
    KospelSensorDescription(
        key="active_warnings",
        name="Active Warnings",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_format_warnings,
    ),
    KospelSensorDescription(
        key="status_word",
        name="Status Word",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: f"0x{d.status_word:08X}",
    ),
    KospelSensorDescription(
        key="max_allowed_temperature",
        name="Max Allowed Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.max_allowed_temp,
    ),
    KospelSensorDescription(
        key="rated_power",
        name="Rated Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.rated_power_w,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KospelDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(KospelSensor(coordinator, desc) for desc in SENSORS)


class KospelSensor(KospelEntity, SensorEntity):
    entity_description: KospelSensorDescription

    def __init__(
        self,
        coordinator: KospelDataCoordinator,
        description: KospelSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
