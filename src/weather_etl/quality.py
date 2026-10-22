"""Data quality checks that gate publication of the curated Parquet file."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

import pandas as pd

from weather_etl.config import Location
from weather_etl.exceptions import WeatherEtlError
from weather_etl.schema import (
    CRITICAL_NOT_NULL,
    CURATED_COLUMNS,
    DATA_SOURCE,
    METRIC_COLUMNS,
    RANGES,
)


class DataQualityError(WeatherEtlError):
    """Raised when checks fail. The curated file is not written."""

    def __init__(self, message: str, report: QualityReport) -> None:
        super().__init__(message)
        self.report = report


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    details: str


@dataclass(frozen=True)
class QualityReport:
    checks: tuple[CheckResult, ...]
    row_count: int

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "row_count": self.row_count,
            "checks": [
                {"name": check.name, "passed": check.passed, "details": check.details}
                for check in self.checks
            ],
        }


def run_checks(
    frame: pd.DataFrame,
    *,
    ingest_date: date,
    forecast_days: int,
    locations: tuple[Location, ...] | list[Location],
    max_null_ratio: float,
) -> QualityReport:
    """Run every check. Column-dependent checks are skipped when the schema is wrong."""
    row_count = int(len(frame))
    schema_result = _check_schema(frame)
    checks: list[CheckResult] = [schema_result, _check_row_count(row_count)]
    if schema_result.passed:
        checks.extend(
            [
                _check_not_null(frame),
                _check_null_ratio(frame, max_null_ratio),
                _check_ranges(frame),
                _check_duplicates(frame),
                _check_freshness(frame, ingest_date, forecast_days),
                _check_locations(frame, locations),
                _check_coordinates(frame, locations),
                _check_data_source(frame),
            ]
        )
    return QualityReport(checks=tuple(checks), row_count=row_count)


def _check_schema(frame: pd.DataFrame) -> CheckResult:
    actual = list(frame.columns)
    missing = [column for column in CURATED_COLUMNS if column not in actual]
    extra = [column for column in actual if column not in CURATED_COLUMNS]
    problems: list[str] = []
    if missing:
        problems.append("missing " + ", ".join(missing))
    if extra:
        problems.append("unexpected " + ", ".join(extra))
    if not problems:
        problems.extend(_dtype_problems(frame))
    if problems:
        return CheckResult("schema", False, "; ".join(problems))
    return CheckResult("schema", True, "columns and dtypes match the curated schema")


def _dtype_problems(frame: pd.DataFrame) -> list[str]:
    problems: list[str] = []
    for column in ("observation_time", "ingested_at"):
        series = frame[column]
        tz = getattr(series.dtype, "tz", None)
        if not pd.api.types.is_datetime64_any_dtype(series) or tz is None:
            problems.append(f"{column} is not a timezone-aware datetime")
    for column in ("location_id", "data_source"):
        if not pd.api.types.is_string_dtype(frame[column]):
            problems.append(f"{column} is not a string")
    for column in (
        "latitude",
        "longitude",
        "elevation_m",
        "temperature_c",
        "relative_humidity_pct",
        "precipitation_mm",
        "wind_speed_kmh",
    ):
        if not pd.api.types.is_float_dtype(frame[column]):
            problems.append(f"{column} is not a float")
    return problems


def _check_row_count(row_count: int) -> CheckResult:
    if row_count < 1:
        return CheckResult("row_count", False, "frame has no rows")
    return CheckResult("row_count", True, f"{row_count} row(s)")


def _check_not_null(frame: pd.DataFrame) -> CheckResult:
    problems = []
    for column in CRITICAL_NOT_NULL:
        count = int(frame[column].isna().sum())
        if count:
            problems.append(f"{column}: {count} null(s)")
    if problems:
        return CheckResult("not_null", False, "; ".join(problems))
    return CheckResult("not_null", True, "critical columns have no nulls")


def _check_null_ratio(frame: pd.DataFrame, max_null_ratio: float) -> CheckResult:
    if len(frame) == 0:
        return CheckResult("null_ratio", False, "frame has no rows")
    problems = []
    for column in METRIC_COLUMNS:
        ratio = float(frame[column].isna().mean())
        if ratio > max_null_ratio:
            problems.append(f"{column}: null ratio {ratio:.2%} exceeds {max_null_ratio:.2%}")
    if problems:
        return CheckResult("null_ratio", False, "; ".join(problems))
    return CheckResult(
        "null_ratio",
        True,
        f"metric null ratios are at or below {max_null_ratio:.2%}",
    )


def _check_ranges(frame: pd.DataFrame) -> CheckResult:
    problems = []
    for column, (low, high) in RANGES.items():
        series = frame[column].dropna()
        if series.empty:
            continue
        count = int((~series.between(low, high)).sum())
        if count:
            problems.append(f"{column}: {count} value(s) outside [{low}, {high}]")
    if problems:
        return CheckResult("ranges", False, "; ".join(problems))
    return CheckResult("ranges", True, "non-null values are inside the expected ranges")


def _check_duplicates(frame: pd.DataFrame) -> CheckResult:
    duplicate_rows = int(frame.duplicated(subset=["location_id", "observation_time"]).sum())
    if duplicate_rows:
        return CheckResult(
            "duplicates",
            False,
            f"{duplicate_rows} duplicate location_id/observation_time row(s)",
        )
    return CheckResult("duplicates", True, "location_id and observation_time are unique")


def _check_freshness(frame: pd.DataFrame, ingest_date: date, forecast_days: int) -> CheckResult:
    """The batch is fresh when it covers the ingest date and stays in the forecast window."""
    observed = frame["observation_time"].dropna()
    if observed.empty:
        return CheckResult("freshness", False, "no observation timestamps")
    start = pd.Timestamp(datetime.combine(ingest_date, time.min, tzinfo=UTC))
    end = start + timedelta(days=forecast_days)
    earliest = pd.Timestamp(observed.min())
    latest = pd.Timestamp(observed.max())
    covers_ingest_date = bool(((observed >= start) & (observed < end)).any())
    inside_window = bool(earliest >= start and latest <= end)
    details = (
        f"observations {earliest.isoformat()} to {latest.isoformat()} "
        f"for window [{start.isoformat()}, {end.isoformat()}]"
    )
    if covers_ingest_date and inside_window:
        return CheckResult("freshness", True, details)
    return CheckResult("freshness", False, details)


def _check_locations(
    frame: pd.DataFrame, locations: tuple[Location, ...] | list[Location]
) -> CheckResult:
    expected = {location.location_id for location in locations}
    actual = set(frame["location_id"].dropna().astype(str))
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    problems = []
    if missing:
        problems.append("missing " + ", ".join(missing))
    if unexpected:
        problems.append("unexpected " + ", ".join(unexpected))
    if problems:
        return CheckResult("locations", False, "; ".join(problems))
    return CheckResult("locations", True, "every configured location is present")


def _check_coordinates(
    frame: pd.DataFrame, locations: tuple[Location, ...] | list[Location]
) -> CheckResult:
    problems = []
    for location in locations:
        subset = frame.loc[
            frame["location_id"] == location.location_id, ["latitude", "longitude"]
        ].dropna()
        if subset.empty:
            continue
        lat_off = float((subset["latitude"] - location.latitude).abs().max())
        lon_off = float((subset["longitude"] - location.longitude).abs().max())
        if lat_off > 1 or lon_off > 1:
            problems.append(
                f"{location.location_id}: differs from config by "
                f"lat {lat_off:.3f} deg, lon {lon_off:.3f} deg"
            )
    if problems:
        return CheckResult("coordinates", False, "; ".join(problems))
    return CheckResult("coordinates", True, "coordinates stay within 1 degree of the config")


def _check_data_source(frame: pd.DataFrame) -> CheckResult:
    values = set(frame["data_source"].dropna().astype(str))
    if values != {DATA_SOURCE}:
        return CheckResult(
            "data_source", False, f"expected {DATA_SOURCE!r}, found {sorted(values)}"
        )
    return CheckResult("data_source", True, f"data_source is {DATA_SOURCE}")
