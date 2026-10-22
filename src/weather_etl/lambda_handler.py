"""AWS Lambda entrypoint. One function serves extract, transform, and full runs."""

from __future__ import annotations

import logging
from typing import Any

from weather_etl.config import Settings, parse_ingest_date
from weather_etl.exceptions import ConfigError
from weather_etl.extract import run_extract
from weather_etl.logging_config import configure_logging
from weather_etl.pipeline import TransformResult, run_pipeline, run_transform
from weather_etl.storage import build_storage

logger = logging.getLogger(__name__)


def handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    """Dispatch on event['action']. The default action runs extract and transform."""
    incoming = event or {}
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    action = incoming.get("action") or "run"
    ingest_date = parse_ingest_date(incoming.get("ingest_date"))
    logger.info("lambda action=%s ingest_date=%s", action, ingest_date.isoformat())
    storage = build_storage(settings)
    if action == "extract":
        extracted = run_extract(settings, storage, ingest_date)
        return {
            "action": "extract",
            "ingest_date": extracted.ingest_date.isoformat(),
            "raw_keys": list(extracted.raw_keys),
        }
    if action == "transform":
        transformed = run_transform(settings, storage, ingest_date)
        return _transform_payload("transform", transformed)
    if action == "run":
        completed = run_pipeline(settings, storage, ingest_date=ingest_date)
        return _transform_payload("run", completed)
    raise ConfigError(f"unknown action: {action}")


def _transform_payload(action: str, result: TransformResult) -> dict[str, Any]:
    return {
        "action": action,
        "ingest_date": result.ingest_date.isoformat(),
        "curated_key": result.curated_key,
        "quality_report_key": result.quality_report_key,
        "row_count": result.row_count,
        "quality_passed": result.quality_passed,
        "raw_keys": list(result.raw_keys),
    }
