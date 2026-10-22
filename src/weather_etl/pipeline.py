"""Extract, transform, and publish one ingest date."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from weather_etl import clock
from weather_etl.config import Settings
from weather_etl.exceptions import TransformError
from weather_etl.extract import FetchFn, run_extract
from weather_etl.paths import curated_parquet_key, quality_report_key, raw_partition_prefix
from weather_etl.quality import DataQualityError, QualityReport, run_checks
from weather_etl.storage import Storage
from weather_etl.transform import forecasts_to_frame, frame_to_parquet_bytes

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransformResult:
    ingest_date: date
    curated_key: str
    curated_uri: str
    quality_report_key: str
    row_count: int
    quality_passed: bool
    raw_keys: tuple[str, ...]


def run_pipeline(
    settings: Settings,
    storage: Storage,
    ingest_date: date | None = None,
    ingested_at: datetime | None = None,
    fetch: FetchFn | None = None,
) -> TransformResult:
    landing_date = ingest_date or clock.today_utc()
    extracted = run_extract(settings, storage, landing_date, fetch=fetch)
    return run_transform(
        settings,
        storage,
        extracted.ingest_date,
        ingested_at=ingested_at,
        raw_keys=extracted.raw_keys,
    )


def run_transform(
    settings: Settings,
    storage: Storage,
    ingest_date: date,
    ingested_at: datetime | None = None,
    raw_keys: tuple[str, ...] | None = None,
) -> TransformResult:
    stamped_at = ingested_at or clock.now_utc()
    keys = list(raw_keys) if raw_keys is not None else _raw_keys(storage, settings, ingest_date)
    if not keys:
        prefix = raw_partition_prefix(settings.raw_prefix, ingest_date)
        raise TransformError(f"no raw JSON found under {prefix}")
    records = [_read_raw(storage, key) for key in keys]
    frame = forecasts_to_frame(records, stamped_at)
    report = run_checks(
        frame,
        ingest_date=ingest_date,
        forecast_days=settings.forecast_days,
        locations=settings.locations,
        max_null_ratio=settings.quality_max_null_ratio,
    )
    report_key = quality_report_key(settings.quality_prefix, ingest_date)
    _write_report(storage, report_key, report)
    if not report.passed:
        failed = ", ".join(check.name for check in report.checks if not check.passed)
        logger.error("data quality checks failed: %s", failed)
        raise DataQualityError(f"data quality checks failed: {failed}", report)
    curated_key = curated_parquet_key(settings.curated_prefix, ingest_date)
    curated_uri = storage.write_bytes(curated_key, frame_to_parquet_bytes(frame))
    logger.info("wrote curated parquet key=%s rows=%s", curated_key, len(frame))
    return TransformResult(
        ingest_date=ingest_date,
        curated_key=curated_key,
        curated_uri=curated_uri,
        quality_report_key=report_key,
        row_count=int(len(frame)),
        quality_passed=True,
        raw_keys=tuple(keys),
    )


def _raw_keys(storage: Storage, settings: Settings, ingest_date: date) -> list[str]:
    prefix = raw_partition_prefix(settings.raw_prefix, ingest_date)
    return [key for key in storage.list_keys(prefix) if key.endswith(".json")]


def _read_raw(storage: Storage, key: str) -> tuple[str, dict]:
    location_id = _location_id_from_key(key)
    try:
        payload = json.loads(storage.read_bytes(key).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise TransformError(f"raw object is not JSON: {key}") from exc
    if not isinstance(payload, dict):
        raise TransformError(f"raw object is not a JSON object: {key}")
    return location_id, payload


def _location_id_from_key(key: str) -> str:
    for part in Path(key).parts:
        if part.startswith("location_id="):
            location_id = part.split("=", 1)[1]
            if location_id:
                return location_id
    raise TransformError(f"could not read location_id from key {key}")


def _write_report(storage: Storage, key: str, report: QualityReport) -> None:
    body = (json.dumps(report.to_dict(), indent=2) + "\n").encode("utf-8")
    storage.write_bytes(key, body)
    logger.info("wrote quality report key=%s passed=%s", key, report.passed)


# Re-exported for callers that want the extract result type next to the pipeline.
__all__ = ["TransformResult", "run_extract", "run_pipeline", "run_transform"]
