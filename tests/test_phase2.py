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
from brain4me.context_builder import build_context_for_question
from brain4me.ingest import ingest_markdown_note
from brain4me.models import TopicExplanation
from brain4me.query import ask_question
from brain4me.storage import initialize_database
from tests.conftest import SAMPLE_NOTE, WorkspaceTempDirTestCase


class Phase2Tests(WorkspaceTempDirTestCase):
    # ------------------------------------------------------------------
    # Teste 1: context_builder monta contexto não vazio a partir de uma
    # explicação com decisions e evidence preenchidos
    # ------------------------------------------------------------------
    def test_context_builder_produces_nonempty_context_from_explanation(self):
        explanation = TopicExplanation(
            topic="SQLite",
            decisions=["usar SQLite no MVP"],
            evidence=["reduz complexidade operacional"],
            alternatives=["Neo4j"],
            risks=["consultas relacionais avancadas podem exigir revisao futura"],
        )

        result = build_context_for_question("Por que SQLite?", explanation)

        self.assertNotEqual(result.context_text, "")
        self.assertIn("Decisões", result.context_text)
        self.assertGreater(result.score, 0)
        self.assertFalse(result.degraded)

    # ------------------------------------------------------------------
    # Teste 2: context_builder respeita max_chars
    # ------------------------------------------------------------------
    def test_context_builder_respects_max_chars_limit(self):
        long_decision = "A" * 200
        explanation = TopicExplanation(
            topic="LongTopic",
            decisions=[long_decision, long_decision, long_decision],
            evidence=[long_decision, long_decision],
            alternatives=[long_decision],
            risks=[long_decision],
        )

        result = build_context_for_question("Pergunta qualquer?", explanation, max_chars=50)

        self.assertLessEqual(len(result.context_text), 50)
        self.assertNotEqual(result.context_text, "")

    # ------------------------------------------------------------------
    # Teste 3: ask_question usa LLM mockado quando provider disponível
    # ------------------------------------------------------------------
    def test_ask_question_uses_llm_when_provider_available(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        fake_answer = "Resposta gerada pelo LLM fake"

        def fake_provider(_: str) -> str:
            return fake_answer

        with patch(
            "brain4me.query.build_qa_provider_from_env",
            return_value=fake_provider,
        ):
            result = ask_question(db_path, "SQLite")

        self.assertFalse(result.degraded)
        self.assertEqual(result.answer, fake_answer)

    # ------------------------------------------------------------------
    # Teste 4: ask_question entra em modo degradado quando LLM falha
    # ------------------------------------------------------------------
    def test_ask_question_degrades_gracefully_when_llm_fails(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        def failing_provider(_: str) -> str:
            raise RuntimeError("LLM unavailable")

        with patch(
            "brain4me.query.build_qa_provider_from_env",
            return_value=failing_provider,
        ):
            result = ask_question(db_path, "SQLite")

        self.assertTrue(result.degraded)
        self.assertNotEqual(result.answer.strip(), "")

    # ------------------------------------------------------------------
    # Teste 5: brain ask --json inclui os campos corretos
    # ------------------------------------------------------------------
    def test_cli_ask_json_output_has_expected_fields(self):
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
        self.assertIn("structured", payload)
        self.assertIn("topic", payload["structured"])
        self.assertIn("decisions", payload["structured"])
        self.assertNotEqual(payload["structured"]["decisions"], [])

    # ------------------------------------------------------------------
    # Teste 6: fontes aparecem quando há nota associada
    # ------------------------------------------------------------------
    def test_ask_question_returns_sources_when_notes_exist(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        result = ask_question(db_path, "SQLite")

        self.assertIsInstance(result.sources, list)
        for source in result.sources:
            self.assertTrue(hasattr(source, "note_id"))
            self.assertTrue(hasattr(source, "source_path"))
            self.assertTrue(hasattr(source, "title"))
            self.assertTrue(hasattr(source, "label"))
        self.assertIsNotNone(result.structured)
