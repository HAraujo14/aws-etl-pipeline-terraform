"""Logging setup shared by the CLI and the Lambda handler."""

import logging


def configure_logging(level: str = "INFO") -> None:
    numeric = getattr(logging, level.upper(), None)
    if not isinstance(numeric, int):
        numeric = logging.INFO
    root = logging.getLogger()
    root.setLevel(numeric)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(handler)
