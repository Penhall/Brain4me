from __future__ import annotations

from difflib import SequenceMatcher
import re
import sqlite3
import unicodedata


SPACE_RE = re.compile(r"\s+")
SEPARATOR_RE = re.compile(r"[_\-.]+")
LOW_SIGNAL_TOKENS = {
    "usar",
    "como",
    "banco",
    "inicial",
    "base",
    "sistema",
    "mvp",
    "no",
    "na",
    "de",
    "do",
    "da",
}


def normalize_entity_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    separated = SEPARATOR_RE.sub(" ", ascii_only)
    collapsed = SPACE_RE.sub(" ", separated)
    return collapsed.strip().lower()


def _meaningful_tokens(name: str) -> set[str]:
    return {
        token
        for token in normalize_entity_name(name).split()
        if len(token) >= 3 and token not in LOW_SIGNAL_TOKENS
    }


def _name_similarity(candidate_name: str, target_name: str) -> float:
    candidate_tokens = _meaningful_tokens(candidate_name)
    target_tokens = _meaningful_tokens(target_name)
    if candidate_tokens and target_tokens:
        token_similarity = len(candidate_tokens & target_tokens) / len(candidate_tokens | target_tokens)
    else:
        token_similarity = 0.0
    string_similarity = SequenceMatcher(
        None,
        normalize_entity_name(candidate_name),
        normalize_entity_name(target_name),
    ).ratio()
    return max(token_similarity, string_similarity * 0.6 + token_similarity * 0.4)


def _fetch_context_terms(conn: sqlite3.Connection, entity_id: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT e.canonical_name
        FROM relations r
        JOIN entities e ON e.id = r.object_entity_id
        WHERE r.subject_entity_id = ?
          AND r.predicate IN ('afeta', 'resolve')
        """,
        (entity_id,),
    ).fetchall()
    terms: set[str] = set()
    for row in rows:
        terms.update(_meaningful_tokens(str(row["canonical_name"])))
    return terms


def _context_similarity(candidate_terms: set[str], current_context_hints: list[str] | None) -> float:
    if not current_context_hints:
        return 0.0
    current_terms: set[str] = set()
    for hint in current_context_hints:
        current_terms.update(_meaningful_tokens(hint))
    if not candidate_terms or not current_terms:
        return 0.0
    return len(candidate_terms & current_terms) / len(candidate_terms | current_terms)


def find_linked_entity_id(
    conn: sqlite3.Connection,
    *,
    compartment_id: str,
    entity_type: str,
    canonical_name: str,
    context_hints: list[str] | None = None,
) -> str | None:
    normalized_target = normalize_entity_name(canonical_name)
    rows = conn.execute(
        """
        SELECT id, canonical_name
        FROM entities
        WHERE compartment_id = ? AND entity_type = ?
        """,
        (compartment_id, entity_type),
    ).fetchall()

    for row in rows:
        candidate_name = str(row["canonical_name"])
        if normalize_entity_name(candidate_name) == normalized_target:
            return str(row["id"])
        similarity = _name_similarity(candidate_name, canonical_name)
        context_similarity = _context_similarity(_fetch_context_terms(conn, str(row["id"])), context_hints)
        if similarity >= 0.72 or (similarity >= 0.48 and context_similarity >= 0.99):
            return str(row["id"])
    return None
