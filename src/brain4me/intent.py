from __future__ import annotations

import unicodedata


INTENT_KEYWORDS = {
    "decision_support": (
        "devo",
        "decidir",
        "decisao",
        "decisao devo",
        "melhor caminho",
        "qual opcao",
        "qual escolha",
        "recomenda",
    ),
    "risk_analysis": (
        "risco",
        "riscos",
        "perigo",
        "impacto",
        "trade-off",
        "tradeoff",
        "conflito",
    ),
    "explanation": (
        "por que",
        "porque",
        "explique",
        "explica",
        "como",
        "justifique",
    ),
    "fact_lookup": (
        "o que",
        "qual",
        "quais",
        "quem",
        "quando",
        "onde",
        "sei sobre",
    ),
    "exploration": (
        "explore",
        "explorar",
        "conexoes",
        "conexoes",
        "mapeie",
        "descobrir",
        "investigue",
    ),
}

INTENT_PRIORITY = (
    "decision_support",
    "risk_analysis",
    "exploration",
    "explanation",
    "fact_lookup",
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii").lower().strip()


def classify_intent(question: str) -> str:
    normalized = _normalize(question)
    if not normalized:
        return "exploration"

    scores = {intent: 0 for intent in INTENT_KEYWORDS}
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                scores[intent] += 1

    if "?" not in normalized and scores["exploration"] == 0 and scores["fact_lookup"] == 0:
        return "exploration"

    best_intent = max(INTENT_PRIORITY, key=lambda intent: (scores[intent], -INTENT_PRIORITY.index(intent)))
    if scores[best_intent] == 0:
        if normalized.startswith(("por que", "porque", "como")):
            return "explanation"
        if normalized.startswith(("o que", "qual", "quais", "quem", "quando", "onde")):
            return "fact_lookup"
        return "exploration"
    return best_intent
