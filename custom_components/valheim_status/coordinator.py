"""Data coordinator that polls status.json from a Valheim server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PATH,
    CONF_SCAN_INTERVAL,
    CONF_STALE_AFTER,
    DEFAULT_PATH,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STALE_AFTER,
    DOMAIN,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

type ValheimConfigEntry = ConfigEntry[ValheimStatusCoordinator]


class CannotConnect(Exception):
    """status.json could not be fetched."""


class InvalidResponse(Exception):
    """The response was not a valheim-server-docker status.json."""


@dataclass(slots=True)
class ValheimPlayer:
    """One entry of the players list."""

    name: str
    score: int
    duration: float


@dataclass(slots=True)
class ValheimStatus:
    """Parsed status.json."""

    last_status_update: datetime | None
    error: str | None
    server_name: str | None = None
    player_count: int | None = None
    password_protected: bool | None = None
    vac_enabled: bool | None = None
    port: int | None = None
    steam_id: int | None = None
    keywords: str | None = None
    game_id: int | None = None
    server_type: str | None = None
    platform: str | None = None
    players: list[ValheimPlayer] = field(default_factory=list)
    stale: bool = False

    @property
    def online(self) -> bool:
        """Server answered the last Steam query and the file is fresh."""
        return self.error is None and not self.stale

    @property
    def version(self) -> str | None:
        """Game version, taken from keywords like '0.217.46@0.9.4'."""
        if not self.keywords:
            return None
        return self.keywords.split("@", 1)[0] or None


def build_url(data: dict[str, Any]) -> str:
    """Build the status.json URL from config entry data."""
    scheme = "https" if data.get(CONF_SSL) else "http"
    path = data.get(CONF_PATH) or DEFAULT_PATH
    if not path.startswith("/"):
        path = f"/{path}"
    host = data[CONF_HOST]
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"  # bare IPv6 address
    return f"{scheme}://{host}:{data[CONF_PORT]}{path}"


def parse_status(raw: Any, stale_after: int = DEFAULT_STALE_AFTER) -> ValheimStatus:
    """Turn the decoded JSON into a ValheimStatus."""
    if not isinstance(raw, dict) or "last_status_update" not in raw:
        raise InvalidResponse("missing last_status_update")

    updated = dt_util.parse_datetime(str(raw["last_status_update"]))
    error = raw.get("error")
    players = [
        ValheimPlayer(
            name=str(p.get("name") or ""),
            score=int(p.get("score") or 0),
            duration=float(p.get("duration") or 0.0),
        )
        for p in raw.get("players") or []
        if isinstance(p, dict)
    ]
    player_count = raw.get("player_count")
    if player_count is None and error is None:
        player_count = len(players)

    stale = updated is None or (
        dt_util.utcnow() - updated > timedelta(seconds=stale_after)
    )

    return ValheimStatus(
        last_status_update=updated,
        error=None if error is None else str(error),
        server_name=raw.get("server_name"),
        player_count=player_count,
        password_protected=raw.get("password_protected"),
        vac_enabled=raw.get("vac_enabled"),
        port=raw.get("port"),
        steam_id=raw.get("steam_id"),
        keywords=raw.get("keywords"),
        game_id=raw.get("game_id"),
        server_type=raw.get("server_type"),
        platform=raw.get("platform"),
        players=players,
        stale=stale,
    )


async def fetch_status(
    session: aiohttp.ClientSession, url: str, stale_after: int = DEFAULT_STALE_AFTER
) -> ValheimStatus:
    """Download and parse status.json."""
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT.total_seconds()):
            resp = await session.get(url)
            resp.raise_for_status()
            # busybox httpd serves .json as application/octet-stream on some
            # images, so don't insist on a JSON content type.
            raw = await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise CannotConnect(f"{url}: {err}") from err
    except ValueError as err:
        raise InvalidResponse(f"{url} is not JSON: {err}") from err
    return parse_status(raw, stale_after)


class ValheimStatusCoordinator(DataUpdateCoordinator[ValheimStatus]):
    """Polls status.json on an interval."""

    config_entry: ValheimConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ValheimConfigEntry) -> None:
        """Set up the coordinator from a config entry."""
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.data[CONF_HOST]}",
            update_interval=timedelta(seconds=interval),
        )
        self.url = build_url(entry.data)
        self.stale_after: int = entry.options.get(CONF_STALE_AFTER, DEFAULT_STALE_AFTER)
        self._session = async_get_clientsession(
            hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True)
        )

    async def _async_update_data(self) -> ValheimStatus:
        try:
            return await fetch_status(self._session, self.url, self.stale_after)
        except (CannotConnect, InvalidResponse) as err:
            raise UpdateFailed(str(err)) from err
