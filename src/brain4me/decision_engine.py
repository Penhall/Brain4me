from __future__ import annotations

import re

from .context_builder import BuiltContext
from .llm_client import build_qa_provider_from_env
from .memory import apply_feedback_penalty


def _memory_stats_for_decision(decision: str, memories: list[str]) -> tuple[int, int]:
    accepted = 0
    rejected = 0
    lowered_decision = decision.lower()
    for memory in memories:
        if lowered_decision not in memory.lower():
            continue
        accepted_match = re.search(r"aceitas=(\d+)", memory)
        rejected_match = re.search(r"rejeitadas=(\d+)", memory)
        if accepted_match:
            accepted += int(accepted_match.group(1))
        elif "padrao aceito" in memory.lower():
            accepted += 1
        if rejected_match:
            rejected += int(rejected_match.group(1))
        elif "padrao rejeitado" in memory.lower():
            rejected += 1
    return accepted, rejected


def _rank_decisions(context: BuiltContext) -> list[str]:
    ranked: list[tuple[float, int, str]] = []
    for index, decision in enumerate(context.decisions):
        accepted, rejected = _memory_stats_for_decision(decision, context.memories)
        penalty = apply_feedback_penalty(decision, context.memories)
        stability_bonus = accepted - rejected
        rank_score = penalty * (1 + (stability_bonus * 0.2))
        ranked.append((rank_score, -index, decision))
    ranked.sort(key=lambda item: (-item[0], -item[1]))
    return [decision for _, _, decision in ranked]


def _build_decision_prompt(context: BuiltContext) -> str:
    memory_block = "\n".join(f"- {item}" for item in context.memories) if context.memories else "(nenhuma memoria relevante)"
    return (
        "Voce e um analista de decisoes. Use apenas o contexto fornecido.\n"
        "Considere memoria historica, penalize decisoes rejeitadas e priorize padroes estaveis.\n"
        "Explique quantas vezes a recomendacao foi aceita ou rejeitada quando essa informacao existir.\n"
        "Responda em portugues brasileiro com uma recomendacao curta, alternativas e riscos.\n\n"
        f"Pergunta: {context.question}\n\n"
        f"Contexto:\n{context.context_text}\n\n"
        f"Memoria historica:\n{memory_block}\n\n"
        "Formato esperado:\n"
        "Recomendacao: ...\n"
        "Alternativas: ...\n"
        "Riscos: ...\n"
        "Baseado em aprendizado: ...\n"
        "Base: ..."
    )


def _fallback_suggestion(context: BuiltContext) -> str:
    ranked_decisions = _rank_decisions(context)
    recommendation = ranked_decisions[0] if ranked_decisions else "Nao ha decisao registrada suficiente para recomendar um caminho"
    alternatives = ", ".join(context.alternatives[:3]) if context.alternatives else "nenhuma alternativa registrada"
    risks = ", ".join(context.risks[:3]) if context.risks else "nenhum risco explicito"

    accepted, rejected = _memory_stats_for_decision(recommendation, context.memories)
    learning_summary = (
        f"Baseado em aprendizado: esta decisao foi aceita {accepted} vezes, rejeitada {rejected} vezes."
        if accepted or rejected
        else "Baseado em aprendizado: nao ha historico forte o suficiente para esta decisao."
    )

    base_parts: list[str] = []
    if context.evidence:
        base_parts.append("evidencias: " + "; ".join(context.evidence[:2]))
    if context.inferences:
        base_parts.append("inferencias: " + "; ".join(context.inferences[:2]))
    if context.memories:
        base_parts.append("decisoes anteriores: " + "; ".join(context.memories[:2]))
    if not base_parts:
        base_parts.append("base insuficiente")

    return (
        f"Recomendacao: {recommendation}. "
        f"Alternativas: {alternatives}. "
        f"Riscos: {risks}. "
        f"{learning_summary} "
        f"Base: {' | '.join(base_parts)}."
    )


def suggest_decision(context: BuiltContext) -> str:
    provider = build_qa_provider_from_env()
    if provider is not None:
        try:
            return provider(_build_decision_prompt(context))
        except Exception:
            pass
    return _fallback_suggestion(context)
