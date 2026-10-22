from __future__ import annotations

import email.message
import json
import urllib.error
import urllib.parse

import pytest

from weather_etl.config import Location
from weather_etl.exceptions import ExtractError
from weather_etl.extract import build_forecast_url, fetch_json


class _Body:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _Body:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://api.open-meteo.com/v1/forecast",
        code,
        "error",
        email.message.Message(),
        None,
    )


def test_build_forecast_url_pins_units_and_timezone() -> None:
    url = build_forecast_url(
        "https://api.open-meteo.com/v1/forecast",
        Location("berlin", 52.52, 13.41),
        1,
    )
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert params["latitude"] == ["52.5200"]
    assert params["longitude"] == ["13.4100"]
    assert params["timezone"] == ["UTC"]
    assert params["temperature_unit"] == ["celsius"]
    assert params["wind_speed_unit"] == ["kmh"]
    assert params["precipitation_unit"] == ["mm"]
    assert params["forecast_days"] == ["1"]
    assert params["hourly"] == ["temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"]


def test_fetch_json_returns_object() -> None:
    def opener(request: object, timeout: float) -> _Body:
        return _Body(b'{"latitude": 1}')

    assert fetch_json("https://example.test/forecast", 1, opener=opener) == {"latitude": 1}


def test_fetch_json_retries_server_errors(forecast_payload: dict) -> None:
    calls = {"count": 0}
    sleeps: list[float] = []

    def opener(request: object, timeout: float) -> _Body:
        calls["count"] += 1
        if calls["count"] < 3:
            raise _http_error(503)
        return _Body(json.dumps(forecast_payload).encode("utf-8"))

    payload = fetch_json(
        "https://example.test/forecast",
        1,
        sleeper=sleeps.append,
        opener=opener,
    )
    assert payload["latitude"] == forecast_payload["latitude"]
    assert calls["count"] == 3
    assert sleeps == [1, 2]


def test_fetch_json_does_not_retry_client_errors() -> None:
    sleeps: list[float] = []

    def opener(request: object, timeout: float) -> _Body:
        raise _http_error(400)

    with pytest.raises(ExtractError, match="HTTP 400"):
        fetch_json("https://example.test/forecast", 1, sleeper=sleeps.append, opener=opener)
    assert sleeps == []


def test_fetch_json_rejects_api_error_object() -> None:
    def opener(request: object, timeout: float) -> _Body:
        return _Body(b'{"error": true, "reason": "latitude out of range"}')

    with pytest.raises(ExtractError, match="latitude out of range"):
        fetch_json("https://example.test/forecast", 1, opener=opener)
