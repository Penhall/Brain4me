from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AnswerResult
from .storage import connect, initialize_database, new_uuid, utc_now


def _normalize_db_path(value: str | Path) -> str:
    return str(Path(value))


def save_reasoning_trace(result: AnswerResult) -> None:
    if not result.db_path:
        return

    try:
        db_path = _normalize_db_path(result.db_path)
        initialize_database(db_path)
        trace_id = new_uuid()
        sources_json = json.dumps(
            [
                {
                    "note_id": source.note_id,
                    "source_path": source.source_path,
                    "title": source.title,
                    "label": source.label,
                }
                for source in result.sources
            ],
            ensure_ascii=False,
            sort_keys=True,
        )
        detected_entities = json.dumps(result.detected_entities, ensure_ascii=False)

        with connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO reasoning_traces (
                    id, question, intent, detected_entities, context_text,
                    suggested_decision, answer, sources_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    result.question,
                    result.intent,
                    detected_entities,
                    result.context_text,
                    result.suggested_decision,
                    result.answer,
                    sources_json,
                    utc_now(),
                ),
            )
            conn.commit()
        result.trace_id = trace_id
    except Exception:
        return


def fetch_recent_reasoning_traces(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    initialize_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, question, intent, detected_entities, context_text, suggested_decision, answer, sources_json, created_at
            FROM reasoning_traces
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    traces: list[dict[str, Any]] = []
    for row in rows:
        traces.append(
            {
                "id": str(row["id"]),
                "question": str(row["question"]),
                "intent": str(row["intent"]),
                "detected_entities": json.loads(row["detected_entities"] or "[]"),
                "context_text": str(row["context_text"]),
                "suggested_decision": str(row["suggested_decision"]),
                "answer": str(row["answer"]),
                "sources": json.loads(row["sources_json"] or "[]"),
                "created_at": str(row["created_at"]),
            }
        )
    return traces
