from __future__ import annotations

from pathlib import Path

import networkx as nx

from .storage import connect


def build_knowledge_graph(db_path: str | Path) -> nx.DiGraph:
    graph = nx.DiGraph(name="knowledge_graph")

    with connect(db_path) as conn:
        for row in conn.execute(
            "SELECT id, entity_type, canonical_name, score, created_at FROM entities ORDER BY id"
        ).fetchall():
            graph.add_node(
                f"entity:{row['id']}",
                entity_type=row["entity_type"],
                label=row["canonical_name"],
                score=row["score"],
                created_at=row["created_at"],
            )

        for row in conn.execute(
            """
            SELECT subject_entity_id, predicate, object_entity_id, assertion_type, score
            FROM relations
            ORDER BY id
            """
        ).fetchall():
            graph.add_edge(
                f"entity:{row['subject_entity_id']}",
                f"entity:{row['object_entity_id']}",
                predicate=row["predicate"],
                assertion_type=row["assertion_type"],
                score=row["score"],
            )

    return graph


def build_context_graph(db_path: str | Path) -> nx.DiGraph:
    graph = nx.DiGraph(name="context_graph")

    with connect(db_path) as conn:
        for row in conn.execute(
            "SELECT id, node_type, label, content, score, note_id, created_at FROM context_nodes ORDER BY id"
        ).fetchall():
            graph.add_node(
                f"context:{row['id']}",
                node_type=row["node_type"],
                label=row["label"],
                content=row["content"],
                score=row["score"],
                note_id=row["note_id"],
                created_at=row["created_at"],
            )

        for row in conn.execute(
            """
            SELECT subject_context_node_id, predicate, object_context_node_id, note_id
            FROM context_edges
            ORDER BY id
            """
        ).fetchall():
            graph.add_edge(
                f"context:{row['subject_context_node_id']}",
                f"context:{row['object_context_node_id']}",
                predicate=row["predicate"],
                note_id=row["note_id"],
            )

    return graph
