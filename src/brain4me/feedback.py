from __future__ import annotations

from pathlib import Path
from typing import Any

from .memory import _fetch_pattern_rows, compute_memory_score, store_learned_pattern
from .patterns import normalize_decision_text
from .storage import connect, initialize_database, new_uuid, utc_now


def detect_unstable_pattern(pattern) -> bool:
    feedback_balance = int(pattern.get("feedback_balance", 0))
    frequency = int(pattern.get("frequency", 1))
    correction_variants = int(pattern.get("correction_variants", 0))
    rejected = max(0, (frequency - feedback_balance) // 2)
    accepted = max(0, frequency - rejected)
    if int(pattern.get("is_unstable", 0)) == 1:
        return True
    if correction_variants >= 2:
        return True
    if rejected >= 3 and accepted <= 1:
        return True
    if accepted > 0 and rejected > 0 and abs(feedback_balance) <= 1:
        return True
    if compute_memory_score(pattern) < 0.25 and rejected >= 2:
        return True
    return False


def _refresh_pattern_stability(conn, decision_key: str) -> None:
    if not decision_key:
        return

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
        (decision_key,),
    ).fetchone()
    if row is None:
        return

    correction_variants = conn.execute(
        """
        SELECT COUNT(DISTINCT correction_key) AS total
        FROM feedback_entries
        WHERE decision_key = ?
          AND correction_key != ''
        """,
        (decision_key,),
    ).fetchone()["total"]

    pattern = {
        **{key: row[key] for key in row.keys()},
        "correction_variants": int(correction_variants),
    }
    is_unstable = 1 if detect_unstable_pattern(pattern) else 0
    conn.execute(
        """
        UPDATE memory_entries
        SET is_unstable = ?
        WHERE id = ?
        """,
        (is_unstable, row["id"]),
    )


def record_feedback(
    question: str,
    accepted: bool,
    correction: str | None = None,
    *,
    db_path: str | Path | None = None,
) -> None:
    if db_path is None:
        return

    initialize_database(db_path)

    with connect(db_path) as conn:
        trace_row = conn.execute(
            """
            SELECT id, question, answer, suggested_decision
            FROM reasoning_traces
            WHERE question = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (question,),
        ).fetchone()

        feedback_type = "accepted" if accepted else ("corrected" if correction else "rejected")
        trace_id = str(trace_row["id"]) if trace_row is not None else ""
        answer = str(trace_row["answer"]) if trace_row is not None else ""
        suggested_decision = str(trace_row["suggested_decision"]) if trace_row is not None else ""
        decision_key = normalize_decision_text(suggested_decision) if suggested_decision else ""
        correction_key = normalize_decision_text(correction or "") if correction else ""

        conn.execute(
            """
            INSERT INTO feedback_entries (
                id, trace_id, question, answer, suggested_decision, feedback_type,
                decision_key, correction, correction_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_uuid(),
                trace_id or None,
                question,
                answer,
                suggested_decision,
                feedback_type,
                decision_key,
                correction or "",
                correction_key,
                utc_now(),
            ),
        )
        conn.commit()

    if accepted and suggested_decision:
        store_learned_pattern(db_path, question, suggested_decision, True)
    elif not accepted and suggested_decision:
        store_learned_pattern(db_path, question, suggested_decision, False)

    if correction and correction_key != decision_key:
        store_learned_pattern(db_path, question, correction, True)

    with connect(db_path) as conn:
        if decision_key:
            _refresh_pattern_stability(conn, decision_key)
        if correction_key:
            _refresh_pattern_stability(conn, correction_key)
        conn.commit()


def fetch_recent_feedback_entries(db_path: str | Path, limit: int = 10) -> list[dict[str, str]]:
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT question, answer, suggested_decision, feedback_type, correction, created_at
            FROM feedback_entries
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "question": str(row["question"]),
            "answer": str(row["answer"]),
            "suggested_decision": str(row["suggested_decision"]),
            "feedback_type": str(row["feedback_type"]),
            "correction": str(row["correction"]),
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]
