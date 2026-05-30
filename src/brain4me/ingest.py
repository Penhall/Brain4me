from __future__ import annotations

import hashlib
from pathlib import Path

from .extractor import ExtractionPayload, MarkdownExtractor, build_default_extractor
from .graph_cache import invalidate_cache
from .ingest_helpers import attach_context_items, create_automatic_conflicts, split_frontmatter
from .models import IngestResult
from .scoring import ScoreInputs, compute_score, default_source_reliability, normalize_frequency
from .storage import (
    connect,
    create_context_edge,
    create_context_node,
    create_ingest_log,
    create_memory_entry,
    create_note,
    create_relation,
    create_source,
    get_or_create_compartment,
    initialize_database,
    link_context_entity,
    upsert_entity,
)


def _ingest_processed_text(
    db_path: str | Path,
    *,
    result: IngestResult,
    note_content: str,
    source_path: str,
    source_hash: str,
    title: str,
    compartment_slug: str,
    source_type: str,
    source_origin_type: str,
    source_reliability: float,
    extraction_payload: ExtractionPayload,
    context_hints: list[str],
) -> IngestResult:
    """Core ingestion logic shared between markdown and raw-text paths."""
    with connect(db_path) as conn:
        compartment_id = get_or_create_compartment(conn, compartment_slug)
        source_id = create_source(
            conn,
            compartment_id=compartment_id,
            source_type=source_type,
            source_origin_type=source_origin_type,
            source_reliability=source_reliability,
            source_path=source_path,
            title=title,
            hash_value=source_hash,
        )
        note_id = create_note(
            conn,
            source_id=source_id,
            content_markdown=note_content,
            summary=title,
            status="validated",
        )
        for warning in extraction_payload.warnings:
            create_ingest_log(
                conn,
                note_id=note_id,
                source_path=source_path,
                stage="extractor",
                level="warning",
                message=warning,
            )
            result.logs_created += 1

        entities_by_type: dict[str, list[tuple[str, str]]] = {}
        item_frequencies: dict[tuple[str, str], int] = {}
        for entity_type, canonical_name in extraction_payload.entity_items:
            key = (entity_type, canonical_name)
            item_frequencies[key] = item_frequencies.get(key, 0) + 1

        for entity_type, canonical_name in extraction_payload.entity_items:
            entity_id, created = upsert_entity(
                conn,
                compartment_id=compartment_id,
                entity_type=entity_type,
                canonical_name=canonical_name,
                context_hints=context_hints,
                description=f"{entity_type} derivado de extracao estruturada.",
                score=compute_score(
                    ScoreInputs(
                        recency=1.0,
                        frequency=normalize_frequency(item_frequencies[(entity_type, canonical_name)]),
                        confidence=1.0,
                        source_reliability=source_reliability,
                    )
                ),
            )
            if created:
                result.entities_created += 1
            entities_by_type.setdefault(entity_type, []).append((entity_id, canonical_name))

        decision_nodes: list[tuple[str, str, str]] = []
        for entity_id, name in entities_by_type.get("Decision", []):
            node_id = create_context_node(
                conn,
                compartment_id=compartment_id,
                node_type="decision",
                label=name,
                content=name,
                note_id=note_id,
                score=compute_score(
                    ScoreInputs(source_reliability=source_reliability)
                ),
            )
            link_context_entity(conn, context_node_id=node_id, entity_id=entity_id, role="decision")
            result.context_nodes_created += 1
            decision_nodes.append((entity_id, node_id, name))

        for entity_type, predicate in (("Project", "afeta"), ("Problem", "resolve")):
            for entity_id, _ in entities_by_type.get(entity_type, []):
                for decision_entity_id, _, _ in decision_nodes:
                    create_relation(
                        conn,
                        subject_entity_id=decision_entity_id,
                        predicate=predicate,
                        object_entity_id=entity_id,
                        assertion_type="decision_context",
                        note_id=note_id,
                        score=compute_score(
                            ScoreInputs(source_reliability=source_reliability)
                        ),
                    )
                    result.relations_created += 1

        scoped_entity_ids = [
            entity_id
            for entity_type in ("Project", "Problem")
            for entity_id, _ in entities_by_type.get(entity_type, [])
        ]
        conflict_nodes, conflict_edges = create_automatic_conflicts(
            conn,
            compartment_id=compartment_id,
            note_id=note_id,
            decision_nodes=decision_nodes,
            scoped_entity_ids=scoped_entity_ids,
            source_reliability=source_reliability,
        )
        result.context_nodes_created += conflict_nodes
        result.context_edges_created += conflict_edges

        for config in (
            ("Evidence", "evidence", "supports", "supports", "evidence"),
            ("Alternative", "alternative", "alternative_a", "alternative_to", "alternative"),
            ("Risk", "risk", "afeta", "warns_about", "risk"),
        ):
            attach_context_items(
                conn,
                result=result,
                compartment_id=compartment_id,
                note_id=note_id,
                decision_nodes=decision_nodes,
                entities_by_type=entities_by_type,
                item_type=config[0],
                node_type=config[1],
                relation_predicate=config[2],
                context_predicate=config[3],
                role=config[4],
                source_reliability=source_reliability,
            )

        for node_type, context_predicate, content in extraction_payload.context_only_items:
            for _, decision_context_id, _ in decision_nodes:
                context_node_id = create_context_node(
                    conn,
                    compartment_id=compartment_id,
                    node_type=node_type,
                    label=content,
                    content=content,
                    note_id=note_id,
                    score=compute_score(
                        ScoreInputs(source_reliability=source_reliability)
                    ),
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

        for decision_entity_id, _, decision_name in decision_nodes:
            create_memory_entry(
                conn,
                compartment_id=compartment_id,
                memory_type="episodic",
                related_entity_id=decision_entity_id,
                content=f"Decisao registrada: {decision_name}",
                priority=10,
                score=compute_score(
                    ScoreInputs(source_reliability=source_reliability)
                ),
            )
            result.memory_entries_created += 1

        conn.commit()

    invalidate_cache(db_path)
    return result


def ingest_markdown_note(
    *,
    db_path: str | Path,
    markdown_text: str,
    source_path: str,
    extractor: MarkdownExtractor | None = None,
) -> IngestResult:
    initialize_database(db_path)
    result = IngestResult()
    metadata, body = split_frontmatter(markdown_text)
    compartment_slug = str(metadata.get("compartment", "default")).strip() or "default"
    title = str(metadata.get("title", Path(source_path).stem)).strip() or Path(source_path).stem
    source_type = str(metadata.get("source_type", "markdown")).strip() or "markdown"
    source_origin_type = str(metadata.get("source_origin_type", "personal")).strip() or "personal"
    source_reliability = default_source_reliability(source_origin_type)
    extraction_payload = (extractor or build_default_extractor()).extract(body)
    source_hash = hashlib.sha256(markdown_text.encode("utf-8")).hexdigest()
    context_hints = [
        canonical_name
        for entity_type, canonical_name in extraction_payload.entity_items
        if entity_type in {"Project", "Problem"}
    ]

    return _ingest_processed_text(
        db_path,
        result=result,
        note_content=markdown_text,
        source_path=source_path,
        source_hash=source_hash,
        title=title,
        compartment_slug=compartment_slug,
        source_type=source_type,
        source_origin_type=source_origin_type,
        source_reliability=source_reliability,
        extraction_payload=extraction_payload,
        context_hints=context_hints,
    )


def ingest_raw_text(
    *,
    db_path: str | Path,
    raw_text: str,
    source_path: str,
    source_type: str,
    compartment: str = "default",
    title: str | None = None,
) -> IngestResult:
    """Ingest raw text (extracted from PDF, DOCX, or TXT) into the brain.

    Parameters
    ----------
    db_path : str or Path
        Path to the SQLite database.
    raw_text : str
        The extracted plain text content.
    source_path : str
        Original file path (used for display and deduplication).
    source_type : str
        Document type: ``"pdf"``, ``"docx"``, or ``"txt"``.
    compartment : str, optional
        Compartment to store data under (default ``"default"``).
    title : str or None, optional
        Display title. Falls back to the stem of *source_path* when ``None``.

    Returns
    -------
    IngestResult
        Counts of entities, relations, context nodes, etc. created.
    """
    initialize_database(db_path)
    result = IngestResult()

    title = title or Path(source_path).stem
    source_origin_type = "external"
    source_reliability = default_source_reliability(source_origin_type)
    extraction_payload = (build_default_extractor()).extract(raw_text)
    source_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    context_hints = [
        canonical_name
        for entity_type, canonical_name in extraction_payload.entity_items
        if entity_type in {"Project", "Problem"}
    ]

    # Store a minimal markdown-like note so it works with the existing schema
    note_content = f"# {title}\n\n{raw_text}"

    return _ingest_processed_text(
        db_path,
        result=result,
        note_content=note_content,
        source_path=source_path,
        source_hash=source_hash,
        title=title,
        compartment_slug=compartment,
        source_type=source_type,
        source_origin_type=source_origin_type,
        source_reliability=source_reliability,
        extraction_payload=extraction_payload,
        context_hints=context_hints,
    )
