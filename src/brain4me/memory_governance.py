from __future__ import annotations

from pathlib import Path

from .memory import _fetch_pattern_rows
from .storage import connect, initialize_database, utc_now


def list_patterns(db_path: str | Path, limit: int = 20) -> list[dict[str, object]]:
    return _fetch_pattern_rows(db_path, limit=limit)


def remove_pattern(db_path: str | Path, pattern_id: str) -> None:
    initialize_database(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE memory_entries
            SET valid_to = ?
            WHERE id = ?
              AND memory_type = 'decision_pattern'
            """,
            (utc_now(), pattern_id),
        )
        conn.commit()


def update_pattern_score(db_path: str | Path, pattern_id: str, new_score: float) -> None:
    initialize_database(db_path)
    bounded_score = max(0.0, min(1.0, float(new_score)))
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE memory_entries
            SET confidence_score = ?, score = ?
            WHERE id = ?
              AND memory_type = 'decision_pattern'
            """,
            (bounded_score, bounded_score, pattern_id),
        )
        conn.commit()
