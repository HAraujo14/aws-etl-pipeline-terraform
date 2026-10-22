import pytest

from weather_etl.config import Location, Settings
from weather_etl.exceptions import ConfigError


def test_from_env_uses_defaults_when_unset() -> None:
    settings = Settings.from_env({})
    assert settings.storage_backend == "local"
    assert settings.forecast_days == 1
    assert [location.location_id for location in settings.locations] == [
        "berlin",
        "sao_paulo",
        "new_york",
    ]
    assert settings.s3_bucket is None


def test_from_env_parses_locations_and_numbers() -> None:
    settings = Settings.from_env(
        {
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "example-bucket",
            "FORECAST_DAYS": "2",
            "QUALITY_MAX_NULL_RATIO": "0.1",
            "LOCATIONS_JSON": '[{"location_id":"lisbon","latitude":38.72,"longitude":-9.14}]',
        }
    )
    assert settings.s3_bucket == "example-bucket"
    assert settings.forecast_days == 2
    assert settings.locations == (Location("lisbon", 38.72, -9.14),)
    assert settings.quality_max_null_ratio == 0.1


def test_s3_backend_requires_a_bucket() -> None:
    with pytest.raises(ConfigError, match="S3_BUCKET"):
        Settings.from_env({"STORAGE_BACKEND": "s3"})


def test_rejects_invalid_locations_json() -> None:
    with pytest.raises(ConfigError, match="LOCATIONS_JSON"):
        Settings.from_env({"LOCATIONS_JSON": "not-json"})


def test_rejects_unsafe_location_ids() -> None:
    with pytest.raises(ConfigError, match="location_id"):
        Location("Berlin", 52.52, 13.41)
    with pytest.raises(ConfigError, match="location_id"):
        Location("../etc", 52.52, 13.41)


def test_rejects_prefix_traversal() -> None:
    with pytest.raises(ConfigError, match="prefix"):
        Settings.from_env({"RAW_PREFIX": "raw/../../secret"})
