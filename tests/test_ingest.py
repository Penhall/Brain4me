from pathlib import Path
import sys
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from brain4me.ingest import ingest_markdown_note
from brain4me.storage import initialize_database
from tests.conftest import (
    EXTERNAL_NOTE,
    FREEFORM_ENRICHED_NOTE,
    FREEFORM_NOTE,
    LINKER_VARIANT_NOTE,
    NATURAL_NOTE,
    SEMANTIC_LINKER_NOTE,
    SAMPLE_NOTE,
    WorkspaceTempDirTestCase,
)


class IngestTests(WorkspaceTempDirTestCase):
    def test_ingest_structured_markdown_persists_knowledge_context_and_memory(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)

        result = ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        self.assertGreaterEqual(result.entities_created, 5)
        self.assertGreaterEqual(result.relations_created, 4)
        self.assertGreaterEqual(result.context_nodes_created, 4)
        self.assertGreaterEqual(result.context_edges_created, 3)
        self.assertGreaterEqual(result.memory_entries_created, 1)

        with sqlite3.connect(db_path) as conn:
            entity_types = {
                row[0]
                for row in conn.execute("SELECT entity_type FROM entities").fetchall()
            }
            context_edge_types = {
                row[0]
                for row in conn.execute("SELECT predicate FROM context_edges").fetchall()
            }
            memory_types = {
                row[0]
                for row in conn.execute("SELECT memory_type FROM memory_entries").fetchall()
            }

        self.assertTrue(
            {"Project", "Problem", "Decision", "Evidence", "Alternative", "Risk"}.issubset(
                entity_types
            )
        )
        self.assertTrue({"supports", "alternative_to", "warns_about"}.issubset(context_edge_types))
        self.assertIn("episodic", memory_types)

    def test_ingest_accepts_contextual_labels_like_conclusao_motivo_e_conflito(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)

        result = ingest_markdown_note(
            db_path=db_path,
            markdown_text=NATURAL_NOTE,
            source_path="notes/revisao-contextual.md",
        )

        self.assertGreaterEqual(result.entities_created, 4)
        self.assertGreaterEqual(result.context_nodes_created, 4)
        self.assertGreaterEqual(result.context_edges_created, 4)

        with sqlite3.connect(db_path) as conn:
            decisions = {
                row[0]
                for row in conn.execute(
                    "SELECT canonical_name FROM entities WHERE entity_type = 'Decision'"
                ).fetchall()
            }
            context_predicates = {
                row[0]
                for row in conn.execute("SELECT predicate FROM context_edges").fetchall()
            }

        self.assertIn("manter SQLite como persistencia inicial", decisions)
        self.assertTrue({"supports", "contradicts", "exception_for"}.issubset(context_predicates))

    def test_ingest_extracts_decision_evidence_alternative_and_risk_from_freeform_text(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)

        result = ingest_markdown_note(
            db_path=db_path,
            markdown_text=FREEFORM_NOTE,
            source_path="notes/freeform-persistencia.md",
        )

        self.assertGreaterEqual(result.entities_created, 4)
        self.assertGreaterEqual(result.relations_created, 3)

        with sqlite3.connect(db_path) as conn:
            entity_rows = conn.execute(
                "SELECT entity_type, canonical_name FROM entities ORDER BY id"
            ).fetchall()

        entities = {(row[0], row[1]) for row in entity_rows}
        self.assertIn(("Decision", "SQLite parece melhor que Neo4j"), entities)
        self.assertIn(("Evidence", "reduz complexidade operacional"), entities)
        self.assertIn(("Alternative", "Neo4j"), entities)
        self.assertIn(("Risk", "limitar consultas relacionais avancadas no futuro"), entities)

    def test_ingest_extracts_project_problem_and_objective_from_freeform_text(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)

        result = ingest_markdown_note(
            db_path=db_path,
            markdown_text=FREEFORM_ENRICHED_NOTE,
            source_path="notes/freeform-enriched.md",
        )

        self.assertGreaterEqual(result.entities_created, 7)

        with sqlite3.connect(db_path) as conn:
            entity_rows = conn.execute(
                "SELECT entity_type, canonical_name FROM entities ORDER BY id"
            ).fetchall()

        entities = {(row[0], row[1]) for row in entity_rows}
        self.assertIn(("Project", "Brain4me"), entities)
        self.assertIn(("Objective", "validar rapido o Brain4me"), entities)
        self.assertIn(
            ("Problem", "escolher persistencia inicial com baixo atrito"),
            entities,
        )

    def test_ingest_populates_source_quality_and_scores(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)

        ingest_markdown_note(
            db_path=db_path,
            markdown_text=EXTERNAL_NOTE,
            source_path="notes/external.md",
        )

        with sqlite3.connect(db_path) as conn:
            source_row = conn.execute(
                "SELECT source_origin_type, source_reliability FROM sources"
            ).fetchone()
            entity_scores = [
                row[0] for row in conn.execute("SELECT score FROM entities").fetchall()
            ]
            relation_scores = [
                row[0] for row in conn.execute("SELECT score FROM relations").fetchall()
            ]
            context_scores = [
                row[0] for row in conn.execute("SELECT score FROM context_nodes").fetchall()
            ]
            memory_scores = [
                row[0] for row in conn.execute("SELECT score FROM memory_entries").fetchall()
            ]

        self.assertEqual(source_row[0], "external")
        self.assertGreater(source_row[1], 0.0)
        self.assertTrue(all(score > 0.0 for score in entity_scores))
        self.assertTrue(all(score > 0.0 for score in relation_scores))
        self.assertTrue(all(score > 0.0 for score in context_scores))
        self.assertTrue(all(score > 0.0 for score in memory_scores))

    def test_ingest_links_entities_with_same_normalized_name_in_same_type(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)

        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        result = ingest_markdown_note(
            db_path=db_path,
            markdown_text=LINKER_VARIANT_NOTE,
            source_path="notes/banco-mvp-variant.md",
        )

        self.assertEqual(result.entities_created, 4)

        with sqlite3.connect(db_path) as conn:
            alternative_rows = conn.execute(
                """
                SELECT canonical_name
                FROM entities
                WHERE entity_type = 'Alternative'
                ORDER BY canonical_name
                """
            ).fetchall()

        self.assertEqual([row[0] for row in alternative_rows], ["Neo4j"])

    def test_ingest_links_semantically_similar_decisions_in_same_context(self):
        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)

        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        result = ingest_markdown_note(
            db_path=db_path,
            markdown_text=SEMANTIC_LINKER_NOTE,
            source_path="notes/banco-mvp-semantic.md",
        )

        self.assertLess(result.entities_created, 6)

        with sqlite3.connect(db_path) as conn:
            decision_rows = conn.execute(
                """
                SELECT canonical_name
                FROM entities
                WHERE entity_type = 'Decision'
                ORDER BY canonical_name
                """
            ).fetchall()

        self.assertEqual([row[0] for row in decision_rows], ["usar SQLite no MVP"])
