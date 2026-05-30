from __future__ import annotations

from collections import Counter
import math
import re


STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "que",
    "um",
    "uma",
}
VECTOR_SIZE = 48


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z0-9_]+", text.lower())
        if len(token) >= 3 and token not in STOPWORDS
    ]


def compute_text_embedding(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    tokens = _tokenize(text)
    if not tokens:
        return vector

    counts = Counter(tokens)
    total = float(sum(counts.values())) or 1.0
    for token, count in counts.items():
        vector[hash(token) % VECTOR_SIZE] += count / total
    return vector


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def semantic_similarity(a: str, b: str) -> float:
    return round(_cosine_similarity(compute_text_embedding(a), compute_text_embedding(b)), 4)
