"""Fixtures for Valheim Server Status tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let HA load custom_components/ from this repo."""
    yield


def online_status(players: int = 2, age: int = 5) -> dict:
    """A status.json from a running server."""
    ts = (datetime.now(UTC) - timedelta(seconds=age)).isoformat()
    return {
        "last_status_update": ts,
        "error": None,
        "server_name": "My Docker based server",
        "server_type": "d",
        "platform": "l",
        "player_count": players,
        "password_protected": True,
        "vac_enabled": False,
        "port": 2456,
        "steam_id": 90143789459088380,
        "keywords": "0.217.46@0.9.4",
        "game_id": 892970,
        "players": [
            {"name": "", "score": 0, "duration": 600.0 * (i + 1)} for i in range(players)
        ],
    }


def offline_status() -> dict:
    """A status.json while the game server is not answering queries."""
    return {
        "last_status_update": datetime.now(UTC).isoformat(),
        "error": "timeout('timed out')",
    }
