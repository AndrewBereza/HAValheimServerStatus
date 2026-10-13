"""Binary sensors for Valheim Server Status."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ValheimConfigEntry, ValheimStatus, ValheimStatusCoordinator
from .entity import ValheimEntity


@dataclass(frozen=True, kw_only=True)
class ValheimBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Valheim binary sensor."""

    value_fn: Callable[[ValheimStatus], bool | None]
    attrs_fn: Callable[[ValheimStatus], dict[str, Any]] | None = None


BINARY_SENSORS: tuple[ValheimBinarySensorDescription, ...] = (
    ValheimBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda s: s.online,
        attrs_fn=lambda s: {"error": s.error, "stale": s.stale},
    ),
    ValheimBinarySensorDescription(
        key="password_protected",
        translation_key="password_protected",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.password_protected,
    ),
    ValheimBinarySensorDescription(
        key="vac_enabled",
        translation_key="vac_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.vac_enabled,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ValheimConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(ValheimBinarySensor(coordinator, d) for d in BINARY_SENSORS)


class ValheimBinarySensor(ValheimEntity, BinarySensorEntity):
    """A Valheim binary sensor."""

    entity_description: ValheimBinarySensorDescription

    def __init__(
        self,
        coordinator: ValheimStatusCoordinator,
        description: ValheimBinarySensorDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """The online sensor stays available so it can report 'off'."""
        if self.entity_description.key == "online":
            return True
        return super().available

    @property
    def is_on(self) -> bool | None:
        """Return the state."""
        if not self.coordinator.last_update_success or self.coordinator.data is None:
            # status.json itself is unreachable: the host is down.
            return False if self.entity_description.key == "online" else None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        fn = self.entity_description.attrs_fn
        if fn is None:
            return None
        if not self.coordinator.last_update_success or self.coordinator.data is None:
            return {"error": str(self.coordinator.last_exception), "stale": True}
        return fn(self.coordinator.data)
