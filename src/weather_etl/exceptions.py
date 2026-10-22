"""Errors raised by the weather ETL pipeline."""


class WeatherEtlError(Exception):
    """Base error for expected pipeline failures."""


class ConfigError(WeatherEtlError):
    """Raised when environment or caller configuration is invalid."""


class ExtractError(WeatherEtlError):
    """Raised when a forecast cannot be fetched or stored."""


class TransformError(WeatherEtlError):
    """Raised when raw JSON cannot be turned into the curated frame."""


class StorageError(WeatherEtlError):
    """Raised when an object cannot be read or written."""
