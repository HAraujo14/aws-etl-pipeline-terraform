import json
from dataclasses import replace
from datetime import date

import boto3
import pytest
from moto import mock_aws

from tests.constants import INGEST_DATE
from weather_etl.config import Location
from weather_etl.exceptions import ConfigError
from weather_etl.paths import curated_parquet_key
from weather_etl.pipeline import run_pipeline
from weather_etl.quality import DataQualityError
from weather_etl.storage import LocalStorage, S3Storage
from weather_etl.transform import parquet_bytes_to_frame


def _fetch(payload: dict):
    def fetch(url: str, timeout: float) -> dict:
        return payload

    return fetch


def test_local_pipeline_writes_raw_parquet_and_report(local_settings, forecast_payload) -> None:
    storage = LocalStorage(local_settings.local_data_dir)
    result = run_pipeline(
        local_settings,
        storage,
        ingest_date=INGEST_DATE,
        fetch=_fetch(forecast_payload),
    )
    assert result.quality_passed is True
    assert result.row_count == 4
    raw = json.loads(storage.read_bytes(result.raw_keys[0]))
    assert raw["hourly"]["temperature_2m"][0] == 10.1
    frame = parquet_bytes_to_frame(storage.read_bytes(result.curated_key))
    assert "ingest_date" not in frame.columns
    assert frame["location_id"].tolist() == ["berlin"] * 4
    report = json.loads(storage.read_bytes(result.quality_report_key))
    assert report["passed"] is True
    assert result.curated_key == curated_parquet_key("curated/weather", INGEST_DATE)


def test_quality_failure_does_not_publish_curated(local_settings, forecast_payload) -> None:
    payload = json.loads(json.dumps(forecast_payload))
    payload["hourly"]["temperature_2m"] = [200, 200, 200, 200]
    storage = LocalStorage(local_settings.local_data_dir)
    with pytest.raises(DataQualityError, match="ranges"):
        run_pipeline(
            local_settings,
            storage,
            ingest_date=INGEST_DATE,
            fetch=_fetch(payload),
        )
    assert not (local_settings.local_data_dir / "curated").exists()
    report = json.loads(
        (
            local_settings.local_data_dir
            / "quality/weather/ingest_date=2026-10-22/quality_report.json"
        ).read_text(encoding="utf-8")
    )
    assert report["passed"] is False
    assert any(check["name"] == "ranges" and check["passed"] is False for check in report["checks"])


def test_s3_pipeline_with_moto(local_settings, forecast_payload) -> None:
    settings = replace(local_settings, storage_backend="s3", s3_bucket="weather-test")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="weather-test")
        storage = S3Storage("weather-test", client)
        result = run_pipeline(
            settings,
            storage,
            ingest_date=INGEST_DATE,
            fetch=_fetch(forecast_payload),
        )
        assert result.curated_uri == f"s3://weather-test/{result.curated_key}"
        saved = client.get_object(Bucket="weather-test", Key=result.curated_key)
        frame = parquet_bytes_to_frame(saved["Body"].read())
        assert len(frame) == 4


def test_two_locations_stay_distinct(local_settings, forecast_payload, berlin) -> None:
    oslo_payload = json.loads(json.dumps(forecast_payload))
    oslo_payload["latitude"] = 59.91
    oslo_payload["longitude"] = 10.75
    settings = replace(
        local_settings,
        locations=(berlin, Location("oslo", 59.91, 10.75)),
    )

    def fetch(url: str, timeout: float) -> dict:
        if "latitude=59.9100" in url:
            return oslo_payload
        return forecast_payload

    storage = LocalStorage(settings.local_data_dir)
    result = run_pipeline(settings, storage, ingest_date=date(2026, 10, 22), fetch=fetch)
    frame = parquet_bytes_to_frame(storage.read_bytes(result.curated_key))
    assert set(frame["location_id"]) == {"berlin", "oslo"}
    assert result.row_count == 8
    assert len(result.raw_keys) == 2


def test_s3_settings_without_bucket_are_rejected(local_settings) -> None:
    with pytest.raises(ConfigError, match="S3_BUCKET"):
        replace(local_settings, storage_backend="s3", s3_bucket=None)
