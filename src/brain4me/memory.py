from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any

from .patterns import normalize_decision_text
from .query_helpers import unique_preserve_order
from .storage import connect, get_or_create_compartment, initialize_database, new_uuid, utc_now


STOPWORDS = {"o", "a", "os", "as", "de", "do", "da", "e", "sobre", "que", "foi", "qual", "quais"}
SYSTEM_MEMORY_SLUG = "system-memory"
MIN_RELEVANT_MEMORY_SCORE = 0.35


def _keywords(question: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z0-9_-]+", question)
        if len(token) >= 4 and token.lower() not in STOPWORDS
    ]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _entry_value(entry: Any, key: str, default: Any = None) -> Any:
    try:
        value = entry[key]
    except Exception:
        value = getattr(entry, key, default)
    return default if value is None else value


def _accepted_rejected_counts(entry: Any) -> tuple[int, int]:
    frequency = int(_entry_value(entry, "frequency", 1))
    feedback_balance = int(_entry_value(entry, "feedback_balance", 0))
    accepted = max(0, (frequency + feedback_balance) // 2)
    rejected = max(0, frequency - accepted)
    return accepted, rejected


def _extract_decision_text(content: str) -> str:
    head = content.split("|", 1)[0].strip()
    if ":" in head:
        return head.split(":", 1)[1].strip()
    return head


def _build_pattern_content(entry: dict[str, Any]) -> str:
    accepted_count, rejected_count = _accepted_rejected_counts(entry)
    decision_text = str(entry["decision_text"])
    last_used_at = str(entry.get("last_used_at") or entry.get("created_at") or "")
    short_last_used = last_used_at[:10] if last_used_at else "desconhecido"

    if entry.get("is_unstable"):
        prefix = "Padrao instavel"
    elif rejected_count > accepted_count:
        prefix = "Padrao rejeitado"
    else:
        prefix = "Padrao aceito"

    return (
        f"{prefix}: {decision_text} | "
        f"aceitas={accepted_count} | "
        f"rejeitadas={rejected_count} | "
        f"ultima_ocorrencia={short_last_used}"
    )


def _recency_weight(entry: Any) -> float:
    now = datetime.now(UTC)
    dt = _parse_datetime(str(_entry_value(entry, "last_used_at", "") or _entry_value(entry, "created_at", "")))
    if dt is None:
        return 0.5
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    age_days = max((now - dt).days, 0)
    return _clamp(1 - (age_days / 180), 0.0, 1.0)


def compute_memory_score(entry) -> float:
    frequency = min(int(_entry_value(entry, "frequency", 1)) / 5, 1.0)
    confidence_score = _clamp(float(_entry_value(entry, "confidence_score", 0.5)), 0.0, 1.0)
    recency_weight = _recency_weight(entry)
    feedback_balance = _clamp(float(_entry_value(entry, "feedback_balance", 0)) / 5, -1.0, 1.0)

    score = (
        (frequency * 0.4) +
        (confidence_score * 0.3) +
        (recency_weight * 0.2) +
        (feedback_balance * 0.1)
    )

    if int(_entry_value(entry, "is_unstable", 0)):
        score *= 0.35

    return round(_clamp(score, 0.0, 1.0), 4)


def _memory_entries_from_input(memories: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in memories:
        if isinstance(item, str):
            decision_text = _extract_decision_text(item)
            accepted_match = re.search(r"aceitas=(\d+)", item)
            rejected_match = re.search(r"rejeitadas=(\d+)", item)
            accepted = int(accepted_match.group(1)) if accepted_match else (1 if "Padrao aceito" in item else 0)
            rejected = int(rejected_match.group(1)) if rejected_match else (1 if "Padrao rejeitado" in item else 0)
            normalized.append(
                {
                    "content": item,
                    "decision_text": decision_text,
                    "normalized_key": normalize_decision_text(decision_text),
                    "frequency": max(accepted + rejected, 1),
                    "feedback_balance": accepted - rejected,
                    "is_unstable": 1 if "instavel" in item.lower() else 0,
                }
            )
        else:
            normalized.append(
                {
                    "content": str(_entry_value(item, "content", "")),
                    "decision_text": str(_entry_value(item, "decision_text", _extract_decision_text(str(_entry_value(item, "content", ""))))),
                    "normalized_key": str(_entry_value(item, "normalized_key", "")),
                    "frequency": int(_entry_value(item, "frequency", 1)),
                    "feedback_balance": int(_entry_value(item, "feedback_balance", 0)),
                    "is_unstable": int(_entry_value(item, "is_unstable", 0)),
                }
            )
    return normalized


def apply_feedback_penalty(decision: str, memories) -> float:
    decision_key = normalize_decision_text(decision)
    relevant = [
        memory
        for memory in _memory_entries_from_input(memories)
        if memory.get("normalized_key") == decision_key
    ]
    if not relevant:
        return 1.0

    rejected = sum(max(0, (int(memory["frequency"]) - int(memory["feedback_balance"])) // 2) for memory in relevant)
    accepted = sum(max(0, (int(memory["frequency"]) + int(memory["feedback_balance"])) // 2) for memory in relevant)
    unstable = any(int(memory.get("is_unstable", 0)) for memory in relevant)

    if unstable:
        return 0.15
    if rejected >= 4 and accepted == 0:
        return 0.05
    if rejected >= 3 and rejected > accepted:
        return 0.15
    if rejected >= 2 and rejected >= accepted:
        return 0.2
    if rejected >= 1 and rejected > accepted:
        return 0.5
    return 1.0


def _find_related_entity_id(conn, decision: str) -> str | None:
    row = conn.execute(
        """
        SELECT id
        FROM entities
        WHERE canonical_name LIKE ?
        ORDER BY score DESC, id
        LIMIT 1
        """,
        (f"%{decision}%",),
    ).fetchone()
    if row is None:
        return None
    return str(row["id"])


def _build_pattern_row(entry: Any) -> dict[str, Any]:
    decision_text = str(_entry_value(entry, "decision_text", "")) or _extract_decision_text(str(_entry_value(entry, "content", "")))
    row = {
        "id": str(_entry_value(entry, "id", "")),
        "content": str(_entry_value(entry, "content", "")),
        "memory_type": str(_entry_value(entry, "memory_type", "")),
        "related_entity_id": _entry_value(entry, "related_entity_id", None),
        "score": float(_entry_value(entry, "score", 0.0)),
        "confidence_score": float(_entry_value(entry, "confidence_score", 0.5)),
        "frequency": int(_entry_value(entry, "frequency", 1)),
        "feedback_balance": int(_entry_value(entry, "feedback_balance", 0)),
        "last_used_at": str(_entry_value(entry, "last_used_at", "") or ""),
        "last_feedbacked_at": str(_entry_value(entry, "last_feedbacked_at", "") or ""),
        "created_at": str(_entry_value(entry, "created_at", "") or ""),
        "priority": int(_entry_value(entry, "priority", 0)),
        "normalized_key": str(_entry_value(entry, "normalized_key", normalize_decision_text(decision_text))),
        "is_unstable": int(_entry_value(entry, "is_unstable", 0)),
        "decision_text": decision_text,
        "valid_to": _entry_value(entry, "valid_to", None),
    }
    accepted_count, rejected_count = _accepted_rejected_counts(row)
    row["accepted_count"] = accepted_count
    row["rejected_count"] = rejected_count
    row["computed_score"] = compute_memory_score(row)
    row["penalty"] = apply_feedback_penalty(row["decision_text"], [row]) if row["memory_type"] == "decision_pattern" else 1.0
    row["final_score"] = round(row["computed_score"] * row["penalty"], 4)
    row["content"] = row["content"] or _build_pattern_content(row)
    return row


def _write_pattern_row(conn, entry: dict[str, Any]) -> None:
    entry["accepted_count"], entry["rejected_count"] = _accepted_rejected_counts(entry)
    entry["computed_score"] = compute_memory_score(entry)
    entry["penalty"] = apply_feedback_penalty(entry["decision_text"], [entry])
    entry["final_score"] = round(entry["computed_score"] * entry["penalty"], 4)
    entry["content"] = _build_pattern_content(entry)
    conn.execute(
        """
        UPDATE memory_entries
        SET content = ?, score = ?, confidence_score = ?, frequency = ?,
            last_used_at = ?, last_feedbacked_at = ?, feedback_balance = ?,
            normalized_key = ?, is_unstable = ?
        WHERE id = ?
        """,
        (
            entry["content"],
            entry["final_score"],
            entry["confidence_score"],
            entry["frequency"],
            entry["last_used_at"],
            entry["last_feedbacked_at"],
            entry["feedback_balance"],
            entry["normalized_key"],
            entry["is_unstable"],
            entry["id"],
        ),
    )


def store_learned_pattern(
    db_path: str | Path,
    question: str,
    decision: str,
    accepted: bool,
) -> None:
    initialize_database(db_path)
    decision = decision.strip()
    if not decision:
        return

    normalized_key = normalize_decision_text(decision)
    now = utc_now()

    with connect(db_path) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            compartment_id = get_or_create_compartment(conn, SYSTEM_MEMORY_SLUG, name="System Memory")
            related_entity_id = _find_related_entity_id(conn, decision)
            row = conn.execute(
                """
                SELECT *
                FROM memory_entries
                WHERE memory_type = 'decision_pattern'
                  AND normalized_key = ?
                  AND valid_to IS NULL
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (normalized_key,),
            ).fetchone()

            if row is None:
                entry = {
                    "id": new_uuid(),
                    "decision_text": decision,
                    "memory_type": "decision_pattern",
                    "related_entity_id": related_entity_id,
                    "frequency": 1,
                    "feedback_balance": 1 if accepted else -1,
                    "confidence_score": 0.8 if accepted else 0.35,
                    "last_used_at": now,
                    "last_feedbacked_at": now,
                    "created_at": now,
                    "priority": 40 if accepted else 10,
                    "normalized_key": normalized_key,
                    "is_unstable": 0,
                }
                entry["content"] = _build_pattern_content(entry)
                entry["computed_score"] = compute_memory_score(entry)
                entry["penalty"] = apply_feedback_penalty(entry["decision_text"], [entry])
                entry["final_score"] = round(entry["computed_score"] * entry["penalty"], 4)
                conn.execute(
                    """
                    INSERT INTO memory_entries (
                        id, compartment_id, memory_type, related_entity_id, content,
                        valid_from, valid_to, priority, score, confidence_score, frequency,
                        last_used_at, last_feedbacked_at, feedback_balance, normalized_key,
                        is_unstable, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry["id"],
                        compartment_id,
                        "decision_pattern",
                        related_entity_id,
                        entry["content"],
                        now,
                        entry["priority"],
                        entry["final_score"],
                        entry["confidence_score"],
                        entry["frequency"],
                        entry["last_used_at"],
                        entry["last_feedbacked_at"],
                        entry["feedback_balance"],
                        normalized_key,
                        entry["is_unstable"],
                        now,
                    ),
                )
            else:
                entry = _build_pattern_row(row)
                entry["decision_text"] = decision
                entry["related_entity_id"] = related_entity_id or entry["related_entity_id"]
                entry["frequency"] += 1
                entry["feedback_balance"] += 1 if accepted else -1
                delta = 0.08 if accepted else -0.18
                entry["confidence_score"] = round(_clamp(entry["confidence_score"] + delta, 0.05, 1.0), 4)
                entry["last_used_at"] = now
                entry["last_feedbacked_at"] = now
                _write_pattern_row(conn, entry)

            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _fetch_pattern_rows(
    db_path: str | Path,
    *,
    limit: int = 50,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    initialize_database(db_path)
    where_clause = "WHERE memory_type = 'decision_pattern'" if include_inactive else "WHERE memory_type = 'decision_pattern' AND valid_to IS NULL"
    with connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM memory_entries
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    pattern_rows = [_build_pattern_row(row) for row in rows]
    pattern_rows.sort(key=lambda item: (-item["final_score"], -item["priority"], item["decision_text"]))
    return pattern_rows


def fetch_learned_patterns(db_path: str | Path, limit: int = 10) -> list[str]:
    return [entry["content"] for entry in _fetch_pattern_rows(db_path, limit=limit) if not entry["is_unstable"]]


def fetch_relevant_memory_entries(
    db_path: str | Path,
    question: str,
    entity_ids: list[str] | None = None,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    initialize_database(db_path)
    keywords = _keywords(question)

    with connect(db_path) as conn:
        candidate_rows: list[object] = []
        if entity_ids:
            placeholders = ",".join("?" for _ in entity_ids)
            candidate_rows.extend(
                conn.execute(
                    f"""
                    SELECT me.*
                    FROM memory_entries me
                    WHERE me.related_entity_id IN ({placeholders})
                      AND me.valid_to IS NULL
                    ORDER BY me.priority DESC, me.score DESC, me.created_at DESC, me.id DESC
                    LIMIT ?
                    """,
                    (*entity_ids, limit),
                ).fetchall()
            )

        for keyword in keywords:
            candidate_rows.extend(
                conn.execute(
                    """
                    SELECT me.*
                    FROM memory_entries me
                    LEFT JOIN entities e ON e.id = me.related_entity_id
                    WHERE me.valid_to IS NULL
                      AND (me.content LIKE ? OR e.canonical_name LIKE ? OR me.normalized_key LIKE ?)
                    ORDER BY me.priority DESC, me.score DESC, me.created_at DESC, me.id DESC
                    LIMIT ?
                    """,
                    (f"%{keyword}%", f"%{keyword}%", f"%{normalize_decision_text(keyword)}%", limit),
                ).fetchall()
            )

        entries = [_build_pattern_row(row) if str(_entry_value(row, "memory_type", "")) == "decision_pattern" else {
            "id": str(_entry_value(row, "id", "")),
            "content": str(_entry_value(row, "content", "")),
            "memory_type": str(_entry_value(row, "memory_type", "")),
            "priority": int(_entry_value(row, "priority", 0)),
            "final_score": float(_entry_value(row, "score", 0.0)),
            "computed_score": float(_entry_value(row, "score", 0.0)),
            "penalty": 1.0,
            "is_unstable": 0,
            "last_used_at": str(_entry_value(row, "last_used_at", "") or ""),
            "last_feedbacked_at": str(_entry_value(row, "last_feedbacked_at", "") or ""),
        } for row in candidate_rows]

        selected: list[dict[str, Any]] = []
        now = utc_now()
        for entry in entries:
            if entry["memory_type"] == "decision_pattern":
                if entry["is_unstable"] or entry["final_score"] < MIN_RELEVANT_MEMORY_SCORE:
                    continue
                entry["last_used_at"] = now
                _write_pattern_row(conn, entry)
            selected.append(entry)

        conn.commit()

    selected = unique_preserve_order([entry["id"] for entry in selected])
    all_entries = {entry["id"]: entry for entry in entries if not entry.get("is_unstable") or entry["memory_type"] != "decision_pattern"}
    ordered_entries = [all_entries[entry_id] for entry_id in selected if entry_id in all_entries]
    ordered_entries.sort(key=lambda item: (-float(item.get("final_score", 0.0)), -int(item.get("priority", 0)), item["content"]))
    return ordered_entries[:limit]


def fetch_relevant_memories(
    db_path: str | Path,
    question: str,
    entity_ids: list[str] | None = None,
    *,
    limit: int = 5,
) -> list[str]:
    entries = fetch_relevant_memory_entries(db_path, question, entity_ids, limit=limit)
    return unique_preserve_order([str(entry["content"]) for entry in entries])[:limit]


def prune_old_memories(db_path: str | Path) -> dict[str, int]:
    initialize_database(db_path)
    archived = 0
    consolidated = 0
    now = utc_now()

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM memory_entries
            WHERE memory_type = 'decision_pattern'
              AND valid_to IS NULL
            ORDER BY normalized_key, score DESC, created_at DESC, id DESC
            """
        ).fetchall()

        groups: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            item = _build_pattern_row(row)
            groups.setdefault(item["normalized_key"], []).append(item)

        for normalized_key, entries in groups.items():
            if not normalized_key:
                continue
            keeper = entries[0]
            duplicates = entries[1:]
            if duplicates:
                consolidated += len(duplicates)
                keeper["frequency"] += sum(int(entry["frequency"]) for entry in duplicates)
                keeper["feedback_balance"] += sum(int(entry["feedback_balance"]) for entry in duplicates)
                keeper["confidence_score"] = max(
                    float(keeper["confidence_score"]),
                    *(float(entry["confidence_score"]) for entry in duplicates),
                )
                keeper["last_used_at"] = max(
                    [str(keeper["last_used_at"] or "")] +
                    [str(entry["last_used_at"] or "") for entry in duplicates]
                )
                keeper["last_feedbacked_at"] = max(
                    [str(keeper["last_feedbacked_at"] or "")] +
                    [str(entry["last_feedbacked_at"] or "") for entry in duplicates]
                )
                _write_pattern_row(conn, keeper)
                conn.execute(
                    f"""
                    UPDATE memory_entries
                    SET valid_to = ?
                    WHERE id IN ({",".join("?" for _ in duplicates)})
                    """,
                    (now, *[entry["id"] for entry in duplicates]),
                )

            for entry in entries[:1]:
                last_reference = _parse_datetime(
                    str(entry.get("last_feedbacked_at") or entry.get("last_used_at") or entry.get("created_at") or "")
                )
                age_days = 0
                if last_reference is not None:
                    if last_reference.tzinfo is None:
                        last_reference = last_reference.replace(tzinfo=UTC)
                    age_days = max((datetime.now(UTC) - last_reference).days, 0)
                if float(entry["final_score"]) < 0.25 and age_days >= 90:
                    conn.execute(
                        """
                        UPDATE memory_entries
                        SET valid_to = ?
                        WHERE id = ?
                        """,
                        (now, entry["id"]),
                    )
                    archived += 1

        conn.commit()

    return {
        "archived": archived,
        "consolidated": consolidated,
    }
