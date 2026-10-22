"""Shared fixtures. Tests do not call Open-Meteo or AWS."""

import json
from pathlib import Path

import pytest

from weather_etl.config import Location, Settings

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "open_meteo_berlin.json"


@pytest.fixture
def berlin() -> Location:
    return Location("berlin", 52.52, 13.41)


@pytest.fixture
def forecast_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def local_settings(tmp_path: Path, berlin: Location) -> Settings:
    return Settings(
        storage_backend="local",
        local_data_dir=tmp_path,
        s3_bucket=None,
        aws_region="us-east-1",
        raw_prefix="raw/weather",
        curated_prefix="curated/weather",
        quality_prefix="quality/weather",
        forecast_days=1,
        locations=(berlin,),
        open_meteo_base_url="https://api.open-meteo.com/v1/forecast",
        request_timeout_seconds=5.0,
        quality_max_null_ratio=0.05,
        log_level="INFO",
    )
