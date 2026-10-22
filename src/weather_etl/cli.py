"""Command line interface for a local or S3 run."""

from __future__ import annotations

import argparse
import logging

from weather_etl import clock
from weather_etl.config import Settings, parse_ingest_date
from weather_etl.exceptions import WeatherEtlError
from weather_etl.extract import run_extract
from weather_etl.logging_config import configure_logging
from weather_etl.pipeline import run_pipeline, run_transform
from weather_etl.quality import DataQualityError
from weather_etl.storage import build_storage

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="weather-etl",
        description="Ingest Open-Meteo forecasts, check quality, and write curated Parquet.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("run", "Extract, transform, and publish one ingest date"),
        ("extract", "Fetch forecasts and write raw JSON only"),
        ("transform", "Transform raw JSON already stored for one ingest date"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--date", help="Ingest date YYYY-MM-DD. Defaults to today UTC.")
        command.add_argument("--backend", choices=("local", "s3"))
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.backend:
            settings = _with_backend(settings, args.backend)
        configure_logging(settings.log_level)
        ingest_date = parse_ingest_date(args.date) if args.date else clock.today_utc()
        storage = build_storage(settings)
        if args.command == "extract":
            extracted = run_extract(settings, storage, ingest_date)
            print(
                f"ingest_date={extracted.ingest_date.isoformat()} "
                f"raw_objects={len(extracted.raw_keys)}"
            )
            return 0
        if args.command == "transform":
            result = run_transform(settings, storage, ingest_date)
        else:
            result = run_pipeline(settings, storage, ingest_date=ingest_date)
    except DataQualityError as exc:
        logger.error("%s", exc)
        print(f"quality=failed {exc}")
        return 1
    except WeatherEtlError as exc:
        logger.error("%s", exc)
        print(f"error={exc}")
        return 1
    print(
        f"ingest_date={result.ingest_date.isoformat()} rows={result.row_count} "
        f"curated={result.curated_uri} quality=passed"
    )
    return 0


def _with_backend(settings: Settings, backend: str) -> Settings:
    from dataclasses import replace

    return replace(settings, storage_backend=backend)
