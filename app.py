from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from brain4me.feedback import fetch_recent_feedback_entries, record_feedback
from brain4me.graph_cache import get_cache_snapshot, get_cached_graphs
from brain4me.graph_viz import build_graph_html
from brain4me.metrics import get_metrics_snapshot
from brain4me.memory_governance import list_patterns, remove_pattern
from brain4me.query import ask_question
from brain4me.reasoning_log import fetch_recent_reasoning_traces


DEFAULT_DB_PATH = str(ROOT / "brain4me.db")


def _render_items(items: list[str], empty_text: str) -> None:
    if not items:
        st.write(empty_text)
        return
    for item in items:
        st.write(f"- {item}")


def _bucket_patterns(patterns: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    buckets = {"strong": [], "rejected": [], "unstable": []}
    for pattern in patterns:
        if bool(pattern.get("is_unstable")):
            buckets["unstable"].append(pattern)
        elif int(pattern.get("rejected_count", 0)) > int(pattern.get("accepted_count", 0)):
            buckets["rejected"].append(pattern)
        else:
            buckets["strong"].append(pattern)
    return buckets


st.set_page_config(page_title="Brain4me", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .brain-card {
        background: linear-gradient(180deg, #ffffff 0%, #f5f8fc 100%);
        border: 1px solid #d9e2ec;
        border-radius: 18px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    }
    .brain-kicker {
        color: #486581;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "feedback_message" not in st.session_state:
    st.session_state.feedback_message = ""

with st.sidebar:
    st.markdown("## Painel")
    db_path = st.text_input("Banco de dados", value=DEFAULT_DB_PATH)

    st.markdown("### Historico de perguntas")
    if st.session_state.history:
        for item in st.session_state.history[:10]:
            st.write(f"- {item}")
    else:
        st.write("Nenhuma pergunta ainda.")

    traces = fetch_recent_reasoning_traces(db_path, limit=5)
    st.markdown("### Historico de decisoes")
    if traces:
        for trace in traces:
            decision_text = trace["suggested_decision"] or "(sem decisao sugerida)"
            st.write(f"- {decision_text}")
    else:
        st.write("Nenhuma decisao registrada.")

    st.markdown("## Aprendizado do sistema")
    patterns = list_patterns(db_path, limit=12)
    buckets = _bucket_patterns(patterns)

    st.markdown("### Padroes fortes")
    if buckets["strong"]:
        for pattern in buckets["strong"][:5]:
            st.write(f"- {pattern['content']}")
    else:
        st.write("Nenhum.")

    st.markdown("### Padroes rejeitados")
    if buckets["rejected"]:
        for pattern in buckets["rejected"][:5]:
            st.write(f"- {pattern['content']}")
    else:
        st.write("Nenhum.")

    st.markdown("### Padroes instaveis")
    if buckets["unstable"]:
        for pattern in buckets["unstable"][:5]:
            st.write(f"- {pattern['content']}")
    else:
        st.write("Nenhum.")

    if patterns:
        options = {f"{pattern['decision_text']} ({pattern['id'][:8]})": pattern["id"] for pattern in patterns}
        selected_label = st.selectbox("Excluir padrao", list(options.keys()))
        if st.button("Excluir padrao selecionado"):
            remove_pattern(db_path, options[selected_label])
            st.session_state.feedback_message = "Padrao removido da memoria ativa."

    st.markdown("## Performance")
    metrics = get_metrics_snapshot()
    cache_snapshot = get_cache_snapshot(db_path)
    st.write(f"Tempo da ultima consulta: {metrics.get('query_time_ms', 0.0)} ms")
    st.write(f"Build de contexto: {metrics.get('context_build_time_ms', 0.0)} ms")
    st.write(f"LLM: {metrics.get('llm_time_ms', 0.0)} ms")
    st.write(f"Tamanho do contexto: {int(metrics.get('context_size_chars', 0.0))} chars")
    st.write(f"Cache usado: {'sim' if metrics.get('cache_used') else 'nao'}")
    if cache_snapshot.get("loaded"):
        st.write(
            f"Grafos em cache: KG {cache_snapshot.get('knowledge_nodes', 0)}n/"
            f"{cache_snapshot.get('knowledge_edges', 0)}e, "
            f"CG {cache_snapshot.get('context_nodes', 0)}n/{cache_snapshot.get('context_edges', 0)}e"
        )

st.markdown('<div class="brain-kicker">Fase 5 • aprendizado controlado e memoria inteligente</div>', unsafe_allow_html=True)
st.title("Brain4me")
question = st.text_input("Faca uma pergunta ao seu Brain4me")

if st.button("Consultar", type="primary") and question.strip():
    result = ask_question(db_path, question.strip())
    st.session_state.last_result = result
    st.session_state.history = [question.strip(), *st.session_state.history]
    st.session_state.feedback_message = ""

result = st.session_state.last_result
if result is not None:
    if st.session_state.feedback_message:
        st.info(st.session_state.feedback_message)

    main_col, side_col = st.columns([1.8, 1.0], gap="large")

    with main_col:
        st.markdown('<div class="brain-card">', unsafe_allow_html=True)
        st.markdown("## Resposta")
        st.markdown(result.answer)
        st.markdown("</div>", unsafe_allow_html=True)

        feedback_col1, feedback_col2 = st.columns(2, gap="medium")
        with feedback_col1:
            if st.button("Aceitar"):
                record_feedback(result.question, True, db_path=db_path)
                st.session_state.feedback_message = "Feedback aceito registrado."
        with feedback_col2:
            if st.button("Rejeitar"):
                record_feedback(result.question, False, db_path=db_path)
                st.session_state.feedback_message = "Feedback de rejeicao registrado."

        correction = st.text_input("Corrigir resposta", key="correction_input")
        if st.button("Salvar correcao"):
            record_feedback(result.question, False, correction, db_path=db_path)
            st.session_state.feedback_message = "Correcao registrada e convertida em memoria."

        left_col, right_col = st.columns(2, gap="large")
        with left_col:
            st.markdown("## Justificativa")
            _render_items(result.justification, "Nenhuma justificativa registrada.")
        with right_col:
            st.markdown("## Riscos")
            _render_items(result.risks, "Nenhum risco registrado.")

        st.markdown("## Fontes")
        if result.sources:
            for source in result.sources:
                label = source.title or source.source_path or source.label
                st.write(f"- {label}")
        else:
            st.write("Nenhuma fonte registrada.")

        # Graph visualization
        cache = get_cached_graphs(db_path)
        if cache.kg and cache.kg.number_of_nodes() > 0:
            with st.expander("🗺️ Knowledge Graph", expanded=False):
                entities = result.detected_entities if result.detected_entities else None
                graph_html = build_graph_html(cache, highlight_entities=entities)
                if graph_html:
                    st.components.v1.html(graph_html, height=620, scrolling=False)

    with side_col:
        st.markdown("## Sinalizacao")
        st.write(f"Intent: `{result.intent}`")
        st.markdown("### Entidades detectadas")
        _render_items(result.detected_entities, "Nenhuma entidade detectada.")

        st.markdown("### Decisao sugerida")
        st.write(result.suggested_decision or "Nenhuma sugestao gerada.")

        st.markdown("### Memoria relevante")
        _render_items(result.memories, "Nenhuma memoria relevante.")

        st.markdown("### Feedback recente")
        feedback_rows = fetch_recent_feedback_entries(db_path, limit=5)
        if feedback_rows:
            for row in feedback_rows:
                correction_text = f" -> {row['correction']}" if row["correction"] else ""
                st.write(f"- {row['feedback_type']}: {row['question']}{correction_text}")
        else:
            st.write("Nenhum feedback registrado.")
