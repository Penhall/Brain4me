from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from brain4me.context_builder import BuiltContext
from brain4me.decision_engine import suggest_decision
from brain4me.feedback import record_feedback
from brain4me.ingest import ingest_markdown_note
from brain4me.memory import fetch_relevant_memories, store_learned_pattern
from brain4me.query import ask_question
from brain4me.reasoning_log import fetch_recent_reasoning_traces
from brain4me.storage import connect, initialize_database
from tests.conftest import SAMPLE_NOTE, WorkspaceTempDirTestCase


class Phase4Tests(WorkspaceTempDirTestCase):
    def test_ask_question_persists_reasoning_trace(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        result = ask_question(db_path, "Qual decisao devo tomar sobre SQLite?")

        traces = fetch_recent_reasoning_traces(db_path)

        self.assertTrue(traces)
        self.assertEqual(traces[0]["question"], result.question)
        self.assertEqual(traces[0]["intent"], "decision_support")
        self.assertIn("SQLite", traces[0]["detected_entities"])
        self.assertIn("Fontes", traces[0]["answer"])

    def test_record_feedback_stores_feedback_with_latest_trace_context(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        ask_question(db_path, "Qual decisao devo tomar sobre SQLite?")

        record_feedback("Qual decisao devo tomar sobre SQLite?", True, db_path=db_path)

        with connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT question, answer, suggested_decision, feedback_type, correction
                FROM feedback_entries
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()

        self.assertEqual(row["question"], "Qual decisao devo tomar sobre SQLite?")
        self.assertEqual(row["feedback_type"], "accepted")
        self.assertEqual(row["correction"], "")
        self.assertNotEqual(row["answer"], "")

    def test_record_feedback_with_correction_stores_learned_patterns(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        result = ask_question(db_path, "Qual decisao devo tomar sobre SQLite?")

        record_feedback(
            "Qual decisao devo tomar sobre SQLite?",
            False,
            correction="usar SQLite no MVP com revisao futura",
            db_path=db_path,
        )

        memories = fetch_relevant_memories(db_path, "Qual decisao devo tomar sobre SQLite?")

        self.assertTrue(any("Padrao rejeitado" in item for item in memories))
        self.assertTrue(any("usar SQLite no MVP com revisao futura" in item for item in memories))
        self.assertNotEqual(result.suggested_decision.strip(), "")

    def test_store_learned_pattern_persists_decision_pattern_memory(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)

        store_learned_pattern(
            db_path,
            "Qual decisao devo tomar sobre persistencia?",
            "usar SQLite no MVP",
            True,
        )

        with connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT memory_type, content, priority
                FROM memory_entries
                WHERE memory_type = 'decision_pattern'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()

        self.assertEqual(row["memory_type"], "decision_pattern")
        self.assertIn("Padrao aceito", row["content"])
        self.assertGreaterEqual(row["priority"], 20)

    def test_decision_engine_adjusts_suggestion_based_on_feedback_memories(self):
        context = BuiltContext(
            question="Qual decisao devo tomar?",
            context_text="### Decisoes\n- usar Neo4j no MVP\n- usar SQLite no MVP",
            sources=[],
            score=0.8,
            degraded=False,
            decisions=["usar Neo4j no MVP", "usar SQLite no MVP"],
            evidence=["reduz complexidade operacional"],
            alternatives=["Neo4j", "SQLite"],
            risks=["maior complexidade operacional no MVP"],
            conflicts=[],
            memories=[
                "Padrao rejeitado para pergunta semelhante: usar Neo4j no MVP",
                "Padrao aceito para pergunta semelhante: usar SQLite no MVP",
            ],
            inferences=[],
            detected_entities=["Neo4j", "SQLite"],
            intent="decision_support",
        )

        suggestion = suggest_decision(context)

        self.assertIn("SQLite", suggestion)
        self.assertIn("decisoes anteriores", suggestion.lower())

    def test_ask_question_uses_learned_pattern_in_memories_and_answer(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        store_learned_pattern(
            db_path,
            "Qual decisao devo tomar sobre SQLite?",
            "usar SQLite no MVP",
            True,
        )

        result = ask_question(db_path, "Qual decisao devo tomar sobre SQLite?")

        self.assertTrue(any("Padrao aceito" in item for item in result.memories))
        self.assertTrue(
            "decisoes anteriores" in result.suggested_decision.lower()
            or "padrao aceito" in result.answer.lower()
        )
