from pathlib import Path
import sys
import json
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from click.testing import CliRunner

from brain4me.cli import cli
from brain4me.context_builder import BuiltContext, build_answer_prompt, build_context_for_question
from brain4me.decision_engine import suggest_decision
from brain4me.ingest import ingest_markdown_note
from brain4me.intent import classify_intent
from brain4me.memory import fetch_relevant_memories
from brain4me.models import SourceReference, TopicExplanation
from brain4me.query import ask_question, expand_graph_context
from brain4me.storage import initialize_database
from tests.conftest import (
    CONFLICTING_DECISION_NOTE,
    INFERENCE_NOTE,
    SAMPLE_NOTE,
    WorkspaceTempDirTestCase,
)


class Phase3Tests(WorkspaceTempDirTestCase):
    def test_classify_intent_distinguishes_decision_risk_and_exploration(self):
        self.assertEqual(
            classify_intent("Qual decisao devo tomar sobre persistencia do MVP?"),
            "decision_support",
        )
        self.assertEqual(
            classify_intent("Quais riscos existem em manter SQLite agora?"),
            "risk_analysis",
        )
        self.assertEqual(
            classify_intent("Explore conexoes entre SQLite e Neo4j no Brain4me"),
            "exploration",
        )

    def test_expand_graph_context_collects_entities_conflicts_and_inferences(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=CONFLICTING_DECISION_NOTE,
            source_path="notes/banco-mvp-conflict.md",
        )
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=INFERENCE_NOTE,
            source_path="notes/inference.md",
        )

        graph_context = expand_graph_context(db_path, ["SQLite"], depth=2)

        self.assertIn("SQLite", graph_context.entities)
        self.assertTrue(any("Neo4j" in item for item in graph_context.entities))
        self.assertTrue(any("Conflito detectado" in item for item in graph_context.conflicts))
        self.assertTrue(any("menor atrito operacional" in item for item in graph_context.inferences))

    def test_fetch_relevant_memories_returns_decision_history_for_question(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        memories = fetch_relevant_memories(db_path, "O que foi decidido sobre SQLite?")

        self.assertTrue(memories)
        self.assertTrue(any("Decisao registrada" in item for item in memories))

    def test_suggest_decision_uses_context_without_llm(self):
        context = BuiltContext(
            question="Qual decisao devo tomar sobre persistencia?",
            context_text="### Decisoes\n- usar SQLite no MVP\n\n### Alternativas\n- Neo4j",
            sources=[],
            score=0.8,
            degraded=False,
            decisions=["usar SQLite no MVP"],
            evidence=["reduz complexidade operacional"],
            alternatives=["Neo4j"],
            risks=["consultas relacionais avancadas podem exigir revisao futura"],
            conflicts=[],
            memories=["Decisao registrada: usar SQLite no MVP"],
            inferences=["priorizar o menor atrito operacional no inicio"],
            detected_entities=["SQLite", "Neo4j"],
            intent="decision_support",
        )

        suggestion = suggest_decision(context)

        self.assertIn("SQLite", suggestion)
        self.assertIn("Neo4j", suggestion)
        self.assertIn("risco", suggestion.lower())

    def test_ask_question_returns_reasoning_metadata_and_suggested_decision(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=INFERENCE_NOTE,
            source_path="notes/inference.md",
        )

        with patch("brain4me.query.build_qa_provider_from_env", return_value=None):
            result = ask_question(db_path, "Qual decisao devo tomar sobre a persistencia inicial?")

        self.assertEqual(result.intent, "decision_support")
        self.assertTrue(result.detected_entities)
        self.assertTrue(result.justification)
        self.assertTrue(result.risks)
        self.assertTrue(result.memories)
        self.assertNotEqual(result.suggested_decision.strip(), "")
        self.assertIn("Fontes", result.answer)
    # ------------------------------------------------------------------
    # Teste 1: QA provider não usa prompt de extração
    # ------------------------------------------------------------------
    def test_qa_provider_sends_qa_system_prompt_not_extraction(self):
        from brain4me.llm_client import QAResponseProvider

        captured = {}

        def capture_post(url, headers, body):
            captured["body"] = body
            return {"choices": [{"message": {"content": "resposta"}}]}

        provider = QAResponseProvider(api_key="key", model="gpt-4", http_post=capture_post)
        provider("Pergunta de teste")

        messages = captured["body"]["messages"]
        system_msg = next(m for m in messages if m["role"] == "system")
        self.assertNotIn("JSON", system_msg["content"])
        self.assertNotIn("entities", system_msg["content"])
        self.assertIn("segundo cérebro", system_msg["content"])

    # ------------------------------------------------------------------
    # Teste 2: fontes chegam ao context builder
    # ------------------------------------------------------------------
    def test_sources_passed_to_context_builder_appear_in_built_context(self):
        explanation = TopicExplanation(
            topic="SQLite",
            decisions=["usar SQLite no MVP"],
        )
        sources = [
            SourceReference(note_id="1", source_path="notes/test.md", title="Test Note", label="nota")
        ]

        result = build_context_for_question("Pergunta?", explanation, sources=sources)

        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.sources[0].title, "Test Note")

    # ------------------------------------------------------------------
    # Teste 3: fontes aparecem no prompt do LLM
    # ------------------------------------------------------------------
    def test_sources_appear_in_answer_prompt_text(self):
        source = SourceReference(
            note_id="1", source_path="notes/test.md", title="Nota Importante", label="nota"
        )
        context = BuiltContext(
            question="Pergunta?",
            context_text="### Decisões\n- usar SQLite",
            sources=[source],
            score=0.5,
            degraded=False,
        )

        prompt = build_answer_prompt("Pergunta?", context)

        self.assertIn("Nota Importante", prompt)

    # ------------------------------------------------------------------
    # Teste 4: CLI ask --json retorna AnswerResult completo
    # ------------------------------------------------------------------
    def test_cli_ask_json_returns_full_answer_result_fields(self):
        db_path = self.temp_dir / "test.db"
        note_path = self.temp_dir / "banco-mvp.md"
        note_path.write_text(SAMPLE_NOTE, encoding="utf-8")

        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])
        runner.invoke(cli, ["ingest", "--db", str(db_path), str(note_path)])

        ask_result = runner.invoke(
            cli,
            ["ask", "--db", str(db_path), "--json", "SQLite"],
        )
        self.assertEqual(ask_result.exit_code, 0, ask_result.output)

        payload = json.loads(ask_result.output)
        self.assertIn("question", payload)
        self.assertIn("answer", payload)
        self.assertIn("degraded", payload)
        self.assertIn("sources", payload)
        self.assertIn("structured", payload)

    # ------------------------------------------------------------------
    # Teste 5: ask_question usa QA provider, não o de extração
    # ------------------------------------------------------------------
    def test_ask_question_uses_qa_provider_not_extraction_provider(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        fake_answer = "Resposta do QA provider"

        def fake_qa_provider(_: str) -> str:
            return fake_answer

        with patch("brain4me.query.build_qa_provider_from_env", return_value=fake_qa_provider):
            result = ask_question(db_path, "SQLite")

        self.assertFalse(result.degraded)
        self.assertEqual(result.answer, fake_answer)

    # ------------------------------------------------------------------
    # Teste 6: fallback continua funcionando com QA provider
    # ------------------------------------------------------------------
    def test_degraded_fallback_works_when_qa_provider_unavailable(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        with patch("brain4me.query.build_qa_provider_from_env", return_value=None):
            result = ask_question(db_path, "SQLite")

        self.assertTrue(result.degraded)
        self.assertNotEqual(result.answer.strip(), "")
