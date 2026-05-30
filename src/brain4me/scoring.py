from __future__ import annotations

from dataclasses import dataclass


DEFAULT_SOURCE_RELIABILITY = {
    "personal": 0.9,
    "external": 0.6,
    "inferred": 0.4,
}


@dataclass(frozen=True, slots=True)
class ScoreInputs:
    recency: float = 1.0
    frequency: float = 1.0
    confidence: float = 1.0
    source_reliability: float = 0.9


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def normalize_frequency(raw_frequency: int) -> float:
    if raw_frequency <= 1:
        return 1.0
    return clamp(0.5 + (raw_frequency / 10.0))


def compute_score(inputs: ScoreInputs) -> float:
    recency = clamp(inputs.recency)
    frequency = clamp(inputs.frequency)
    confidence = clamp(inputs.confidence)
    source_reliability = clamp(inputs.source_reliability)
    score = (
        (0.25 * recency)
        + (0.2 * frequency)
        + (0.25 * confidence)
        + (0.3 * source_reliability)
    )
    return round(clamp(score), 4)


def default_source_reliability(source_origin_type: str) -> float:
    return DEFAULT_SOURCE_RELIABILITY.get(source_origin_type, 0.5)
