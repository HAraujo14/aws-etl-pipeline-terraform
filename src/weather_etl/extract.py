"""Fetch Open-Meteo forecasts and land the raw JSON response."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from weather_etl.config import Location, Settings
from weather_etl.exceptions import ExtractError
from weather_etl.paths import raw_object_key
from weather_etl.schema import HOURLY_FIELDS
from weather_etl.storage import Storage

logger = logging.getLogger(__name__)

USER_AGENT = "weather-etl-portfolio/0.1 (personal project; educational use)"
FetchFn = Callable[[str, float], dict[str, Any]]
Sleeper = Callable[[float], None]
Opener = Callable[..., Any]


@dataclass(frozen=True)
class ExtractResult:
    ingest_date: date
    raw_keys: tuple[str, ...]
    location_ids: tuple[str, ...]


def build_forecast_url(base_url: str, location: Location, forecast_days: int) -> str:
    params = {
        "latitude": f"{location.latitude:.4f}",
        "longitude": f"{location.longitude:.4f}",
        "hourly": ",".join(HOURLY_FIELDS),
        "forecast_days": str(forecast_days),
        "timezone": "UTC",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def fetch_json(
    url: str,
    timeout: float,
    attempts: int = 3,
    sleeper: Sleeper = time.sleep,
    opener: Opener = urllib.request.urlopen,
) -> dict[str, Any]:
    """GET a JSON object, retrying timeouts, network errors, 429, and 5xx."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _request_json(url, timeout, opener)
        except ExtractError:
            raise
        except urllib.error.HTTPError as exc:
            last_error = exc
            if 400 <= exc.code < 500 and exc.code != 429:
                raise ExtractError(f"Open-Meteo request failed with HTTP {exc.code}") from exc
            logger.warning("forecast request HTTP %s (attempt %s/%s)", exc.code, attempt, attempts)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("forecast request failed (attempt %s/%s): %s", attempt, attempts, exc)
        if attempt < attempts:
            sleeper(min(2 ** (attempt - 1), 4))
    raise ExtractError(f"failed to fetch forecast after {attempts} attempts: {last_error}") from (
        last_error
    )


def run_extract(
    settings: Settings,
    storage: Storage,
    ingest_date: date,
    fetch: FetchFn | None = None,
) -> ExtractResult:
    fetch_fn = fetch or fetch_json
    keys: list[str] = []
    for location in settings.locations:
        url = build_forecast_url(settings.open_meteo_base_url, location, settings.forecast_days)
        logger.info("fetching forecast location=%s", location.location_id)
        try:
            payload = fetch_fn(url, settings.request_timeout_seconds)
        except ExtractError:
            raise
        except Exception as exc:
            raise ExtractError(f"{location.location_id}: fetch failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise ExtractError(f"{location.location_id}: response was not a JSON object")
        key = raw_object_key(settings.raw_prefix, ingest_date, location.location_id)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        storage.write_bytes(key, body)
        keys.append(key)
        logger.info("wrote raw object key=%s", key)
    return ExtractResult(
        ingest_date=ingest_date,
        raw_keys=tuple(keys),
        location_ids=tuple(location.location_id for location in settings.locations),
    )


def _request_json(url: str, timeout: float, opener: Opener) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with opener(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ExtractError("Open-Meteo response was not a JSON object")
    if payload.get("error"):
        reason = payload.get("reason", "unknown error")
        raise ExtractError(f"Open-Meteo error: {reason}")
    return payload
