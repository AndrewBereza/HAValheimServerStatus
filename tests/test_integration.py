"""End-to-end tests: config flow, setup and entity states."""

from __future__ import annotations

from datetime import timedelta

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.valheim_status.const import CONF_PATH, DOMAIN

from .conftest import offline_status, online_status

URL = "http://valheim.local:8080/status.json"
USER_INPUT = {
    CONF_NAME: "Valheim",
    CONF_HOST: "valheim.local",
    CONF_PORT: 8080,
    CONF_PATH: "/status.json",
    CONF_SSL: False,
    CONF_VERIFY_SSL: True,
}


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Valheim", data=USER_INPUT, unique_id=URL)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow_success(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, json=online_status())
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Valheim"
    assert result["data"][CONF_HOST] == "valheim.local"


async def test_config_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, status=404)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_not_valheim(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, json={"hello": "world"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "invalid_response"}


async def test_sensors_online(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, json=online_status(players=2))
    await _setup(hass)

    assert hass.states.get("binary_sensor.valheim_online").state == STATE_ON
    players = hass.states.get("sensor.valheim_players")
    assert players.state == "2"
    assert players.attributes["players"][1]["duration_minutes"] == 20.0
    assert players.attributes["longest_session_minutes"] == 20.0
    assert hass.states.get("sensor.valheim_server_name").state == "My Docker based server"
    assert hass.states.get("sensor.valheim_version").state == "0.217.46"
    assert hass.states.get("binary_sensor.valheim_password_protected").state == STATE_ON
    assert hass.states.get("sensor.valheim_status_error").state == "none"
    assert hass.states.get("sensor.valheim_last_status_update").state not in (
        STATE_UNAVAILABLE,
        "unknown",
    )


async def test_game_server_down(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, json=offline_status())
    await _setup(hass)

    online = hass.states.get("binary_sensor.valheim_online")
    assert online.state == STATE_OFF
    assert online.attributes["error"] == "timeout('timed out')"
    assert hass.states.get("sensor.valheim_players").state == "0"
    assert hass.states.get("sensor.valheim_status_error").state == "timeout('timed out')"


async def test_stale_status_is_offline(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, json=online_status(age=600))
    await _setup(hass)
    online = hass.states.get("binary_sensor.valheim_online")
    assert online.state == STATE_OFF
    assert online.attributes["stale"] is True


async def test_host_unreachable_after_setup(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, json=online_status())
    await _setup(hass)
    assert hass.states.get("binary_sensor.valheim_online").state == STATE_ON

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=500)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()

    # Online keeps reporting so automations can react to "off".
    assert hass.states.get("binary_sensor.valheim_online").state == STATE_OFF
    assert hass.states.get("sensor.valheim_players").state == STATE_UNAVAILABLE


async def test_options_flow(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(URL, json=online_status())
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 60, "stale_after": 300}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {"scan_interval": 60, "stale_after": 300}
    assert entry.runtime_data.update_interval == timedelta(seconds=60)


async def test_unload(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(URL, json=online_status())
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.NOT_LOADED
