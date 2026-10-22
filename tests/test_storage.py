import boto3
import pytest
from moto import mock_aws

from weather_etl.exceptions import StorageError
from weather_etl.storage import LocalStorage, S3Storage


def test_local_storage_roundtrip_and_listing(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    uri = storage.write_bytes(
        "raw/weather/ingest_date=2026-10-22/location_id=berlin/forecast.json", b"{}"
    )
    assert uri.endswith("forecast.json")
    assert (
        storage.read_bytes("raw/weather/ingest_date=2026-10-22/location_id=berlin/forecast.json")
        == b"{}"
    )
    keys = storage.list_keys("raw/weather/ingest_date=2026-10-22/")
    assert keys == ["raw/weather/ingest_date=2026-10-22/location_id=berlin/forecast.json"]
    assert storage.list_keys("raw/weather/ingest_date=1999-01-01/") == []


def test_local_storage_rejects_path_traversal(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    with pytest.raises(StorageError):
        storage.write_bytes("../escape", b"nope")
    with pytest.raises(StorageError):
        storage.read_bytes("/etc/passwd")


def test_s3_storage_roundtrip() -> None:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="weather-test")
        storage = S3Storage("weather-test", client)
        uri = storage.write_bytes("raw/weather/file.json", b'{"ok": true}')
        assert uri == "s3://weather-test/raw/weather/file.json"
        assert storage.read_bytes("raw/weather/file.json") == b'{"ok": true}'
        assert storage.list_keys("raw/weather/") == ["raw/weather/file.json"]
