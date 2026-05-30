from __future__ import annotations

from pathlib import Path
import sqlite3

from .storage_context import (
    create_context_edge,
    create_context_node,
    create_ingest_log,
    create_memory_entry,
    link_context_entity,
)
from .storage_core import (
    create_note,
    create_relation,
    create_source,
    get_or_create_compartment,
    new_uuid,
    upsert_entity,
    utc_now,
)
from .storage_schema import SCHEMA_SQL, create_indexes, ensure_required_columns


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: str | Path) -> Path:
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    with connect(db_file) as conn:
        conn.executescript(SCHEMA_SQL)
        ensure_required_columns(conn)
        create_indexes(conn)

    return db_file


__all__ = [
    "SCHEMA_SQL",
    "connect",
    "create_context_edge",
    "create_context_node",
    "create_ingest_log",
    "create_memory_entry",
    "create_note",
    "create_relation",
    "create_source",
    "get_or_create_compartment",
    "initialize_database",
    "link_context_entity",
    "new_uuid",
    "upsert_entity",
    "utc_now",
]
