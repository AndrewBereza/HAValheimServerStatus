# Valheim Server Status for Home Assistant

Polls the `status.json` that a Valheim server publishes (the `STATUS_HTTP=true`
option of [lloesche/valheim-server-docker](https://github.com/lloesche/valheim-server-docker))
and turns it into Home Assistant sensors and dashboard cards.

## Server side

Run the container with the status web server on, and expose its port:

```yaml
environment:
  SERVER_PUBLIC: "true"      # required: private servers don't answer Steam queries
  STATUS_HTTP: "true"
  STATUS_HTTP_PORT: "80"
ports:
  - "8080:80/tcp"            # status.json at http://<host>:8080/status.json
```

Any other server that serves the same JSON shape works too.

## Install

**HACS:**

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AndrewBereza&repository=HAValheimServerStatus&category=integration)

Or by hand: **HACS > ⋮ > Custom repositories**, add
`https://github.com/AndrewBereza/HAValheimServerStatus` with type *Integration*,
then download *Valheim Server Status* and restart Home Assistant.

**Manual:** copy `custom_components/valheim_status` into your
`<config>/custom_components/` folder and restart.

Then go to **Settings > Devices & services > Add integration > Valheim Server Status**
and enter:

| Field | Default | Notes |
|---|---|---|
| Name | `Valheim` | Used for the device and entity ids (`sensor.valheim_players`). |
| Host | | Hostname or IP of the status web server. |
| Status HTTP port | `80` | The status server port, not the game port 2456. |
| Path | `/status.json` | |
| Use HTTPS / Verify SSL | off / on | For a reverse proxy in front of the server. |

The form checks the URL answers with a Valheim `status.json` before saving.
Add the integration once per server.

**Options** (Configure button): poll interval (default 30 s; the container
rewrites the file every 10 s) and the age after which `status.json` is
considered stale (default 120 s).

## Entities

| Entity | Example | Meaning |
|---|---|---|
| `binary_sensor.valheim_online` | on | Server answered its last Steam query and the file is fresh. Turns **off** (never unavailable) when the game server is down, the file is stale, or the host is unreachable. Attributes: `error`, `stale`. |
| `sensor.valheim_players` | 3 | Players connected (0 when offline). Long-term statistics enabled. Attributes: `players` (list with `duration_minutes`), `longest_session_minutes`. |
| `sensor.valheim_server_name` | My server | |
| `sensor.valheim_version` | 0.217.46 | Game version from `keywords`. |
| `binary_sensor.valheim_password_protected` | on | Diagnostic. |
| `sensor.valheim_last_status_update` | timestamp | Diagnostic. |
| `sensor.valheim_status_error` | none | Diagnostic: the query error string, e.g. `timeout('timed out')`. |
| `binary_sensor.valheim_vac_enabled`, `sensor.valheim_game_port`, `sensor.valheim_steam_id` | | Diagnostic, disabled by default. |

Valheim's Steam query does not return player names (they come back empty), so
the player list shows session lengths only.

## Dashboard widgets

Paste either file from `dashboards/` via **Edit dashboard > Add card > Manual**:

- `valheim_card.yaml`: full card with online tile, offline warning, glance row,
  "who's online" table with session lengths, 24 h player history and server details.
- `valheim_compact_card.yaml`: two tiles side by side (online, player count).

If you named the integration something other than `Valheim`, replace `valheim_`
in the entity ids with your name's slug.

## Development

```bash
pip install pytest-homeassistant-custom-component
pytest
```
