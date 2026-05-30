from __future__ import annotations

from dataclasses import dataclass, field

from brain4me.models import EntityExplanation, GraphContext, SourceReference, TopicExplanation
from brain4me.metrics import log_metric
from brain4me.query_helpers import unique_preserve_order


@dataclass
class BuiltContext:
    question: str
    context_text: str
    sources: list[SourceReference]
    score: float
    degraded: bool = False
    intent: str = "exploration"
    decisions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    detected_entities: list[str] = field(default_factory=list)
    suggested_decision: str = ""


def _rank_decisions_with_memories(decisions: list[str], memories: list[str]) -> list[str]:
    indexed = list(enumerate(unique_preserve_order(decisions)))

    def memory_score(decision: str) -> int:
        lowered_decision = decision.lower()
        score = 0
        for memory in memories:
            lowered_memory = memory.lower()
            if lowered_decision not in lowered_memory:
                continue
            if "padrao aceito" in lowered_memory:
                score += 2
            if "padrao rejeitado" in lowered_memory:
                score -= 2
        return score

    indexed.sort(key=lambda item: (-memory_score(item[1]), item[0]))
    return [decision for _, decision in indexed]


def _memory_learning_summary(memories: list[str]) -> list[str]:
    summaries: list[str] = []
    for memory in memories:
        lowered_memory = memory.lower()
        accepted = 0
        rejected = 0
        for marker, target in (("aceitas=", "accepted"), ("rejeitadas=", "rejected")):
            if marker in lowered_memory:
                try:
                    value = int(lowered_memory.split(marker, 1)[1].split("|", 1)[0].strip())
                except Exception:
                    value = 0
                if target == "accepted":
                    accepted = value
                else:
                    rejected = value

        decision_head = memory.split("|", 1)[0].strip()
        if ":" in decision_head:
            decision_head = decision_head.split(":", 1)[1].strip()
        if not decision_head:
            continue

        summaries.append(
            f"{decision_head}: aceita {accepted} vez(es), rejeitada {rejected} vez(es)."
        )
    return unique_preserve_order(summaries)


def _build_sections(explanation: TopicExplanation | EntityExplanation) -> list[tuple[str, list[str]]]:
    if isinstance(explanation, TopicExplanation):
        return [
            ("Decis\u00f5es", explanation.decisions),
            ("Evid\u00eancias", explanation.evidence),
            ("Riscos", explanation.risks),
            ("Alternativas", explanation.alternatives),
        ]
    return [
        ("Decis\u00f5es", explanation.decisions),
        ("Contexto", explanation.context),
        ("Hist\u00f3rico", explanation.history),
        ("Conflitos", explanation.conflicts),
        ("Rela\u00e7\u00f5es", explanation.relations),
    ]


def _merge_section_items(
    explanation: TopicExplanation | EntityExplanation,
    graph_context: GraphContext,
    memories: list[str],
) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str]]:
    decisions = _rank_decisions_with_memories([*explanation.decisions, *graph_context.decisions], memories)

    if isinstance(explanation, TopicExplanation):
        evidence = unique_preserve_order([*explanation.evidence, *graph_context.evidence])
        alternatives = unique_preserve_order([*explanation.alternatives, *graph_context.alternatives])
        risks = unique_preserve_order([*explanation.risks, *graph_context.risks])
        conflicts = unique_preserve_order(graph_context.conflicts)
    else:
        evidence = unique_preserve_order([*explanation.context, *graph_context.evidence])
        alternatives = unique_preserve_order([*explanation.relations, *graph_context.alternatives])
        risks = unique_preserve_order([*explanation.conflicts, *graph_context.risks])
        conflicts = unique_preserve_order([*explanation.conflicts, *graph_context.conflicts])

    entities = unique_preserve_order(graph_context.entities)
    return decisions, evidence, alternatives, risks, conflicts, entities


def build_context_for_question(
    question: str,
    explanation: TopicExplanation | EntityExplanation,
    *,
    graph_context: GraphContext | None = None,
    memories: list[str] | None = None,
    intent: str = "exploration",
    suggested_decision: str = "",
    detected_entities: list[str] | None = None,
    sources: list[SourceReference] | None = None,
    max_chars: int = 12000,
) -> BuiltContext:
    graph_context = graph_context or GraphContext()
    memories = unique_preserve_order(memories or [])
    detected_entities = detected_entities or []

    sections = _build_sections(explanation)
    ranked_decisions = _rank_decisions_with_memories([*explanation.decisions, *graph_context.decisions], memories)
    enriched_sections = [
        *( [("Decisao sugerida", [suggested_decision])] if suggested_decision else [] ),
        *( [("Decis\u00f5es influenciadas por mem\u00f3ria", ranked_decisions)] if ranked_decisions else [] ),
        *sections,
        ("Decis\u00f5es recentes", graph_context.decisions),
        ("Conflitos", graph_context.conflicts),
        ("Infer\u00eancias", graph_context.inferences),
        ("Aprendizado consolidado", _memory_learning_summary(memories)),
        ("Mem\u00f3ria relevante", memories),
        ("Entidades conectadas", graph_context.entities),
    ]

    nonempty = sum(1 for _, items in enriched_sections if items)
    score = nonempty / len(enriched_sections) if enriched_sections else 0.0

    if isinstance(explanation, TopicExplanation):
        degraded = not explanation.decisions and not explanation.evidence and not graph_context.decisions
    else:
        degraded = not explanation.decisions and not explanation.context and not graph_context.decisions

    parts: list[str] = []
    total_chars = 0

    for heading, items in enriched_sections:
        if not items:
            continue
        section_lines = [f"### {heading}"] + [f"- {item}" for item in unique_preserve_order(items)]
        section_text = "\n".join(section_lines)
        separator = 2 if parts else 0
        needed = len(section_text) + separator
        if total_chars + needed > max_chars:
            remaining = max_chars - total_chars - separator
            if remaining > len(f"### {heading}\n") and parts:
                parts.append(section_text[: remaining - 3] + "...")
            elif not parts and remaining > 0:
                parts.append(section_text[:remaining])
            break
        if parts:
            total_chars += 2
        parts.append(section_text)
        total_chars += len(section_text)

    context_text = "\n\n".join(parts)
    if not context_text:
        for _, items in enriched_sections:
            if items:
                context_text = items[0]
                break

    log_metric("context_size_chars", len(context_text))

    decisions, evidence, alternatives, risks, conflicts, entities = _merge_section_items(
        explanation,
        graph_context,
        memories,
    )

    return BuiltContext(
        question=question,
        context_text=context_text,
        sources=sources or [],
        score=score,
        degraded=degraded,
        intent=intent,
        decisions=decisions,
        evidence=evidence,
        alternatives=alternatives,
        risks=risks,
        conflicts=conflicts,
        memories=memories,
        inferences=unique_preserve_order(graph_context.inferences),
        detected_entities=unique_preserve_order([*detected_entities, *entities]),
        suggested_decision=suggested_decision,
    )


def build_answer_prompt(question: str, context: BuiltContext) -> str:
    insufficient = context.degraded or not context.context_text.strip()

    if insufficient:
        context_block = (
            "[CONTEXTO INSUFICIENTE: nao ha informacoes suficientes registradas para responder esta pergunta.]"
        )
        instruction_extra = (
            "O contexto disponivel e insuficiente. Informe ao usuario que nao ha informacoes suficientes "
            "para responder com precisao. Nao invente dados."
        )
    else:
        source_lines = [f"- {src.title or src.source_path}" for src in context.sources]
        sources_block = "\n".join(source_lines) if source_lines else "(nenhuma fonte registrada)"
        metadata_lines = [
            f"- Intent: {context.intent}",
            f"- Entidades detectadas: {', '.join(context.detected_entities) if context.detected_entities else '(nenhuma)'}",
        ]
        if context.suggested_decision:
            metadata_lines.append(f"- Decisao sugerida: {context.suggested_decision}")
        metadata_block = "\n".join(metadata_lines)
        context_block = (
            f"{context.context_text}\n\n**Metadados de raciocinio:**\n{metadata_block}\n\n"
            f"**Fontes disponiveis:**\n{sources_block}"
        )
        instruction_extra = (
            "Use somente o contexto fornecido. Nao invente informacoes. "
            "Cite as fontes pelo titulo ou caminho quando disponiveis."
        )

    return (
        "Voce e um assistente de segundo cerebro. Responda em portugues brasileiro.\n"
        f"{instruction_extra}\n\n"
        "Formate sua resposta exatamente assim:\n\n"
        "## Resposta direta\n"
        "[resposta objetiva aqui]\n\n"
        "## Justificativa\n"
        "[justificativa baseada no contexto]\n\n"
        "## Riscos e conflitos\n"
        "[riscos e conflitos identificados, ou 'Nenhum identificado']\n\n"
        "## Proximos passos\n"
        "[sugestoes de proximos passos, ou 'Nenhum identificado']\n\n"
        "## Fontes\n"
        "[lista de fontes citadas]\n\n"
        "---\n\n"
        f"**Pergunta:** {question}\n\n"
        f"**Contexto:**\n{context_block}"
    )
