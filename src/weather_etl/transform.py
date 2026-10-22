"""Normalize raw Open-Meteo JSON into the curated Parquet schema."""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import pyarrow.parquet as pq

from weather_etl.exceptions import TransformError
from weather_etl.schema import (
    CURATED_ARROW_SCHEMA,
    CURATED_COLUMNS,
    DATA_SOURCE,
    EXPECTED_UNITS,
    FLOAT_COLUMNS,
    HOURLY_FIELDS,
)


def payload_to_frame(location_id: str, payload: dict, ingested_at: datetime) -> pd.DataFrame:
    if not isinstance(payload, dict):
        raise TransformError(f"{location_id}: payload was not an object")
    if payload.get("error"):
        raise TransformError(f"{location_id}: Open-Meteo error: {payload.get('reason', 'unknown')}")
    _require_units(location_id, payload.get("hourly_units") or {})
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise TransformError(f"{location_id}: missing hourly object")
    _require_aligned_arrays(location_id, hourly)
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TransformError(f"{location_id}: latitude/longitude missing or invalid") from exc
    elevation = payload.get("elevation")
    frame = pd.DataFrame(
        {
            "observation_time": pd.to_datetime(hourly["time"], utc=True, errors="coerce"),
            "location_id": location_id,
            "latitude": latitude,
            "longitude": longitude,
            "elevation_m": pd.NA if elevation is None else elevation,
            "temperature_c": hourly["temperature_2m"],
            "relative_humidity_pct": hourly["relative_humidity_2m"],
            "precipitation_mm": hourly["precipitation"],
            "wind_speed_kmh": hourly["wind_speed_10m"],
            "data_source": DATA_SOURCE,
            "ingested_at": ingested_at,
        }
    )
    return cast_frame(frame)


def forecasts_to_frame(
    records: list[tuple[str, dict]],
    ingested_at: datetime,
) -> pd.DataFrame:
    if not records:
        raise TransformError("no forecast payloads to transform")
    frames = [
        payload_to_frame(location_id, payload, ingested_at) for location_id, payload in records
    ]
    return pd.concat(frames, ignore_index=True)


def cast_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in CURATED_COLUMNS if column not in frame.columns]
    if missing:
        raise TransformError(f"frame is missing columns: {', '.join(missing)}")
    out = frame.loc[:, list(CURATED_COLUMNS)].copy()
    out["observation_time"] = pd.to_datetime(out["observation_time"], utc=True, errors="coerce")
    out["ingested_at"] = pd.to_datetime(out["ingested_at"], utc=True, errors="coerce")
    # Floor to microseconds so the Parquet timestamp[us] schema does not reject ns values.
    out["observation_time"] = out["observation_time"].dt.floor("us")
    out["ingested_at"] = out["ingested_at"].dt.floor("us")
    out["location_id"] = out["location_id"].astype("string")
    out["data_source"] = out["data_source"].astype("string")
    for column in FLOAT_COLUMNS:
        # Open-Meteo sends some measures as JSON integers (humidity is the
        # usual one). The curated contract is float64, matching the Glue doubles.
        out[column] = pd.to_numeric(out[column], errors="coerce").astype("float64")
    return out


def frame_to_parquet_bytes(frame: pd.DataFrame) -> bytes:
    table = pa_table(frame)
    buffer = io.BytesIO()
    pq.write_table(table, buffer, compression="snappy")
    return buffer.getvalue()


def parquet_bytes_to_frame(data: bytes) -> pd.DataFrame:
    table = pq.read_table(io.BytesIO(data))
    return cast_frame(table.to_pandas())


def pa_table(frame: pd.DataFrame):
    import pyarrow as pa

    return pa.Table.from_pandas(
        cast_frame(frame), schema=CURATED_ARROW_SCHEMA, preserve_index=False
    )


def _require_units(location_id: str, units: dict) -> None:
    mismatches = [
        f"{field}: expected {expected!r}, got {units.get(field)!r}"
        for field, expected in EXPECTED_UNITS.items()
        if units.get(field) != expected
    ]
    if mismatches:
        raise TransformError(f"{location_id}: unexpected units: " + "; ".join(mismatches))


def _require_aligned_arrays(location_id: str, hourly: dict) -> None:
    lengths: dict[str, int] = {}
    for field in ("time", *HOURLY_FIELDS):
        values = hourly.get(field)
        if not isinstance(values, list):
            raise TransformError(f"{location_id}: hourly.{field} is not a list")
        lengths[field] = len(values)
    if len(set(lengths.values())) != 1:
        raise TransformError(f"{location_id}: hourly arrays differ in length: {lengths}")
    if lengths["time"] == 0:
        raise TransformError(f"{location_id}: hourly arrays are empty")
