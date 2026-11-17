"""Base entity for Kospel PPE4.M."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import KospelDataCoordinator


class KospelEntity(CoordinatorEntity[KospelDataCoordinator]):
    """Base class for Kospel PPE4.M entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: KospelDataCoordinator, key: str) -> None:
        super().__init__(coordinator)
        host = coordinator.client.host
        self._attr_unique_id = f"{DOMAIN}_{host}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        host = self.coordinator.client.host
        return DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=f"Kospel PPE4.M ({host})",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
