SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS compartments (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    compartment_id TEXT NOT NULL REFERENCES compartments(id),
    source_type TEXT NOT NULL,
    source_origin_type TEXT NOT NULL DEFAULT 'personal',
    source_reliability REAL NOT NULL DEFAULT 0.9,
    source_path TEXT NOT NULL,
    title TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    hash TEXT NOT NULL,
    UNIQUE(source_path, hash)
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    content_markdown TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    compartment_id TEXT NOT NULL REFERENCES compartments(id),
    entity_type TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 1.0,
    score REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    UNIQUE(compartment_id, entity_type, canonical_name)
);

CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL REFERENCES entities(id),
    predicate TEXT NOT NULL,
    object_entity_id TEXT NOT NULL REFERENCES entities(id),
    assertion_type TEXT NOT NULL,
    note_id TEXT NOT NULL REFERENCES notes(id),
    confidence REAL NOT NULL DEFAULT 1.0,
    score REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_nodes (
    id TEXT PRIMARY KEY,
    compartment_id TEXT NOT NULL REFERENCES compartments(id),
    node_type TEXT NOT NULL,
    label TEXT NOT NULL,
    content TEXT NOT NULL,
    note_id TEXT NOT NULL REFERENCES notes(id),
    score REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_edges (
    id TEXT PRIMARY KEY,
    subject_context_node_id TEXT NOT NULL REFERENCES context_nodes(id),
    predicate TEXT NOT NULL,
    object_context_node_id TEXT NOT NULL REFERENCES context_nodes(id),
    note_id TEXT NOT NULL REFERENCES notes(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_entity_links (
    id TEXT PRIMARY KEY,
    context_node_id TEXT NOT NULL REFERENCES context_nodes(id),
    entity_id TEXT NOT NULL REFERENCES entities(id),
    role TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    compartment_id TEXT NOT NULL REFERENCES compartments(id),
    memory_type TEXT NOT NULL,
    related_entity_id TEXT REFERENCES entities(id),
    content TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    score REAL NOT NULL DEFAULT 1.0,
    confidence_score REAL NOT NULL DEFAULT 0.5,
    frequency INTEGER NOT NULL DEFAULT 1,
    last_used_at TEXT,
    last_feedbacked_at TEXT,
    feedback_balance INTEGER NOT NULL DEFAULT 0,
    normalized_key TEXT NOT NULL DEFAULT '',
    is_unstable INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingest_logs (
    id TEXT PRIMARY KEY,
    note_id TEXT REFERENCES notes(id),
    source_path TEXT NOT NULL,
    stage TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reasoning_traces (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    intent TEXT NOT NULL,
    detected_entities TEXT NOT NULL DEFAULT '[]',
    context_text TEXT NOT NULL DEFAULT '',
    suggested_decision TEXT NOT NULL DEFAULT '',
    answer TEXT NOT NULL DEFAULT '',
    sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_entries (
    id TEXT PRIMARY KEY,
    trace_id TEXT REFERENCES reasoning_traces(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL DEFAULT '',
    suggested_decision TEXT NOT NULL DEFAULT '',
    feedback_type TEXT NOT NULL,
    decision_key TEXT NOT NULL DEFAULT '',
    correction TEXT NOT NULL DEFAULT '',
    correction_key TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def ensure_required_columns(conn) -> None:
    required_columns = {
        "sources": {
            "source_origin_type": "TEXT NOT NULL DEFAULT 'personal'",
            "source_reliability": "REAL NOT NULL DEFAULT 0.9",
        },
        "entities": {"score": "REAL NOT NULL DEFAULT 1.0"},
        "relations": {"score": "REAL NOT NULL DEFAULT 1.0"},
        "context_nodes": {"score": "REAL NOT NULL DEFAULT 1.0"},
        "memory_entries": {
            "score": "REAL NOT NULL DEFAULT 1.0",
            "confidence_score": "REAL NOT NULL DEFAULT 0.5",
            "frequency": "INTEGER NOT NULL DEFAULT 1",
            "last_used_at": "TEXT",
            "last_feedbacked_at": "TEXT",
            "feedback_balance": "INTEGER NOT NULL DEFAULT 0",
            "normalized_key": "TEXT NOT NULL DEFAULT ''",
            "is_unstable": "INTEGER NOT NULL DEFAULT 0",
        },
        "feedback_entries": {
            "decision_key": "TEXT NOT NULL DEFAULT ''",
            "correction_key": "TEXT NOT NULL DEFAULT ''",
        },
    }

    for table_name, columns in required_columns.items():
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, definition in columns.items():
            if column_name not in existing:
                conn.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
                )


def create_indexes(conn) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_entities_canonical_name
            ON entities(canonical_name);
        CREATE INDEX IF NOT EXISTS idx_relations_subject_entity_id
            ON relations(subject_entity_id);
        CREATE INDEX IF NOT EXISTS idx_relations_object_entity_id
            ON relations(object_entity_id);
        CREATE INDEX IF NOT EXISTS idx_context_entity_links_entity_id
            ON context_entity_links(entity_id);
        CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type
            ON memory_entries(memory_type);
        """
    )
