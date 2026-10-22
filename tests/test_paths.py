from datetime import date

from weather_etl.paths import curated_parquet_key, quality_report_key, raw_object_key


def test_keys_are_partitioned_by_ingest_date() -> None:
    day = date(2026, 10, 22)
    raw = raw_object_key("raw/weather", day, "berlin")
    curated = curated_parquet_key("curated/weather", day)
    report = quality_report_key("quality/weather", day)

    assert raw == "raw/weather/ingest_date=2026-10-22/location_id=berlin/forecast.json"
    assert curated == "curated/weather/ingest_date=2026-10-22/observations.parquet"
    assert report == "quality/weather/ingest_date=2026-10-22/quality_report.json"
    assert not report.startswith("curated/")
    assert curated.endswith(".parquet")
