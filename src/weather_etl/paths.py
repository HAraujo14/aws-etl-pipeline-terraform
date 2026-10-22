"""Hive-style object keys for the raw, curated, and quality prefixes."""

from datetime import date


def raw_object_key(prefix: str, ingest_date: date, location_id: str) -> str:
    return (
        f"{prefix}/ingest_date={ingest_date.isoformat()}"
        f"/location_id={location_id}/forecast.json"
    )


def curated_parquet_key(prefix: str, ingest_date: date) -> str:
    return f"{prefix}/ingest_date={ingest_date.isoformat()}/observations.parquet"


def quality_report_key(prefix: str, ingest_date: date) -> str:
    return f"{prefix}/ingest_date={ingest_date.isoformat()}/quality_report.json"


def raw_partition_prefix(prefix: str, ingest_date: date) -> str:
    return f"{prefix}/ingest_date={ingest_date.isoformat()}/"
