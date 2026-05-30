from __future__ import annotations

import re
import unicodedata


TERM_NORMALIZATION = {
    "manter": "usar",
    "adotar": "usar",
    "escolher": "usar",
    "priorizar": "usar",
    "utilizar": "usar",
    "persistencia": "persistencia",
    "banco": "persistencia",
}

NOISE_WORDS = {"no", "na", "do", "da", "de", "o", "a", "para", "com", "um", "uma"}


def _ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def normalize_decision_text(text: str) -> str:
    cleaned = _ascii(text).lower()
    cleaned = re.sub(r"[^a-z0-9\s_-]+", " ", cleaned)
    tokens = [token for token in cleaned.split() if token]
    normalized_tokens: list[str] = []
    for token in tokens:
        canonical = TERM_NORMALIZATION.get(token, token)
        if canonical in NOISE_WORDS:
            continue
        normalized_tokens.append(canonical)
    return " ".join(normalized_tokens)
