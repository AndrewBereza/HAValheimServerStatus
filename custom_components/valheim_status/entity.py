"""Base entity for Valheim Server Status."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ValheimStatusCoordinator


class ValheimEntity(CoordinatorEntity[ValheimStatusCoordinator]):
    """Groups all entities of one server under a single device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ValheimStatusCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        data = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Iron Gate",
            model="Valheim dedicated server",
            sw_version=data.version if data else None,
            configuration_url=coordinator.url,
            entry_type=DeviceEntryType.SERVICE,
        )
