from typing import Any

from .models import SourceReference


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def find_entity_rows(conn: Any, terms: list[str], limit: int = 10):
    matches: list[object] = []
    for term in terms:
        pattern = f"%{term}%"
        matches.extend(
            conn.execute(
                """
                SELECT id, entity_type, canonical_name, score
                FROM entities
                WHERE canonical_name LIKE ?
                ORDER BY score DESC, id
                LIMIT ?
                """,
                (pattern, limit),
            ).fetchall()
        )
    return matches


def fetch_linked_context_node_ids(conn: Any, entity_ids: list[str]) -> list[str]:
    if not entity_ids:
        return []
    placeholders = ",".join("?" for _ in entity_ids)
    rows = conn.execute(
        f"""
        SELECT DISTINCT context_node_id
        FROM context_entity_links
        WHERE entity_id IN ({placeholders})
        ORDER BY context_node_id
        """,
        (*entity_ids,),
    ).fetchall()
    return [str(row["context_node_id"]) for row in rows]


def find_decision_rows(conn: Any, topic: str):
    pattern = f"%{topic}%"
    return conn.execute(
        """
        SELECT DISTINCT d.id, d.canonical_name
        FROM entities d
        WHERE d.entity_type = 'Decision'
          AND (
                d.canonical_name LIKE ?
             OR d.id IN (
                SELECT DISTINCT linked.entity_id
                FROM context_nodes cn
                JOIN context_edges ce
                  ON ce.subject_context_node_id = cn.id
                JOIN context_entity_links linked
                  ON linked.context_node_id = ce.object_context_node_id
                 AND linked.role = 'decision'
                WHERE cn.content LIKE ?
             )
             OR d.id IN (
                SELECT DISTINCT r.object_entity_id
                FROM relations r
                JOIN entities e ON e.id = r.subject_entity_id
                WHERE e.canonical_name LIKE ?
             )
             OR d.id IN (
                SELECT DISTINCT r.subject_entity_id
                FROM relations r
                JOIN entities e ON e.id = r.object_entity_id
                WHERE e.canonical_name LIKE ?
             )
          )
        ORDER BY d.score DESC, d.id
        """,
        (pattern, pattern, pattern, pattern),
    ).fetchall()


def fetch_related_decision_entities(conn: Any, decision_ids: list[str], entity_type: str, predicate: str) -> list[str]:
    placeholders = ",".join("?" for _ in decision_ids)
    relation_query = f"""
        SELECT e.canonical_name
        FROM relations r
        JOIN entities e ON e.id = r.subject_entity_id
        WHERE r.object_entity_id IN ({placeholders})
          AND e.entity_type = ?
          AND r.predicate = ?
        ORDER BY r.score DESC, r.id
    """
    return [
        str(row["canonical_name"])
        for row in conn.execute(relation_query, (*decision_ids, entity_type, predicate)).fetchall()
    ]


def fetch_entity_relations(conn: Any, related_ids: list[str]):
    placeholders = ",".join("?" for _ in related_ids)
    return conn.execute(
        f"""
        SELECT
            s.entity_type AS subject_type,
            s.canonical_name AS subject_name,
            r.predicate AS predicate,
            o.entity_type AS object_type,
            o.canonical_name AS object_name
        FROM relations r
        JOIN entities s ON s.id = r.subject_entity_id
        JOIN entities o ON o.id = r.object_entity_id
        WHERE r.subject_entity_id IN ({placeholders})
           OR r.object_entity_id IN ({placeholders})
        ORDER BY r.score DESC, r.id
        """,
        (*related_ids, *related_ids),
    ).fetchall()


def fetch_decision_context(conn: Any, decision_ids: list[str]):
    decision_placeholders = ",".join("?" for _ in decision_ids)
    return conn.execute(
        f"""
        SELECT DISTINCT
            cn.node_type,
            cn.content,
            ce.predicate
        FROM context_entity_links cel
        JOIN context_edges ce
          ON ce.object_context_node_id = cel.context_node_id
        JOIN context_nodes cn
          ON cn.id = ce.subject_context_node_id
        WHERE cel.role = 'decision'
          AND cel.entity_id IN ({decision_placeholders})
        ORDER BY cn.score DESC, cn.id
        """,
        (*decision_ids,),
    ).fetchall()


def fetch_history(conn: Any, related_ids: list[str]):
    placeholders = ",".join("?" for _ in related_ids)
    return conn.execute(
        f"""
        SELECT content
        FROM memory_entries
        WHERE related_entity_id IN ({placeholders})
        ORDER BY score DESC, id
        """,
        (*related_ids,),
    ).fetchall()


def fetch_sources_for_decisions(conn: Any, decision_ids: list[str]) -> list[SourceReference]:
    if not decision_ids:
        return []
    placeholders = ",".join("?" for _ in decision_ids)
    rows = conn.execute(
        f"""
        SELECT e.canonical_name AS label, n.id AS note_id, s.source_path, s.title
        FROM entities e
        JOIN context_entity_links cel ON cel.entity_id = e.id AND cel.role = 'decision'
        JOIN context_nodes cn ON cn.id = cel.context_node_id
        LEFT JOIN notes n ON n.id = cn.note_id
        LEFT JOIN sources s ON s.id = n.source_id
        WHERE e.id IN ({placeholders})
          AND n.id IS NOT NULL
        GROUP BY n.id
        ORDER BY e.id
        """,
        (*decision_ids,),
    ).fetchall()

    return [
        SourceReference(
            note_id=str(row["note_id"]),
            source_path=row["source_path"] or "",
            title=row["title"] or "",
            label=str(row["label"]),
        )
        for row in rows
    ]
