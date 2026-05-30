from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


_METRICS: dict[str, Any] = {}


def log_metric(name: str, value: float) -> None:
    _METRICS[name] = round(float(value), 4)
    _METRICS[f"{name}_at"] = datetime.now(UTC).isoformat()


def set_metric(name: str, value: Any) -> None:
    _METRICS[name] = value
    _METRICS[f"{name}_at"] = datetime.now(UTC).isoformat()


def get_metrics_snapshot() -> dict[str, Any]:
    return dict(_METRICS)


def reset_metrics() -> None:
    _METRICS.clear()
