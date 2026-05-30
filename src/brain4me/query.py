from __future__ import annotations

from collections import deque
from dataclasses import replace
from pathlib import Path
from time import perf_counter
import re

from .context_builder import build_answer_prompt, build_context_for_question
from .decision_engine import suggest_decision
from .graph_cache import get_cached_graphs
from .intent import classify_intent
from .llm_client import build_qa_provider_from_env
from .metrics import get_metrics_snapshot, log_metric, set_metric
from .memory import fetch_relevant_memories
from .models import AnswerResult, EntityExplanation, GraphContext, TopicExplanation
from .query_helpers import (
    fetch_decision_context,
    fetch_entity_relations,
    fetch_history,
    fetch_linked_context_node_ids,
    fetch_related_decision_entities,
    fetch_sources_for_decisions,
    find_decision_rows,
    find_entity_rows,
    unique_preserve_order,
)
from .reasoning_log import save_reasoning_trace
from .semantic import semantic_similarity
from .storage import connect


STOPWORDS = {"o", "a", "os", "as", "de", "do", "da", "e", "eu", "sei", "sobre", "que"}


def _candidate_terms(question: str) -> list[str]:
    candidates = [question]
    candidates.extend(
        token
        for token in re.findall(r"[A-Za-z0-9_-]+", question)
        if len(token) >= 4 and token.lower() not in STOPWORDS
    )
    return unique_preserve_order(candidates)


def _format_reasoned_answer(question: str, context, sources) -> str:
    lines: list[str] = ["## Resposta direta"]
    if context.suggested_decision:
        lines.append(context.suggested_decision)
    elif context.decisions:
        for decision in context.decisions[:3]:
            lines.append(f"- {decision}")
    else:
        lines.append("Nao ha informacoes suficientes para responder com precisao.")

    lines.extend(["", "## Justificativa"])
    if context.evidence or context.memories or context.inferences:
        for item in unique_preserve_order([*context.evidence, *context.memories, *context.inferences])[:6]:
            lines.append(f"- {item}")
    else:
        lines.append("Nenhuma justificativa registrada.")

    lines.extend(["", "## Riscos e conflitos"])
    if context.risks or context.conflicts:
        for item in unique_preserve_order([*context.risks, *context.conflicts])[:6]:
            lines.append(f"- {item}")
    else:
        lines.append("Nenhum identificado.")

    lines.extend(["", "## Proximos passos"])
    next_steps = context.alternatives or context.detected_entities
    if next_steps:
        for item in unique_preserve_order(next_steps)[:6]:
            lines.append(f"- {item}")
    else:
        lines.append("Nenhum identificado.")

    lines.extend(["", "## Fontes"])
    if sources:
        for source in sources:
            label_text = source.title or source.source_path or source.label
            lines.append(f"- {label_text}")
    else:
        lines.append("- Nenhuma fonte registrada")
    return "\n".join(lines)


def explain_topic(db_path: str | Path, topic: str) -> TopicExplanation:
    with connect(db_path) as conn:
        decision_rows = find_decision_rows(conn, topic)
        decision_ids = [str(row["id"]) for row in decision_rows]
        if not decision_ids:
            return TopicExplanation(topic=topic)

        return TopicExplanation(
            topic=topic,
            decisions=unique_preserve_order([str(row["canonical_name"]) for row in decision_rows]),
            evidence=unique_preserve_order(
                fetch_related_decision_entities(conn, decision_ids, "Evidence", "supports")
            ),
            alternatives=unique_preserve_order(
                fetch_related_decision_entities(conn, decision_ids, "Alternative", "alternative_a")
            ),
            risks=unique_preserve_order(
                fetch_related_decision_entities(conn, decision_ids, "Risk", "afeta")
            ),
        )


def _resolve_explanation(db_path: str | Path, question: str) -> TopicExplanation:
    direct = explain_topic(db_path, question)
    if direct.decisions:
        return direct

    explanation = TopicExplanation(topic=question)
    for candidate in _candidate_terms(question):
        candidate_explanation = explain_topic(db_path, candidate)
        if candidate_explanation.decisions:
            return replace(candidate_explanation, topic=question)
    return explanation


def _lookup_entity_rows(db_path: str | Path, question: str):
    with connect(db_path) as conn:
        return find_entity_rows(conn, _candidate_terms(question))


def _neighbors_bidirectional(graph, node_id: str) -> list[str]:
    return unique_preserve_order(
        [*list(graph.successors(node_id)), *list(graph.predecessors(node_id))]
    )


def _traverse_graph(graph, start_nodes: list[str], depth: int) -> list[str]:
    visited: list[str] = []
    seen: set[str] = set()
    queue = deque((node_id, 0) for node_id in start_nodes if node_id in graph)

    while queue:
        node_id, distance = queue.popleft()
        if node_id in seen or distance > depth:
            continue
        seen.add(node_id)
        visited.append(node_id)
        if distance == depth:
            continue
        for neighbor_id in _neighbors_bidirectional(graph, node_id):
            if neighbor_id not in seen:
                queue.append((neighbor_id, distance + 1))
    return visited


def _resolve_entity_node_ids(db_path: str | Path, entity_ids: list[str]) -> list[str]:
    resolved_node_ids: list[str] = []
    raw_ids = [item for item in entity_ids if item and not item.startswith("entity:")]
    prefixed_ids = [item for item in entity_ids if item.startswith("entity:")]
    resolved_node_ids.extend(prefixed_ids)

    with connect(db_path) as conn:
        for item in raw_ids:
            rows = conn.execute(
                """
                SELECT id
                FROM entities
                WHERE id = ? OR canonical_name LIKE ?
                ORDER BY score DESC, id
                LIMIT 10
                """,
                (item, f"%{item}%"),
            ).fetchall()
            for row in rows:
                resolved_node_ids.append(f"entity:{row['id']}")
    return unique_preserve_order(resolved_node_ids)


def expand_graph_context(db_path: str | Path, entity_ids: list[str], depth: int = 2) -> GraphContext:
    if not entity_ids:
        return GraphContext()

    cached_graphs = get_cached_graphs(db_path)
    set_metric("cache_used", bool(cached_graphs.cache_hit))
    knowledge_graph = cached_graphs.kg
    context_graph = cached_graphs.context_graph
    if knowledge_graph is None or context_graph is None:
        return GraphContext()
    entity_node_ids = _resolve_entity_node_ids(db_path, entity_ids)
    visited_entity_nodes = _traverse_graph(knowledge_graph, entity_node_ids, depth)

    entity_labels: list[str] = []
    relation_texts: list[str] = []
    decision_labels: list[str] = []
    entity_db_ids = [node_id.split(":", 1)[1] for node_id in visited_entity_nodes if node_id.startswith("entity:")]

    for node_id in visited_entity_nodes:
        node = knowledge_graph.nodes[node_id]
        label = str(node.get("label", ""))
        if label:
            entity_labels.append(label)
        if node.get("entity_type") == "Decision" and label:
            decision_labels.append(label)

    for source_id in visited_entity_nodes:
        for target_id in knowledge_graph.successors(source_id):
            if target_id not in visited_entity_nodes:
                continue
            edge = knowledge_graph.edges[source_id, target_id]
            source_label = str(knowledge_graph.nodes[source_id].get("label", source_id))
            target_label = str(knowledge_graph.nodes[target_id].get("label", target_id))
            relation_texts.append(f"{source_label} --{edge.get('predicate', 'related_to')}--> {target_label}")

    with connect(db_path) as conn:
        linked_context_ids = fetch_linked_context_node_ids(conn, entity_db_ids)
    visited_context_nodes = _traverse_graph(
        context_graph,
        [f"context:{node_id}" for node_id in linked_context_ids],
        depth,
    )

    grouped_items: dict[str, list[str]] = {
        "decision": [],
        "evidence": [],
        "alternative": [],
        "risk": [],
        "conflict": [],
        "inference": [],
    }
    context_labels: list[str] = []

    for node_id in visited_context_nodes:
        node = context_graph.nodes[node_id]
        node_type = str(node.get("node_type", ""))
        content = str(node.get("content", "")) or str(node.get("label", ""))
        if content:
            context_labels.append(content)
        if node_type in grouped_items and content:
            grouped_items[node_type].append(content)

    return GraphContext(
        entities=unique_preserve_order([*entity_labels, *context_labels]),
        relations=unique_preserve_order(relation_texts),
        decisions=unique_preserve_order([*decision_labels, *grouped_items["decision"]]),
        evidence=unique_preserve_order(grouped_items["evidence"]),
        alternatives=unique_preserve_order(grouped_items["alternative"]),
        risks=unique_preserve_order(grouped_items["risk"]),
        conflicts=unique_preserve_order(grouped_items["conflict"]),
        inferences=unique_preserve_order(grouped_items["inference"]),
        context_nodes=unique_preserve_order(visited_context_nodes),
    )


def _semantic_context_search(
    db_path: str | Path,
    question: str,
    *,
    limit: int = 5,
    threshold: float = 0.18,
) -> GraphContext:
    matched_entities: list[str] = []
    grouped_items: dict[str, list[str]] = {
        "decision": [],
        "evidence": [],
        "alternative": [],
        "risk": [],
        "conflict": [],
        "inference": [],
    }
    semantic_relations: list[str] = []
    semantic_context_nodes: list[str] = []

    with connect(db_path) as conn:
        entity_rows = conn.execute(
            """
            SELECT canonical_name, entity_type, description, score
            FROM entities
            WHERE score >= 0.3
            ORDER BY score DESC, id
            LIMIT 200
            """
        ).fetchall()
        context_rows = conn.execute(
            """
            SELECT id, node_type, label, content
            FROM context_nodes
            ORDER BY score DESC, id
            LIMIT 500
            """
        ).fetchall()
    if len(entity_rows) >= 200:
        log_metric("semantic_search_entity_truncated", 1.0)

    scored_entities = []
    for row in entity_rows:
        content = " ".join(
            part
            for part in (str(row["canonical_name"]), str(row["description"] or ""))
            if part.strip()
        )
        similarity = semantic_similarity(question, content)
        combined_score = (similarity * 0.7) + (float(row["score"]) * 0.3)
        if combined_score >= threshold:
            scored_entities.append((combined_score, str(row["canonical_name"]), str(row["entity_type"])))

    for score, canonical_name, entity_type in sorted(scored_entities, reverse=True)[:limit]:
        matched_entities.append(canonical_name)
        semantic_relations.append(
            f"Semantica({round(score, 2)}): {entity_type}({canonical_name})"
        )

    scored_context = []
    for row in context_rows:
        content = " ".join(
            part
            for part in (str(row["label"] or ""), str(row["content"] or ""))
            if part.strip()
        )
        similarity = semantic_similarity(question, content)
        if similarity >= threshold:
            scored_context.append(
                (similarity, str(row["id"]), str(row["node_type"]), str(row["content"] or row["label"] or ""))
            )

    for similarity, node_id, node_type, content in sorted(scored_context, reverse=True)[:limit]:
        semantic_context_nodes.append(f"context:{node_id}")
        if node_type in grouped_items and content:
            grouped_items[node_type].append(content)
        if content:
            semantic_relations.append(f"Semantica({round(similarity, 2)}): {content}")

    return GraphContext(
        entities=unique_preserve_order(matched_entities),
        relations=unique_preserve_order(semantic_relations),
        decisions=unique_preserve_order(grouped_items["decision"]),
        evidence=unique_preserve_order(grouped_items["evidence"]),
        alternatives=unique_preserve_order(grouped_items["alternative"]),
        risks=unique_preserve_order(grouped_items["risk"]),
        conflicts=unique_preserve_order(grouped_items["conflict"]),
        inferences=unique_preserve_order(
            [*grouped_items["inference"], *[text for text in semantic_relations[:3]]]
        ),
        context_nodes=unique_preserve_order(semantic_context_nodes),
    )


def _merge_graph_contexts(primary: GraphContext, secondary: GraphContext) -> GraphContext:
    return GraphContext(
        entities=unique_preserve_order([*primary.entities, *secondary.entities]),
        relations=unique_preserve_order([*primary.relations, *secondary.relations]),
        decisions=unique_preserve_order([*primary.decisions, *secondary.decisions]),
        evidence=unique_preserve_order([*primary.evidence, *secondary.evidence]),
        alternatives=unique_preserve_order([*primary.alternatives, *secondary.alternatives]),
        risks=unique_preserve_order([*primary.risks, *secondary.risks]),
        conflicts=unique_preserve_order([*primary.conflicts, *secondary.conflicts]),
        inferences=unique_preserve_order([*primary.inferences, *secondary.inferences]),
        context_nodes=unique_preserve_order([*primary.context_nodes, *secondary.context_nodes]),
    )


def hybrid_retrieval(db_path: str | Path, question: str, entity_ids: list[str], depth: int = 2) -> GraphContext:
    graph_context = expand_graph_context(db_path, entity_ids, depth=depth)
    semantic_context = _semantic_context_search(db_path, question)
    return _merge_graph_contexts(graph_context, semantic_context)


def ask_question(db_path: str | Path, question: str) -> AnswerResult:
    query_started_at = perf_counter()
    intent = classify_intent(question)
    explanation = _resolve_explanation(db_path, question)
    matched_entity_rows = _lookup_entity_rows(db_path, question)
    detected_entities = unique_preserve_order(
        [
            *_candidate_terms(question)[1:],
            *[str(row["canonical_name"]) for row in matched_entity_rows],
        ]
    )

    with connect(db_path) as conn:
        decision_rows = find_decision_rows(conn, explanation.topic if explanation.decisions else question)
        decision_ids = [str(row["id"]) for row in decision_rows]
        matched_entity_ids = [str(row["id"]) for row in matched_entity_rows]
        sources = fetch_sources_for_decisions(conn, decision_ids)

    graph_seeds = unique_preserve_order([*matched_entity_ids, *decision_ids, *detected_entities])
    graph_context = hybrid_retrieval(db_path, question, graph_seeds, depth=2)
    memories = fetch_relevant_memories(db_path, question, entity_ids=unique_preserve_order([*matched_entity_ids, *decision_ids]))

    context_build_started_at = perf_counter()
    built_context = build_context_for_question(
        question,
        explanation,
        graph_context=graph_context,
        memories=memories,
        intent=intent,
        detected_entities=detected_entities,
        sources=sources,
    )
    log_metric("context_build_time_ms", (perf_counter() - context_build_started_at) * 1000)

    suggested_decision = ""
    if intent == "decision_support":
        suggested_decision = suggest_decision(built_context)
        context_build_started_at = perf_counter()
        built_context = build_context_for_question(
            question,
            explanation,
            graph_context=graph_context,
            memories=memories,
            intent=intent,
            suggested_decision=suggested_decision,
            detected_entities=detected_entities,
            sources=sources,
        )
        log_metric("context_build_time_ms", (perf_counter() - context_build_started_at) * 1000)

    provider = build_qa_provider_from_env()
    llm_started_at = perf_counter()
    if provider is not None:
        try:
            prompt = build_answer_prompt(question, built_context)
            answer = provider(prompt)
            log_metric("llm_time_ms", (perf_counter() - llm_started_at) * 1000)
            result = AnswerResult(
                question=question,
                answer=answer,
                degraded=False,
                sources=sources,
                structured=explanation,
                intent=intent,
                justification=unique_preserve_order([*built_context.evidence, *built_context.inferences])[:6],
                risks=unique_preserve_order([*built_context.risks, *built_context.conflicts])[:6],
                detected_entities=built_context.detected_entities,
                suggested_decision=suggested_decision,
                memories=built_context.memories,
                context_text=built_context.context_text,
                db_path=str(db_path),
            )
            save_reasoning_trace(result)
            log_metric("query_time_ms", (perf_counter() - query_started_at) * 1000)
            set_metric("graph_cache_hit_last_query", get_metrics_snapshot().get("graph_cache_hit", 0.0))
            return result
        except Exception:
            pass

    log_metric("llm_time_ms", (perf_counter() - llm_started_at) * 1000)
    result = AnswerResult(
        question=question,
        answer=_format_reasoned_answer(question, built_context, sources),
        degraded=True,
        sources=sources,
        structured=explanation,
        intent=intent,
        justification=unique_preserve_order([*built_context.evidence, *built_context.inferences])[:6],
        risks=unique_preserve_order([*built_context.risks, *built_context.conflicts])[:6],
        detected_entities=built_context.detected_entities,
        suggested_decision=suggested_decision,
        memories=built_context.memories,
        context_text=built_context.context_text,
        db_path=str(db_path),
    )
    save_reasoning_trace(result)
    log_metric("query_time_ms", (perf_counter() - query_started_at) * 1000)
    set_metric("graph_cache_hit_last_query", get_metrics_snapshot().get("graph_cache_hit", 0.0))
    return result


def explain_entity(db_path: str | Path, entity: str) -> EntityExplanation:
    topic_explanation = explain_topic(db_path, entity)

    with connect(db_path) as conn:
        matched_entity_rows = conn.execute(
            "SELECT id FROM entities WHERE canonical_name LIKE ? ORDER BY score DESC, id",
            (f"%{entity}%",),
        ).fetchall()
        matched_entity_ids = [str(row["id"]) for row in matched_entity_rows]
        decision_ids = [str(row["id"]) for row in find_decision_rows(conn, entity)]
        related_ids = unique_preserve_order([*matched_entity_ids, *decision_ids])
        if not related_ids:
            return EntityExplanation(entity=entity)

        relation_rows = fetch_entity_relations(conn, related_ids)
        context_rows = fetch_decision_context(conn, decision_ids) if decision_ids else []
        history_rows = fetch_history(conn, related_ids)

    relations = [
        f"{row['subject_type']}({row['subject_name']}) --{row['predicate']}--> {row['object_type']}({row['object_name']})"
        for row in relation_rows
    ]
    context = [f"{row['predicate']}: {row['content']}" for row in context_rows]
    conflicts = [
        row["content"]
        for row in context_rows
        if row["predicate"] == "contradicts" or row["node_type"] == "conflict"
    ]

    return EntityExplanation(
        entity=entity,
        relations=unique_preserve_order(relations),
        decisions=unique_preserve_order(topic_explanation.decisions),
        context=unique_preserve_order(context),
        history=unique_preserve_order([str(row["content"]) for row in history_rows]),
        conflicts=unique_preserve_order(conflicts),
    )
