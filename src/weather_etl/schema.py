"""Curated schema shared by the transform, quality checks, and Glue table."""

import pyarrow as pa

DATA_SOURCE = "open-meteo"

HOURLY_FIELDS: tuple[str, ...] = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
)

# Unit query parameters make this contract stable. The degree symbol is the
# character Open-Meteo returns for Celsius.
EXPECTED_UNITS: dict[str, str] = {
    "temperature_2m": "\u00b0C",
    "relative_humidity_2m": "%",
    "precipitation": "mm",
    "wind_speed_10m": "km/h",
}

CURATED_COLUMNS: tuple[str, ...] = (
    "observation_time",
    "location_id",
    "latitude",
    "longitude",
    "elevation_m",
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
    "data_source",
    "ingested_at",
)

FLOAT_COLUMNS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "elevation_m",
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
)

CRITICAL_NOT_NULL: tuple[str, ...] = (
    "observation_time",
    "location_id",
    "latitude",
    "longitude",
    "data_source",
    "ingested_at",
)

METRIC_COLUMNS: tuple[str, ...] = (
    "elevation_m",
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
)

# Inclusive bounds. They are wide enough for real weather and tight enough
# to reject corrupted values (a 200C temperature, negative rain, and so on).
RANGES: dict[str, tuple[float, float]] = {
    "temperature_c": (-80.0, 60.0),
    "relative_humidity_pct": (0.0, 100.0),
    "precipitation_mm": (0.0, 500.0),
    "wind_speed_kmh": (0.0, 400.0),
    "latitude": (-90.0, 90.0),
    "longitude": (-180.0, 180.0),
    "elevation_m": (-500.0, 9000.0),
}

CURATED_ARROW_SCHEMA = pa.schema(
    [
        pa.field("observation_time", pa.timestamp("us", tz="UTC")),
        pa.field("location_id", pa.string()),
        pa.field("latitude", pa.float64()),
        pa.field("longitude", pa.float64()),
        pa.field("elevation_m", pa.float64()),
        pa.field("temperature_c", pa.float64()),
        pa.field("relative_humidity_pct", pa.float64()),
        pa.field("precipitation_mm", pa.float64()),
        pa.field("wind_speed_kmh", pa.float64()),
        pa.field("data_source", pa.string()),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)
