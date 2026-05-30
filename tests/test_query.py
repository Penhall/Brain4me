from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from brain4me.ingest import ingest_markdown_note
from brain4me.graphs import build_context_graph, build_knowledge_graph
from brain4me.query import explain_entity, explain_topic
from brain4me.storage import initialize_database
from tests.conftest import (
    CONFLICTING_DECISION_NOTE,
    EXTERNAL_NOTE,
    NATURAL_NOTE,
    SAMPLE_NOTE,
    WorkspaceTempDirTestCase,
)


class QueryTests(WorkspaceTempDirTestCase):
    def test_explain_topic_returns_evidence_risks_and_alternatives(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        explanation = explain_topic(db_path, "SQLite")

        self.assertEqual(explanation.topic, "SQLite")
        self.assertIn("usar SQLite no MVP", explanation.decisions)
        self.assertIn("reduz complexidade operacional", explanation.evidence)
        self.assertIn("Neo4j", explanation.alternatives)
        self.assertIn(
            "consultas relacionais avancadas podem exigir revisao futura",
            explanation.risks,
        )

    def test_builds_separate_knowledge_and_context_graphs(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        knowledge_graph = build_knowledge_graph(db_path)
        context_graph = build_context_graph(db_path)

        self.assertGreaterEqual(knowledge_graph.number_of_edges(), 4)
        self.assertGreaterEqual(context_graph.number_of_edges(), 3)
        self.assertTrue(
            all(node_id.startswith("entity:") for node_id in knowledge_graph.nodes)
        )
        self.assertTrue(
            all(node_id.startswith("context:") for node_id in context_graph.nodes)
        )

    def test_explain_topic_can_find_decision_through_context_terms(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=NATURAL_NOTE,
            source_path="notes/revisao-contextual.md",
        )

        explanation = explain_topic(db_path, "complexidade operacional")

        self.assertEqual(explanation.topic, "complexidade operacional")
        self.assertIn("manter SQLite como persistencia inicial", explanation.decisions)
        self.assertIn("reduzir complexidade operacional e setup", explanation.evidence)
        self.assertIn("Neo4j", explanation.alternatives)

    def test_explain_topic_can_find_decision_through_project_name(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        explanation = explain_topic(db_path, "Brain4me")

        self.assertEqual(explanation.topic, "Brain4me")
        self.assertIn("usar SQLite no MVP", explanation.decisions)
        self.assertIn("reduz complexidade operacional", explanation.evidence)

    def test_explain_topic_can_find_decision_through_problem_name(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        explanation = explain_topic(db_path, "persistencia inicial do MVP")

        self.assertEqual(explanation.topic, "persistencia inicial do MVP")
        self.assertIn("usar SQLite no MVP", explanation.decisions)
        self.assertIn("Neo4j", explanation.alternatives)

    def test_explain_topic_prioritizes_higher_scored_evidence(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=EXTERNAL_NOTE,
            source_path="notes/external.md",
        )
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/personal.md",
        )

        explanation = explain_topic(db_path, "SQLite")

        self.assertGreaterEqual(len(explanation.evidence), 2)
        self.assertEqual(explanation.evidence[0], "reduz complexidade operacional")

    def test_explain_entity_returns_relations_context_history_and_conflicts(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=NATURAL_NOTE,
            source_path="notes/revisao-contextual.md",
        )

        explanation = explain_entity(db_path, "SQLite")

        self.assertEqual(explanation.entity, "SQLite")
        self.assertTrue(any("Decision" in item or "manter SQLite" in item for item in explanation.decisions))
        self.assertTrue(any("supports" in item for item in explanation.relations))
        self.assertTrue(any("reduzir complexidade operacional" in item for item in explanation.context))
        self.assertTrue(any("Decisao registrada" in item for item in explanation.history))
        self.assertTrue(any("Neo4j facilita exploracao relacional" in item for item in explanation.conflicts))

    def test_ingest_detects_conflict_between_competing_decisions_for_same_problem(self):
        db_path = self.temp_dir / "brain4me.db"
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

        explanation = explain_entity(db_path, "Neo4j")

        self.assertIn("usar Neo4j no MVP", explanation.decisions)
        self.assertTrue(
            any("usar SQLite no MVP" in item and "usar Neo4j no MVP" in item for item in explanation.conflicts)
        )
