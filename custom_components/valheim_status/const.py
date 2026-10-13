"""Constants for the Valheim Server Status integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "valheim_status"

CONF_PATH = "path"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_STALE_AFTER = "stale_after"

DEFAULT_NAME = "Valheim"
DEFAULT_PORT = 80
DEFAULT_PATH = "/status.json"
# The status updater in valheim-server-docker rewrites status.json every 10 s.
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 5
# status.json older than this is treated as "server offline": the updater
# inside the container has stopped, so the file is no longer trustworthy.
DEFAULT_STALE_AFTER = 120

REQUEST_TIMEOUT = timedelta(seconds=10)
