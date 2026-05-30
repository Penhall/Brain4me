from __future__ import annotations

from pathlib import Path

from .graphs import build_context_graph, build_knowledge_graph
from .storage import connect


def _fetch_table_rows(conn, table_name: str) -> list[dict[str, object]]:
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table_name} ORDER BY id").fetchall()]


def build_snapshot_payload(db_path: str | Path) -> dict[str, object]:
    knowledge_graph = build_knowledge_graph(db_path)
    context_graph = build_context_graph(db_path)

    with connect(db_path) as conn:
        counts = {
            "Compartments": conn.execute("SELECT COUNT(*) FROM compartments").fetchone()[0],
            "Sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "Notes": conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0],
            "Entities": conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
            "Relations": conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0],
            "Context Nodes": conn.execute("SELECT COUNT(*) FROM context_nodes").fetchone()[0],
            "Context Edges": conn.execute("SELECT COUNT(*) FROM context_edges").fetchone()[0],
            "Memory Entries": conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0],
            "Ingest Logs": conn.execute("SELECT COUNT(*) FROM ingest_logs").fetchone()[0],
        }

        return {
            "counts": counts,
            "graphs": {
                "knowledge": {
                    "nodes": knowledge_graph.number_of_nodes(),
                    "edges": knowledge_graph.number_of_edges(),
                },
                "context": {
                    "nodes": context_graph.number_of_nodes(),
                    "edges": context_graph.number_of_edges(),
                },
            },
            "entities": _fetch_table_rows(conn, "entities"),
            "relations": _fetch_table_rows(conn, "relations"),
            "context_nodes": _fetch_table_rows(conn, "context_nodes"),
            "context_edges": _fetch_table_rows(conn, "context_edges"),
            "memory_entries": _fetch_table_rows(conn, "memory_entries"),
        }
