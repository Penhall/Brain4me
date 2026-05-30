from pathlib import Path
import sys
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from click.testing import CliRunner

from brain4me.cli import cli
from brain4me.context_builder import BuiltContext
from brain4me.decision_engine import suggest_decision
from brain4me.feedback import detect_unstable_pattern, record_feedback
from brain4me.ingest import ingest_markdown_note
from brain4me.memory import (
    apply_feedback_penalty,
    compute_memory_score,
    fetch_relevant_memories,
    store_learned_pattern,
)
from brain4me.memory_governance import list_patterns, remove_pattern, update_pattern_score
from brain4me.patterns import normalize_decision_text
from brain4me.query import ask_question
from brain4me.storage import connect, initialize_database, utc_now
from tests.conftest import SAMPLE_NOTE, WorkspaceTempDirTestCase


class Phase5Tests(WorkspaceTempDirTestCase):
    def test_compute_memory_score_rewards_recent_frequent_confident_patterns(self):
        strong_entry = {
            "frequency": 5,
            "confidence_score": 0.9,
            "feedback_balance": 4,
            "last_used_at": utc_now(),
            "created_at": utc_now(),
            "is_unstable": 0,
        }
        weak_entry = {
            "frequency": 1,
            "confidence_score": 0.3,
            "feedback_balance": -2,
            "last_used_at": "2024-01-01T00:00:00+00:00",
            "created_at": "2024-01-01T00:00:00+00:00",
            "is_unstable": 0,
        }

        self.assertGreater(compute_memory_score(strong_entry), compute_memory_score(weak_entry))

    def test_apply_feedback_penalty_strongly_reduces_repeated_rejections(self):
        penalty = apply_feedback_penalty(
            "usar Neo4j no MVP",
            [
                {
                    "content": "Padrao rejeitado: usar Neo4j no MVP",
                    "normalized_key": normalize_decision_text("usar Neo4j no MVP"),
                    "feedback_balance": -4,
                    "frequency": 4,
                    "is_unstable": 0,
                }
            ],
        )

        self.assertLessEqual(penalty, 0.2)

    def test_normalize_decision_text_groups_superficial_variants(self):
        left = normalize_decision_text("Usar SQLite no MVP")
        right = normalize_decision_text("manter sqlite no mvp.")

        self.assertEqual(left, right)

    def test_detect_unstable_pattern_flags_conflicting_feedback(self):
        pattern = {
            "feedback_balance": 0,
            "frequency": 4,
            "correction_variants": 2,
            "is_unstable": 0,
        }

        self.assertTrue(detect_unstable_pattern(pattern))

    def test_governance_can_list_update_and_remove_patterns(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        store_learned_pattern(db_path, "Qual decisao devo tomar?", "usar SQLite no MVP", True)

        patterns = list_patterns(db_path, limit=10)
        self.assertTrue(patterns)
        pattern_id = patterns[0]["id"]

        update_pattern_score(db_path, pattern_id, 0.95)
        updated_patterns = list_patterns(db_path, limit=10)
        self.assertGreaterEqual(updated_patterns[0]["confidence_score"], 0.95)

        remove_pattern(db_path, pattern_id)
        self.assertEqual(list_patterns(db_path, limit=10), [])

    def test_fetch_relevant_memories_discards_unstable_patterns(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        ask_question(db_path, "Qual decisao devo tomar sobre SQLite?")
        record_feedback(
            "Qual decisao devo tomar sobre SQLite?",
            False,
            correction="usar SQLite no MVP com revisao semanal",
            db_path=db_path,
        )
        ask_question(db_path, "Qual decisao devo tomar sobre SQLite?")
        record_feedback(
            "Qual decisao devo tomar sobre SQLite?",
            False,
            correction="usar SQLite no MVP com revisao trimestral",
            db_path=db_path,
        )

        memories = fetch_relevant_memories(db_path, "Qual decisao devo tomar sobre SQLite?")

        self.assertFalse(any("instavel" in item.lower() for item in memories))
        self.assertTrue(any("Padrao aceito" in item for item in memories))

    def test_decision_engine_avoids_penalized_patterns_and_explains_learning(self):
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
                "Padrao rejeitado: usar Neo4j no MVP | aceitas=0 | rejeitadas=4 | ultima_ocorrencia=2026-05-01",
                "Padrao aceito: usar SQLite no MVP | aceitas=5 | rejeitadas=0 | ultima_ocorrencia=2026-05-01",
            ],
            inferences=[],
            detected_entities=["Neo4j", "SQLite"],
            intent="decision_support",
        )

        suggestion = suggest_decision(context)

        self.assertIn("SQLite", suggestion)
        self.assertIn("aceitas", suggestion.lower())

    def test_cli_memory_commands_support_list_review_and_remove(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        store_learned_pattern(db_path, "Qual decisao devo tomar?", "usar SQLite no MVP", True)

        runner = CliRunner()
        list_result = runner.invoke(cli, ["memory", "--db", str(db_path), "list"])
        self.assertEqual(list_result.exit_code, 0, list_result.output)
        self.assertIn("usar SQLite no MVP", list_result.output)

        review_result = runner.invoke(cli, ["memory", "--db", str(db_path), "review"])
        self.assertEqual(review_result.exit_code, 0, review_result.output)
        self.assertIn("Fortes", review_result.output)

        pattern_id = list_patterns(db_path, limit=10)[0]["id"]
        remove_result = runner.invoke(cli, ["memory", "--db", str(db_path), "remove", pattern_id])
        self.assertEqual(remove_result.exit_code, 0, remove_result.output)
        self.assertEqual(list_patterns(db_path, limit=10), [])
