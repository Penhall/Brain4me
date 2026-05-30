from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import click

from .graph_cache import get_cache_snapshot, invalidate_cache
from .graphs import build_context_graph, build_knowledge_graph
from .ingest import ingest_markdown_note
from .metrics import get_metrics_snapshot
from .memory_governance import list_patterns, remove_pattern, update_pattern_score
from .query import ask_question, explain_entity, explain_topic
from .snapshot import build_snapshot_payload
from .storage import connect, initialize_database


@click.group()
def cli() -> None:
    """CLI inicial do MVP Brain4me."""


def _pattern_bucket(pattern: dict[str, Any]) -> str:
    if bool(pattern.get("is_unstable")):
        return "unstable"
    if int(pattern.get("rejected_count", 0)) > int(pattern.get("accepted_count", 0)):
        return "rejected"
    return "strong"


def _print_topic_explanation(explanation) -> None:
    click.echo(f"Topic: {explanation.topic}")
    if not explanation.decisions:
        click.echo("No decision context found.")
        return

    click.echo("Decisions:")
    for decision in explanation.decisions:
        click.echo(f"- {decision}")

    click.echo("Evidence:")
    for item in explanation.evidence:
        click.echo(f"- {item}")

    click.echo("Alternatives:")
    for item in explanation.alternatives:
        click.echo(f"- {item}")

    click.echo("Risks:")
    for item in explanation.risks:
        click.echo(f"- {item}")


def _print_json_payload(payload) -> None:
    click.echo(json.dumps(asdict(payload), ensure_ascii=False, sort_keys=True))


def _build_summary_payload(db_path: Path) -> dict[str, Any]:
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
    }


def _build_markdown_note(
    *,
    title: str,
    compartment: str,
    body_lines: list[str],
) -> str:
    frontmatter = [
        "---",
        f"title: {title}",
        f"compartment: {compartment}",
        "source_type: markdown",
        "source_origin_type: personal",
        "---",
    ]
    return "\n".join([*frontmatter, "", *body_lines, ""])


def _ingest_file(db_path: Path, file_path: Path) -> None:
    markdown_text = file_path.read_text(encoding="utf-8")
    result = ingest_markdown_note(
        db_path=db_path,
        markdown_text=markdown_text,
        source_path=str(file_path),
    )
    click.echo(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))


@cli.command("init-db")
@click.option("--db", "db_path", required=True, type=click.Path(path_type=Path))
def init_db_command(db_path: Path) -> None:
    initialize_database(db_path)
    click.echo(f"Initialized database at {db_path}")


@cli.command("ingest-markdown")
@click.option("--db", "db_path", required=True, type=click.Path(path_type=Path))
@click.option("--file", "file_path", required=True, type=click.Path(exists=True, path_type=Path))
def ingest_markdown_command(db_path: Path, file_path: Path) -> None:
    _ingest_file(db_path, file_path)


@cli.command("ingest")
@click.option("--db", "db_path", required=True, type=click.Path(path_type=Path))
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def ingest_command(db_path: Path, file_path: Path) -> None:
    _ingest_file(db_path, file_path)


@cli.command("explain-topic")
@click.option("--db", "db_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--topic", required=True)
def explain_topic_command(db_path: Path, topic: str) -> None:
    explanation = explain_topic(db_path, topic)
    _print_topic_explanation(explanation)


@cli.command("ask")
@click.option("--db", "db_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, default=False)
@click.argument("question")
def ask_command(db_path: Path, as_json: bool, question: str) -> None:
    result = ask_question(db_path, question)
    if as_json:
        payload = {
            "question": result.question,
            "answer": result.answer,
            "degraded": result.degraded,
            "sources": [asdict(s) for s in result.sources],
            "structured": asdict(result.structured),
            "intent": result.intent,
            "justification": result.justification,
            "risks": result.risks,
            "detected_entities": result.detected_entities,
            "suggested_decision": result.suggested_decision,
            "memories": result.memories,
        }
        click.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    click.echo(result.answer)
    if result.degraded:
        click.echo("[Modo degradado: LLM não disponível ou falhou]")
    if result.sources:
        click.echo("Fontes:")
        for source in result.sources:
            label_text = source.title if source.title else source.source_path
            click.echo(f"- {label_text} ({source.label})")
    if result.suggested_decision:
        click.echo("Decisao sugerida:")
        click.echo(result.suggested_decision)


@cli.command("explain")
@click.option("--db", "db_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, default=False)
@click.argument("entity")
def explain_command(db_path: Path, as_json: bool, entity: str) -> None:
    explanation = explain_entity(db_path, entity)
    if as_json:
        _print_json_payload(explanation)
        return
    click.echo(f"Entity: {explanation.entity}")
    click.echo("Decisions:")
    for item in explanation.decisions:
        click.echo(f"- {item}")
    click.echo("Relations:")
    for item in explanation.relations:
        click.echo(f"- {item}")
    click.echo("Context:")
    for item in explanation.context:
        click.echo(f"- {item}")
    click.echo("History:")
    for item in explanation.history:
        click.echo(f"- {item}")
    click.echo("Conflicts:")
    for item in explanation.conflicts:
        click.echo(f"- {item}")


@cli.command("fact")
@click.option("--db", "db_path", required=True, type=click.Path(path_type=Path))
@click.option("--compartment", default="inbox")
@click.argument("fact_text")
def fact_command(db_path: Path, compartment: str, fact_text: str) -> None:
    markdown_text = _build_markdown_note(
        title="Fato manual",
        compartment=compartment,
        body_lines=["Evidencia: " + fact_text],
    )
    result = ingest_markdown_note(
        db_path=db_path,
        markdown_text=markdown_text,
        source_path=f"manual://fact/{fact_text[:20]}",
    )
    click.echo(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))


@cli.command("log")
@click.option("--db", "db_path", required=True, type=click.Path(path_type=Path))
@click.option("--compartment", default="inbox")
@click.argument("event_text")
def log_command(db_path: Path, compartment: str, event_text: str) -> None:
    markdown_text = _build_markdown_note(
        title="Log manual",
        compartment=compartment,
        body_lines=["Evidencia: " + event_text],
    )
    result = ingest_markdown_note(
        db_path=db_path,
        markdown_text=markdown_text,
        source_path=f"manual://log/{event_text[:20]}",
    )
    click.echo(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))


@cli.command("decide")
@click.option("--db", "db_path", required=True, type=click.Path(path_type=Path))
@click.option("--compartment", default="inbox")
@click.option("--project")
@click.option("--problem")
@click.option("--evidence", multiple=True)
@click.option("--alternative", multiple=True)
@click.option("--risk", multiple=True)
@click.argument("decision_text")
def decide_command(
    db_path: Path,
    compartment: str,
    project: str | None,
    problem: str | None,
    evidence: tuple[str, ...],
    alternative: tuple[str, ...],
    risk: tuple[str, ...],
    decision_text: str,
) -> None:
    body_lines = ["Decisao: " + decision_text]
    if project:
        body_lines.insert(0, "Projeto: " + project)
    if problem:
        insert_at = 1 if project else 0
        body_lines.insert(insert_at, "Problema: " + problem)
    body_lines.extend("Evidencia: " + item for item in evidence)
    body_lines.extend("Alternativa: " + item for item in alternative)
    body_lines.extend("Risco: " + item for item in risk)
    markdown_text = _build_markdown_note(
        title="Decisao manual",
        compartment=compartment,
        body_lines=body_lines,
    )
    result = ingest_markdown_note(
        db_path=db_path,
        markdown_text=markdown_text,
        source_path=f"manual://decide/{decision_text[:20]}",
    )
    click.echo(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))


@cli.command("summary")
@click.option("--db", "db_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, default=False)
def summary_command(db_path: Path, as_json: bool) -> None:
    payload = _build_summary_payload(db_path)
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return

    for label, value in payload["counts"].items():
        click.echo(f"{label}: {value}")

    knowledge = payload["graphs"]["knowledge"]
    context = payload["graphs"]["context"]
    click.echo(f"Knowledge Graph: {knowledge['nodes']} nodes, {knowledge['edges']} edges")
    click.echo(f"Context Graph: {context['nodes']} nodes, {context['edges']} edges")


@cli.command("export")
@click.option("--db", "db_path", required=True, type=click.Path(exists=True, path_type=Path))
def export_command(db_path: Path) -> None:
    click.echo(json.dumps(build_snapshot_payload(db_path), ensure_ascii=False, sort_keys=True))


@cli.command("metrics")
@click.option("--db", "db_path", required=False, type=click.Path(path_type=Path))
def metrics_command(db_path: Path | None) -> None:
    payload = {
        "metrics": get_metrics_snapshot(),
        "cache": get_cache_snapshot(db_path) if db_path is not None else get_cache_snapshot(),
    }
    click.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))


@cli.group("cache")
def cache_group() -> None:
    """Operacoes de cache em memoria."""


@cache_group.command("clear")
def cache_clear_command() -> None:
    invalidate_cache()
    click.echo("Graph cache cleared.")


@cli.group("memory")
@click.option("--db", "db_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.pass_context
def memory_group(ctx: click.Context, db_path: Path) -> None:
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path


@memory_group.command("list")
@click.option("--limit", default=20, type=int)
@click.pass_context
def memory_list_command(ctx: click.Context, limit: int) -> None:
    patterns = list_patterns(ctx.obj["db_path"], limit=limit)
    if not patterns:
        click.echo("Nenhum padrao encontrado.")
        return
    for pattern in patterns:
        click.echo(
            f"{pattern['id']} | score={pattern['final_score']:.2f} | "
            f"confidence={pattern['confidence_score']:.2f} | {pattern['content']}"
        )


@memory_group.command("remove")
@click.argument("pattern_id")
@click.pass_context
def memory_remove_command(ctx: click.Context, pattern_id: str) -> None:
    remove_pattern(ctx.obj["db_path"], pattern_id)
    click.echo(f"Pattern removed: {pattern_id}")


@memory_group.command("review")
@click.option("--limit", default=20, type=int)
@click.pass_context
def memory_review_command(ctx: click.Context, limit: int) -> None:
    patterns = list_patterns(ctx.obj["db_path"], limit=limit)
    buckets = {"strong": [], "rejected": [], "unstable": []}
    for pattern in patterns:
        buckets[_pattern_bucket(pattern)].append(pattern)

    click.echo("Fortes:")
    if buckets["strong"]:
        for pattern in buckets["strong"]:
            click.echo(f"- {pattern['content']}")
    else:
        click.echo("- Nenhum")

    click.echo("Rejeitados:")
    if buckets["rejected"]:
        for pattern in buckets["rejected"]:
            click.echo(f"- {pattern['content']}")
    else:
        click.echo("- Nenhum")

    click.echo("Instaveis:")
    if buckets["unstable"]:
        for pattern in buckets["unstable"]:
            click.echo(f"- {pattern['content']}")
    else:
        click.echo("- Nenhum")
