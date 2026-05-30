from __future__ import annotations

from datetime import UTC, datetime
import sqlite3
import uuid

from .linker import find_linked_entity_id


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_uuid() -> str:
    return str(uuid.uuid4())


def get_or_create_compartment(
    conn: sqlite3.Connection,
    slug: str,
    name: str | None = None,
    description: str = "",
) -> str:
    row = conn.execute(
        "SELECT id FROM compartments WHERE slug = ?",
        (slug,),
    ).fetchone()
    if row:
        return str(row["id"])

    compartment_id = new_uuid()
    conn.execute(
        """
        INSERT INTO compartments (id, slug, name, description, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (compartment_id, slug, name or slug.replace("-", " ").title(), description, utc_now()),
    )
    return compartment_id


def create_source(
    conn: sqlite3.Connection,
    *,
    compartment_id: str,
    source_type: str,
    source_origin_type: str,
    source_reliability: float,
    source_path: str,
    title: str,
    hash_value: str,
) -> str:
    source_id = new_uuid()
    conn.execute(
        """
        INSERT OR IGNORE INTO sources (
            id, compartment_id, source_type, source_origin_type, source_reliability, source_path, title, captured_at, hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_id,
            compartment_id,
            source_type,
            source_origin_type,
            source_reliability,
            source_path,
            title,
            utc_now(),
            hash_value,
        ),
    )
    return str(
        conn.execute(
            "SELECT id FROM sources WHERE source_path = ? AND hash = ?",
            (source_path, hash_value),
        ).fetchone()["id"]
    )


def create_note(
    conn: sqlite3.Connection,
    *,
    source_id: str,
    content_markdown: str,
    summary: str = "",
    status: str = "validated",
) -> str:
    note_id = new_uuid()
    conn.execute(
        """
        INSERT INTO notes (id, source_id, content_markdown, summary, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (note_id, source_id, content_markdown, summary, status, utc_now()),
    )
    return note_id


def upsert_entity(
    conn: sqlite3.Connection,
    *,
    compartment_id: str,
    entity_type: str,
    canonical_name: str,
    context_hints: list[str] | None = None,
    description: str = "",
    confidence: float = 1.0,
    score: float = 1.0,
) -> tuple[str, bool]:
    row = conn.execute(
        """
        SELECT id FROM entities
        WHERE compartment_id = ? AND entity_type = ? AND canonical_name = ?
        """,
        (compartment_id, entity_type, canonical_name),
    ).fetchone()
    if row:
        return str(row["id"]), False

    linked_entity_id = find_linked_entity_id(
        conn,
        compartment_id=compartment_id,
        entity_type=entity_type,
        canonical_name=canonical_name,
        context_hints=context_hints,
    )
    if linked_entity_id is not None:
        return linked_entity_id, False

    entity_id = new_uuid()
    conn.execute(
        """
        INSERT INTO entities (
            id, compartment_id, entity_type, canonical_name, description, confidence, score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            compartment_id,
            entity_type,
            canonical_name,
            description,
            confidence,
            score,
            utc_now(),
        ),
    )
    return entity_id, True


def create_relation(
    conn: sqlite3.Connection,
    *,
    subject_entity_id: str,
    predicate: str,
    object_entity_id: str,
    assertion_type: str,
    note_id: str,
    confidence: float = 1.0,
    score: float = 1.0,
) -> str:
    relation_id = new_uuid()
    conn.execute(
        """
        INSERT INTO relations (
            id, subject_entity_id, predicate, object_entity_id, assertion_type, note_id, confidence, score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            relation_id,
            subject_entity_id,
            predicate,
            object_entity_id,
            assertion_type,
            note_id,
            confidence,
            score,
            utc_now(),
        ),
    )
    return relation_id
