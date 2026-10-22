from collections.abc import Sequence
from datetime import date

import pandas as pd

from tests.constants import INGEST_DATE, RUN_AT
from weather_etl.config import Location
from weather_etl.quality import QualityReport, run_checks
from weather_etl.transform import payload_to_frame


def _locations() -> tuple[Location, ...]:
    return (Location("berlin", 52.52, 13.41),)


def _report(
    frame: pd.DataFrame,
    *,
    ingest_date: date = INGEST_DATE,
    forecast_days: int = 1,
    locations: Sequence[Location] | None = None,
    max_null_ratio: float = 0.05,
) -> QualityReport:
    return run_checks(
        frame,
        ingest_date=ingest_date,
        forecast_days=forecast_days,
        locations=tuple(locations or _locations()),
        max_null_ratio=max_null_ratio,
    )


def _failed(frame: pd.DataFrame, name: str, **kwargs: object) -> None:
    report = _report(frame, **kwargs)  # type: ignore[arg-type]
    assert report.passed is False
    failed = {check.name for check in report.checks if not check.passed}
    assert name in failed


def test_clean_frame_passes(forecast_payload: dict) -> None:
    report = _report(payload_to_frame("berlin", forecast_payload, RUN_AT))
    assert report.passed is True
    assert report.row_count == 4
    assert {check.name for check in report.checks} >= {
        "schema",
        "not_null",
        "null_ratio",
        "ranges",
        "duplicates",
        "freshness",
        "locations",
        "coordinates",
        "data_source",
        "row_count",
    }


def test_null_location_fails(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    frame.loc[0, "location_id"] = pd.NA
    _failed(frame, "not_null")


def test_null_ratio_fails_when_metrics_are_sparse(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    frame.loc[0, "temperature_c"] = pd.NA
    _failed(frame, "null_ratio")


def test_temperature_bounds(forecast_payload: dict) -> None:
    low = payload_to_frame("berlin", forecast_payload, RUN_AT)
    low["temperature_c"] = -80.0
    assert _report(low).passed is True
    low.loc[0, "temperature_c"] = -80.1
    _failed(low, "ranges")

    high = payload_to_frame("berlin", forecast_payload, RUN_AT)
    high["temperature_c"] = 60.0
    assert _report(high).passed is True
    high.loc[0, "temperature_c"] = 60.1
    _failed(high, "ranges")


def test_humidity_and_precipitation_bounds(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    frame.loc[0, "relative_humidity_pct"] = 101
    _failed(frame, "ranges")

    rain = payload_to_frame("berlin", forecast_payload, RUN_AT)
    rain.loc[0, "precipitation_mm"] = -0.1
    _failed(rain, "ranges")


def test_duplicate_observation_fails(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    _failed(pd.concat([frame, frame], ignore_index=True), "duplicates")


def test_freshness_requires_the_ingest_date(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    report = _report(frame, ingest_date=INGEST_DATE.replace(year=2020))
    assert report.passed is False
    freshness = next(check for check in report.checks if check.name == "freshness")
    assert freshness.passed is False


def test_missing_location_fails(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    _failed(
        frame,
        "locations",
        locations=(Location("berlin", 52.52, 13.41), Location("oslo", 59.91, 10.75)),
    )


def test_coordinate_mismatch_fails(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT)
    frame["latitude"] = 10.0
    _failed(frame, "coordinates")


def test_missing_column_fails_schema_and_skips_later_checks(forecast_payload: dict) -> None:
    frame = payload_to_frame("berlin", forecast_payload, RUN_AT).drop(columns=["temperature_c"])
    report = _report(frame)
    assert report.passed is False
    names = [check.name for check in report.checks]
    assert names == ["schema", "row_count"]
