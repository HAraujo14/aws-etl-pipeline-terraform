"""Runtime configuration loaded from the environment."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from weather_etl.clock import today_utc
from weather_etl.exceptions import ConfigError

LOCATION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


@dataclass(frozen=True)
class Location:
    location_id: str
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not LOCATION_ID_PATTERN.fullmatch(self.location_id):
            raise ConfigError(
                "location_id must match ^[a-z][a-z0-9_]{0,62}$ " f"(got {self.location_id!r})"
            )
        if not -90 <= self.latitude <= 90:
            raise ConfigError(f"latitude out of range for {self.location_id}")
        if not -180 <= self.longitude <= 180:
            raise ConfigError(f"longitude out of range for {self.location_id}")


DEFAULT_LOCATIONS = (
    Location("berlin", 52.52, 13.41),
    Location("sao_paulo", -23.55, -46.63),
    Location("new_york", 40.71, -74.01),
)


@dataclass(frozen=True)
class Settings:
    storage_backend: str
    local_data_dir: Path
    s3_bucket: str | None
    aws_region: str
    raw_prefix: str
    curated_prefix: str
    quality_prefix: str
    forecast_days: int
    locations: tuple[Location, ...]
    open_meteo_base_url: str
    request_timeout_seconds: float
    quality_max_null_ratio: float
    log_level: str

    def __post_init__(self) -> None:
        if self.storage_backend not in {"local", "s3"}:
            raise ConfigError("STORAGE_BACKEND must be 'local' or 's3'")
        if self.storage_backend == "s3" and not self.s3_bucket:
            raise ConfigError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        if not 1 <= self.forecast_days <= 16:
            raise ConfigError("FORECAST_DAYS must be between 1 and 16")
        if not 0 <= self.quality_max_null_ratio <= 1:
            raise ConfigError("QUALITY_MAX_NULL_RATIO must be between 0 and 1")
        if self.request_timeout_seconds <= 0:
            raise ConfigError("REQUEST_TIMEOUT_SECONDS must be positive")
        if not self.locations:
            raise ConfigError("at least one location is required")
        for prefix in (self.raw_prefix, self.curated_prefix, self.quality_prefix):
            _validate_prefix(prefix)
        if not self.open_meteo_base_url.startswith("https://"):
            raise ConfigError("OPEN_METEO_BASE_URL must start with https://")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        return cls(
            storage_backend=env.get("STORAGE_BACKEND", "local"),
            local_data_dir=Path(env.get("LOCAL_DATA_DIR", "data")),
            s3_bucket=env.get("S3_BUCKET") or None,
            aws_region=env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION") or "us-east-1",
            raw_prefix=env.get("RAW_PREFIX", "raw/weather"),
            curated_prefix=env.get("CURATED_PREFIX", "curated/weather"),
            quality_prefix=env.get("QUALITY_PREFIX", "quality/weather"),
            forecast_days=_env_int(env, "FORECAST_DAYS", 1),
            locations=_parse_locations(env.get("LOCATIONS_JSON")),
            open_meteo_base_url=env.get(
                "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast"
            ),
            request_timeout_seconds=_env_float(env, "REQUEST_TIMEOUT_SECONDS", 30.0),
            quality_max_null_ratio=_env_float(env, "QUALITY_MAX_NULL_RATIO", 0.05),
            log_level=env.get("LOG_LEVEL", "INFO"),
        )


def parse_ingest_date(value: object) -> date:
    """Return today's UTC date when the caller does not pass one."""
    if value is None or value == "":
        return today_utc()
    if not isinstance(value, str):
        raise ConfigError("ingest_date must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"invalid ingest_date: {value}") from exc


def _validate_prefix(prefix: str) -> None:
    parts = prefix.split("/")
    if not prefix or prefix.startswith("/") or prefix.endswith("/") or ".." in parts:
        raise ConfigError(f"invalid storage prefix: {prefix}")


def _env_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc


def _env_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc


def _parse_locations(raw: str | None) -> tuple[Location, ...]:
    if not raw:
        return DEFAULT_LOCATIONS
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("LOCATIONS_JSON is not valid JSON") from exc
    if not isinstance(parsed, list):
        raise ConfigError("LOCATIONS_JSON must be a JSON list")
    locations: list[Location] = []
    for item in parsed:
        if not isinstance(item, dict):
            raise ConfigError("each LOCATIONS_JSON entry must be an object")
        try:
            locations.append(
                Location(
                    location_id=str(item["location_id"]),
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"invalid location entry: {item}") from exc
    return tuple(locations)
