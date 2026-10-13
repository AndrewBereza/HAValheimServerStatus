"""Sensors for Valheim Server Status."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ValheimConfigEntry, ValheimStatus, ValheimStatusCoordinator
from .entity import ValheimEntity


def _players_attrs(s: ValheimStatus) -> dict[str, Any]:
    # Valheim's Steam query returns empty names and zero scores, so the useful
    # part is how long each connection has lasted.
    return {
        "players": [
            {
                "name": p.name or None,
                "score": p.score,
                "duration_minutes": round(p.duration / 60, 1),
            }
            for p in s.players
        ],
        "longest_session_minutes": (
            round(max(p.duration for p in s.players) / 60, 1) if s.players else 0
        ),
    }


@dataclass(frozen=True, kw_only=True)
class ValheimSensorDescription(SensorEntityDescription):
    """Describes a Valheim sensor."""

    value_fn: Callable[[ValheimStatus], str | int | datetime | None]
    attrs_fn: Callable[[ValheimStatus], dict[str, Any]] | None = None


SENSORS: tuple[ValheimSensorDescription, ...] = (
    ValheimSensorDescription(
        key="players",
        translation_key="players",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="players",
        value_fn=lambda s: (s.player_count or 0) if s.online else 0,
        attrs_fn=_players_attrs,
    ),
    ValheimSensorDescription(
        key="server_name",
        translation_key="server_name",
        value_fn=lambda s: s.server_name,
    ),
    ValheimSensorDescription(
        key="version",
        translation_key="version",
        value_fn=lambda s: s.version,
        attrs_fn=lambda s: {"keywords": s.keywords},
    ),
    ValheimSensorDescription(
        key="last_status_update",
        translation_key="last_status_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.last_status_update,
    ),
    ValheimSensorDescription(
        key="status_error",
        translation_key="status_error",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: (s.error or "none")[:255],
    ),
    ValheimSensorDescription(
        key="game_port",
        translation_key="game_port",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.port,
    ),
    ValheimSensorDescription(
        key="steam_id",
        translation_key="steam_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda s: str(s.steam_id) if s.steam_id is not None else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ValheimConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    async_add_entities(ValheimSensor(coordinator, d) for d in SENSORS)


class ValheimSensor(ValheimEntity, SensorEntity):
    """A Valheim sensor."""

    entity_description: ValheimSensorDescription

    def __init__(
        self,
        coordinator: ValheimStatusCoordinator,
        description: ValheimSensorDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | int | datetime | None:
        """Return the state."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        fn = self.entity_description.attrs_fn
        return fn(self.coordinator.data) if fn else None
