from __future__ import annotations

from typing import Any

import yaml

from .models import IngestResult
from .scoring import ScoreInputs, compute_score
from .storage import (
    create_context_edge,
    create_context_node,
    create_relation,
    link_context_entity,
)


def split_frontmatter(markdown_text: str) -> tuple[dict[str, str], str]:
    if not markdown_text.startswith("---"):
        return {}, markdown_text

    marker = "\n---"
    end_index = markdown_text.find(marker, 3)
    if end_index == -1:
        return {}, markdown_text

    raw_frontmatter = markdown_text[3:end_index]
    body = markdown_text[end_index + len(marker) :].lstrip("\n")
    parsed = yaml.safe_load(raw_frontmatter) or {}
    return parsed, body


def create_automatic_conflicts(
    conn: Any,
    *,
    compartment_id: str,
    note_id: str,
    decision_nodes: list[tuple[str, str, str]],
    scoped_entity_ids: list[str],
    source_reliability: float,
) -> tuple[int, int]:
    if not decision_nodes or not scoped_entity_ids:
        return 0, 0

    current_decision_ids = [decision_id for decision_id, _, _ in decision_nodes]
    scope_placeholders = ",".join("?" for _ in scoped_entity_ids)
    decision_placeholders = ",".join("?" for _ in current_decision_ids)
    conflicting_rows = conn.execute(
        f"""
        SELECT DISTINCT
            d.id AS decision_id,
            d.canonical_name AS decision_name,
            cel.context_node_id AS decision_context_node_id
        FROM relations r
        JOIN entities d
          ON d.id = r.subject_entity_id
         AND d.entity_type = 'Decision'
        JOIN context_entity_links cel
          ON cel.entity_id = d.id
         AND cel.role = 'decision'
        WHERE r.predicate IN ('afeta', 'resolve')
          AND r.object_entity_id IN ({scope_placeholders})
          AND d.id NOT IN ({decision_placeholders})
        ORDER BY d.score DESC, d.id
        """,
        (*scoped_entity_ids, *current_decision_ids),
    ).fetchall()

    context_nodes_created = 0
    context_edges_created = 0
    seen_pairs: set[tuple[str, str]] = set()

    for current_decision_id, current_context_id, current_name in decision_nodes:
        for row in conflicting_rows:
            other_decision_id = str(row["decision_id"])
            other_context_id = str(row["decision_context_node_id"])
            other_name = str(row["decision_name"])
            if other_decision_id == current_decision_id or other_name == current_name:
                continue

            pair = tuple(sorted((current_decision_id, other_decision_id)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            conflict_node_id = create_context_node(
                conn,
                compartment_id=compartment_id,
                node_type="conflict",
                label="conflict",
                content=f"Conflito detectado entre decisoes: {current_name} <-> {other_name}",
                note_id=note_id,
                score=compute_score(
                    ScoreInputs(source_reliability=source_reliability)
                ),
            )
            context_nodes_created += 1

            create_context_edge(
                conn,
                subject_context_node_id=conflict_node_id,
                predicate="contradicts",
                object_context_node_id=current_context_id,
                note_id=note_id,
            )
            create_context_edge(
                conn,
                subject_context_node_id=conflict_node_id,
                predicate="contradicts",
                object_context_node_id=other_context_id,
                note_id=note_id,
            )
            context_edges_created += 2

    return context_nodes_created, context_edges_created


def attach_context_items(
    conn: Any,
    *,
    result: IngestResult,
    compartment_id: str,
    note_id: str,
    decision_nodes: list[tuple[str, str, str]],
    entities_by_type: dict[str, list[tuple[str, str]]],
    item_type: str,
    node_type: str,
    relation_predicate: str,
    context_predicate: str,
    role: str,
    source_reliability: float,
) -> None:
    for entity_id, name in entities_by_type.get(item_type, []):
        for decision_entity_id, decision_context_id, _ in decision_nodes:
            create_relation(
                conn,
                subject_entity_id=entity_id,
                predicate=relation_predicate,
                object_entity_id=decision_entity_id,
                assertion_type="decision_context",
                note_id=note_id,
                score=compute_score(
                    ScoreInputs(source_reliability=source_reliability)
                ),
            )
            result.relations_created += 1

            context_node_id = create_context_node(
                conn,
                compartment_id=compartment_id,
                node_type=node_type,
                label=name,
                content=name,
                note_id=note_id,
                score=compute_score(
                    ScoreInputs(source_reliability=source_reliability)
                ),
            )
            link_context_entity(
                conn,
                context_node_id=context_node_id,
                entity_id=entity_id,
                role=role,
            )
            result.context_nodes_created += 1
            create_context_edge(
                conn,
                subject_context_node_id=context_node_id,
                predicate=context_predicate,
                object_context_node_id=decision_context_id,
                note_id=note_id,
            )
            result.context_edges_created += 1
