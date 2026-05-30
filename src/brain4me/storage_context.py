from __future__ import annotations

import sqlite3

from .storage_core import new_uuid, utc_now


def create_context_node(
    conn: sqlite3.Connection,
    *,
    compartment_id: str,
    node_type: str,
    label: str,
    content: str,
    note_id: str,
    score: float = 1.0,
) -> str:
    context_node_id = new_uuid()
    conn.execute(
        """
        INSERT INTO context_nodes (id, compartment_id, node_type, label, content, note_id, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (context_node_id, compartment_id, node_type, label, content, note_id, score, utc_now()),
    )
    return context_node_id


def create_context_edge(
    conn: sqlite3.Connection,
    *,
    subject_context_node_id: str,
    predicate: str,
    object_context_node_id: str,
    note_id: str,
) -> str:
    context_edge_id = new_uuid()
    conn.execute(
        """
        INSERT INTO context_edges (
            id, subject_context_node_id, predicate, object_context_node_id, note_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (context_edge_id, subject_context_node_id, predicate, object_context_node_id, note_id, utc_now()),
    )
    return context_edge_id


def link_context_entity(
    conn: sqlite3.Connection,
    *,
    context_node_id: str,
    entity_id: str,
    role: str,
) -> str:
    link_id = new_uuid()
    conn.execute(
        """
        INSERT INTO context_entity_links (id, context_node_id, entity_id, role, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (link_id, context_node_id, entity_id, role, utc_now()),
    )
    return link_id


def create_memory_entry(
    conn: sqlite3.Connection,
    *,
    compartment_id: str,
    memory_type: str,
    related_entity_id: str | None,
    content: str,
    priority: int = 0,
    score: float = 1.0,
) -> str:
    memory_id = new_uuid()
    created_at = utc_now()
    conn.execute(
        """
        INSERT INTO memory_entries (
            id, compartment_id, memory_type, related_entity_id, content, valid_from, valid_to, priority, score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        """,
        (
            memory_id,
            compartment_id,
            memory_type,
            related_entity_id,
            content,
            created_at,
            priority,
            score,
            created_at,
        ),
    )
    return memory_id


def create_ingest_log(
    conn: sqlite3.Connection,
    *,
    note_id: str | None,
    source_path: str,
    stage: str,
    level: str,
    message: str,
) -> str:
    log_id = new_uuid()
    conn.execute(
        """
        INSERT INTO ingest_logs (
            id, note_id, source_path, stage, level, message, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (log_id, note_id, source_path, stage, level, message, utc_now()),
    )
    return log_id
