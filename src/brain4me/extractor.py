from __future__ import annotations

import json
from dataclasses import replace
import re
from typing import Callable, Protocol
import unicodedata

from .llm_client import build_openai_compatible_provider_from_env
from .models import ExtractionPayload


ENTITY_LABEL_TO_TYPE = {
    "projeto": "Project",
    "problema": "Problem",
    "objetivo": "Objective",
    "decisao": "Decision",
    "conclusao": "Decision",
    "evidencia": "Evidence",
    "motivo": "Evidence",
    "justificativa": "Evidence",
    "alternativa": "Alternative",
    "risco": "Risk",
    "hipotese": "Hypothesis",
    "oportunidade": "Opportunity",
}
CONTEXT_ONLY_LABELS = {
    "conflito": ("conflict", "contradicts"),
    "excecao": ("exception", "exception_for"),
    "inferencia": ("inference", "infers"),
}
STRUCTURED_LINE_RE = re.compile(r"^(?P<label>[A-Za-zÀ-ÿ]+):\s*(?P<value>.+?)\s*$")
DECISION_PATTERN = re.compile(
    r"(?P<decision>[A-Z][A-Za-z0-9_-]+)\s+parece melhor que\s+(?P<alternative>[A-Z][A-Za-z0-9_-]+)\s+porque\s+(?P<reason>[^.]+)",
    re.IGNORECASE,
)
RISK_PATTERN = re.compile(r"\bo risco (?:e|é)\s+(?P<risk>[^.]+)", re.IGNORECASE)
OBJECTIVE_PATTERN = re.compile(r"\bo objetivo(?:\s+atual)?\s+(?:e|é)\s+(?P<objective>[^.]+)", re.IGNORECASE)
PROBLEM_PATTERN = re.compile(r"\bo problema(?:\s+imediato)?\s+(?:e|é)\s+(?P<problem>[^.]+)", re.IGNORECASE)
PROJECT_PATTERN = re.compile(r"\bvalidar rapido o\s+(?P<project>[A-Z][A-Za-z0-9_-]+)\b", re.IGNORECASE)
CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(?P<body>.*?)\s*```$", re.DOTALL)
TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


class MarkdownExtractor(Protocol):
    def extract(self, body: str) -> ExtractionPayload:
        ...


def _normalize_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", label)
    return normalized.encode("ascii", "ignore").decode("ascii").strip().lower()


def _parse_structured_lines(body: str) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    entity_items: list[tuple[str, str]] = []
    context_only_items: list[tuple[str, str, str]] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = STRUCTURED_LINE_RE.match(line)
        if not match:
            continue
        normalized_label = _normalize_label(match.group("label"))
        value = match.group("value").strip()
        entity_type = ENTITY_LABEL_TO_TYPE.get(normalized_label)
        if entity_type and value:
            entity_items.append((entity_type, value))
            continue
        context_metadata = CONTEXT_ONLY_LABELS.get(normalized_label)
        if context_metadata and value:
            context_only_items.append((context_metadata[0], context_metadata[1], value))
    return entity_items, context_only_items


def _parse_freeform_text(body: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    if objective_match := OBJECTIVE_PATTERN.search(body):
        items.append(("Objective", objective_match.group("objective").strip()))
    if problem_match := PROBLEM_PATTERN.search(body):
        items.append(("Problem", problem_match.group("problem").strip()))
    if project_match := PROJECT_PATTERN.search(body):
        items.append(("Project", project_match.group("project").strip()))
    if decision_match := DECISION_PATTERN.search(body):
        chosen = decision_match.group("decision").strip()
        alternative = decision_match.group("alternative").strip()
        reason = decision_match.group("reason").strip()
        items.extend(
            [
                ("Decision", f"{chosen} parece melhor que {alternative}"),
                ("Evidence", reason),
                ("Alternative", alternative),
            ]
        )
    if risk_match := RISK_PATTERN.search(body):
        items.append(("Risk", risk_match.group("risk").strip()))
    return items


class HeuristicMarkdownExtractor:
    def extract(self, body: str) -> ExtractionPayload:
        entity_items, context_only_items = _parse_structured_lines(body)
        if not entity_items:
            entity_items = _parse_freeform_text(body)
        return ExtractionPayload(entity_items=entity_items, context_only_items=context_only_items, method="heuristic")


def _extract_json_document(raw_payload: str) -> str:
    stripped = raw_payload.strip()
    if fenced_match := CODE_FENCE_RE.match(stripped):
        stripped = fenced_match.group("body").strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]
    raise ValueError("no JSON object found in extractor payload")


def _repair_json_document(document: str) -> str:
    repaired = document.replace("“", '"').replace("”", '"').replace("’", "'")
    repaired = TRAILING_COMMA_RE.sub(r"\1", repaired)
    return repaired


def parse_extraction_json_payload(raw_payload: str) -> ExtractionPayload:
    json_document = _extract_json_document(raw_payload)
    try:
        parsed = json.loads(json_document)
    except json.JSONDecodeError:
        parsed = json.loads(_repair_json_document(json_document))

    if not isinstance(parsed, dict):
        raise ValueError("extractor payload must be a JSON object")
    raw_entities = parsed.get("entities", [])
    raw_context = parsed.get("context", [])
    if not isinstance(raw_entities, list) or not isinstance(raw_context, list):
        raise ValueError("entities and context must be lists")

    entity_items = [
        (str(item.get("type", "")).strip(), str(item.get("name", "")).strip())
        for item in raw_entities
        if isinstance(item, dict) and str(item.get("type", "")).strip() and str(item.get("name", "")).strip()
    ]
    context_items = [
        (
            str(item.get("node_type", "")).strip(),
            str(item.get("predicate", "")).strip(),
            str(item.get("content", "")).strip(),
        )
        for item in raw_context
        if isinstance(item, dict)
        and str(item.get("node_type", "")).strip()
        and str(item.get("predicate", "")).strip()
        and str(item.get("content", "")).strip()
    ]
    return ExtractionPayload(entity_items=entity_items, context_only_items=context_items, method="llm_json")


class SpacyFallbackExtractor:
    def __init__(
        self,
        *,
        nlp: Callable[[str], object] | None = None,
        heuristic_extractor: MarkdownExtractor | None = None,
    ) -> None:
        self._nlp = nlp
        self.heuristic_extractor = heuristic_extractor

    def _load_nlp(self) -> Callable[[str], object] | None:
        if self._nlp is not None:
            return self._nlp
        try:
            import spacy
        except ImportError:
            return None
        try:
            self._nlp = spacy.load("pt_core_news_sm")
        except Exception:
            self._nlp = spacy.blank("pt")
        return self._nlp

    def extract(self, body: str) -> ExtractionPayload:
        warnings: list[str] = []
        entity_items = _parse_freeform_text(body)
        nlp = self._load_nlp()
        if nlp is None:
            warnings.append("spacy_unavailable")
        else:
            doc = nlp(body)
            for ent in getattr(doc, "ents", []):
                text = str(getattr(ent, "text", "")).strip()
                if text and getattr(ent, "label_", "") in {"ORG", "PRODUCT", "WORK_OF_ART"}:
                    entity_items.append(("Project", text))
        if not entity_items and self.heuristic_extractor is not None:
            payload = self.heuristic_extractor.extract(body)
            return replace(payload, method="spacy_fallback", warnings=[*warnings, *payload.warnings])
        return ExtractionPayload(entity_items=entity_items, context_only_items=[], method="spacy", warnings=warnings)


class LLMJsonExtractor:
    def __init__(self, *, response_provider: Callable[[str], str], fallback_extractor: MarkdownExtractor | None = None) -> None:
        self.response_provider = response_provider
        self.fallback_extractor = fallback_extractor or HeuristicMarkdownExtractor()

    def extract(self, body: str) -> ExtractionPayload:
        try:
            payload = parse_extraction_json_payload(self.response_provider(body))
            if payload.entity_items or payload.context_only_items:
                return payload
            raise ValueError("extractor payload did not contain usable entities or context")
        except Exception as exc:
            fallback_payload = self.fallback_extractor.extract(body)
            return replace(
                fallback_payload,
                method=f"{fallback_payload.method}_fallback",
                warnings=[*fallback_payload.warnings, f"llm_json_fallback: {exc}"],
            )


class AdaptiveMarkdownExtractor:
    def __init__(
        self,
        *,
        llm_extractor: MarkdownExtractor | None = None,
        spacy_extractor: MarkdownExtractor | None = None,
        heuristic_extractor: MarkdownExtractor | None = None,
    ) -> None:
        self.llm_extractor = llm_extractor
        self.spacy_extractor = spacy_extractor or SpacyFallbackExtractor()
        self.heuristic_extractor = heuristic_extractor or HeuristicMarkdownExtractor()

    def extract(self, body: str) -> ExtractionPayload:
        warnings: list[str] = []
        if self.llm_extractor is not None:
            payload = self.llm_extractor.extract(body)
            if payload.method == "llm_json":
                return payload
            warnings.extend(payload.warnings)

        structured_entities, structured_context = _parse_structured_lines(body)
        if structured_entities or structured_context:
            heuristic_payload = ExtractionPayload(
                entity_items=structured_entities,
                context_only_items=structured_context,
                method="heuristic",
            )
            return replace(heuristic_payload, warnings=[*warnings, *heuristic_payload.warnings])

        if self.spacy_extractor is not None:
            payload = self.spacy_extractor.extract(body)
            if payload.entity_items or payload.context_only_items:
                return replace(payload, warnings=[*warnings, *payload.warnings])
            warnings.extend(payload.warnings)
        heuristic_payload = self.heuristic_extractor.extract(body)
        return replace(heuristic_payload, warnings=[*warnings, *heuristic_payload.warnings])


def build_default_extractor() -> MarkdownExtractor:
    llm_provider = build_openai_compatible_provider_from_env()
    llm_extractor = LLMJsonExtractor(response_provider=llm_provider) if llm_provider is not None else None
    return AdaptiveMarkdownExtractor(llm_extractor=llm_extractor)
