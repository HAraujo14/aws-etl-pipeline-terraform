import json

import boto3
import pytest
from moto import mock_aws

from tests.constants import INGEST_DATE
from weather_etl.exceptions import ConfigError
from weather_etl.lambda_handler import handler
from weather_etl.transform import parquet_bytes_to_frame


def _aws(monkeypatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


def _patch_fetch(monkeypatch, forecast_payload: dict) -> None:
    monkeypatch.setattr(
        "weather_etl.extract.fetch_json",
        lambda url, timeout: forecast_payload,
    )


def test_handler_runs_against_s3(monkeypatch, forecast_payload) -> None:
    _aws(monkeypatch)
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "weather-test")
    monkeypatch.setenv(
        "LOCATIONS_JSON",
        json.dumps([{"location_id": "berlin", "latitude": 52.52, "longitude": 13.41}]),
    )
    _patch_fetch(monkeypatch, forecast_payload)
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="weather-test")
        result = handler({"action": "run", "ingest_date": INGEST_DATE.isoformat()}, None)
        assert result["action"] == "run"
        assert result["quality_passed"] is True
        assert result["row_count"] == 4
        body = client.get_object(Bucket="weather-test", Key=result["curated_key"])["Body"].read()
        assert len(parquet_bytes_to_frame(body)) == 4


def test_handler_extract_then_transform(monkeypatch, forecast_payload) -> None:
    _aws(monkeypatch)
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "weather-test")
    monkeypatch.setenv(
        "LOCATIONS_JSON",
        json.dumps([{"location_id": "berlin", "latitude": 52.52, "longitude": 13.41}]),
    )
    _patch_fetch(monkeypatch, forecast_payload)
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="weather-test")
        extracted = handler({"action": "extract", "ingest_date": "2026-10-22"}, None)
        assert extracted["raw_keys"]
        transformed = handler(
            {"action": "transform", "ingest_date": extracted["ingest_date"]},
            None,
        )
        assert transformed["action"] == "transform"
        assert transformed["quality_passed"] is True
        assert transformed["row_count"] == 4


def test_handler_rejects_unknown_action(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv(
        "LOCATIONS_JSON",
        json.dumps([{"location_id": "berlin", "latitude": 52.52, "longitude": 13.41}]),
    )
    with pytest.raises(ConfigError, match="unknown action"):
        handler({"action": "drop-table"}, None)
