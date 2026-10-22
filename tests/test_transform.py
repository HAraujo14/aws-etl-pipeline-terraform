import copy

import pandas as pd
import pytest
from tests.constants import RUN_AT

from weather_etl.exceptions import TransformError
from weather_etl.schema import CURATED_COLUMNS
from weather_etl.transform import frame_to_parquet_bytes, parquet_bytes_to_frame, payload_to_frame


def test_payload_to_frame_uses_curated_names(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    assert list(frame.columns) == list(CURATED_COLUMNS)
    assert len(frame) == 4
    assert frame.loc[0, "location_id"] == "berlin"
    assert frame.loc[0, "temperature_c"] == pytest.approx(10.1)
    assert frame.loc[0, "data_source"] == "open-meteo"
    assert str(frame.loc[0, "observation_time"]) == "2026-10-22 00:00:00+00:00"
    assert "ingest_date" not in frame.columns


def test_payload_to_frame_rejects_unexpected_units(forecast_payload: dict) -> None:
    payload = copy.deepcopy(forecast_payload)
    payload["hourly_units"]["temperature_2m"] = "\u00b0F"
    with pytest.raises(TransformError, match="unexpected units"):
        payload_to_frame("berlin", payload, RUN_AT)


def test_payload_to_frame_rejects_ragged_arrays(forecast_payload: dict) -> None:
    payload = copy.deepcopy(forecast_payload)
    payload["hourly"]["precipitation"] = [0.0]
    with pytest.raises(TransformError, match="differ in length"):
        payload_to_frame("berlin", payload, RUN_AT)


def test_parquet_roundtrip_keeps_values(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    restored = parquet_bytes_to_frame(frame_to_parquet_bytes(frame))
    assert list(restored.columns) == list(CURATED_COLUMNS)
    assert restored["temperature_c"].tolist() == pytest.approx(frame["temperature_c"].tolist())
    assert restored["location_id"].tolist() == ["berlin", "berlin", "berlin", "berlin"]
    left = pd.to_datetime(frame["observation_time"], utc=True)
    right = pd.to_datetime(restored["observation_time"], utc=True)
    assert left.tolist() == right.tolist()
