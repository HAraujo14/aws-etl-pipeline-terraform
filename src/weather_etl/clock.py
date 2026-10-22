"""Clock helpers so tests can freeze 'now' without patching datetime."""

from datetime import UTC, date, datetime


def now_utc() -> datetime:
    return datetime.now(UTC)


def today_utc() -> date:
    return now_utc().date()
