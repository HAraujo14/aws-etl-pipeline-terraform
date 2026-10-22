import json

from weather_etl.cli import main


def test_cli_local_run(monkeypatch, tmp_path, forecast_payload, capsys) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv(
        "LOCATIONS_JSON",
        json.dumps([{"location_id": "berlin", "latitude": 52.52, "longitude": 13.41}]),
    )
    monkeypatch.setattr("weather_etl.extract.fetch_json", lambda url, timeout: forecast_payload)
    code = main(["run", "--date", "2026-10-22", "--backend", "local"])
    captured = capsys.readouterr()
    assert code == 0
    assert "quality=passed" in captured.out
    assert "rows=4" in captured.out
    assert (tmp_path / "curated/weather/ingest_date=2026-10-22/observations.parquet").is_file()


def test_cli_returns_nonzero_when_quality_fails(
    monkeypatch, tmp_path, forecast_payload, capsys
) -> None:
    payload = json.loads(json.dumps(forecast_payload))
    payload["hourly"]["wind_speed_10m"] = [-5, -5, -5, -5]
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv(
        "LOCATIONS_JSON",
        json.dumps([{"location_id": "berlin", "latitude": 52.52, "longitude": 13.41}]),
    )
    monkeypatch.setattr("weather_etl.extract.fetch_json", lambda url, timeout: payload)
    code = main(["run", "--date", "2026-10-22"])
    captured = capsys.readouterr()
    assert code == 1
    assert "quality=failed" in captured.out
    assert not (tmp_path / "curated").exists()
