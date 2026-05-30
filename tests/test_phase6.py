from pathlib import Path
import sys
import json


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from click.testing import CliRunner

from brain4me.cli import cli
from brain4me.graph_cache import get_cached_graphs, invalidate_cache
from brain4me.ingest import ingest_markdown_note
from brain4me.memory import prune_old_memories, store_learned_pattern
from brain4me.metrics import get_metrics_snapshot, reset_metrics
from brain4me.query import ask_question, hybrid_retrieval
from brain4me.semantic import semantic_similarity
from brain4me.storage import connect, get_or_create_compartment, initialize_database, new_uuid, utc_now
from brain4me.storage_schema import create_indexes
from tests.conftest import SAMPLE_NOTE, SEMANTIC_LINKER_NOTE, WorkspaceTempDirTestCase


class Phase6Tests(WorkspaceTempDirTestCase):
    def test_graph_cache_reuses_graphs_until_invalidation(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        first = get_cached_graphs(db_path, ttl_seconds=60)
        second = get_cached_graphs(db_path, ttl_seconds=60)
        self.assertIs(first.kg, second.kg)
        self.assertTrue(second.cache_hit)

        first.last_loaded_at = (first.last_loaded_at or 0.0) - 120.0
        refreshed = get_cached_graphs(db_path, ttl_seconds=60)
        self.assertIsNot(first.kg, refreshed.kg)

        invalidate_cache(db_path)
        invalidated = get_cached_graphs(db_path, ttl_seconds=60)
        self.assertIsNot(refreshed.kg, invalidated.kg)

    def test_create_indexes_registers_expected_sqlite_indexes(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)

        with connect(db_path) as conn:
            create_indexes(conn)
            entity_indexes = {row["name"] for row in conn.execute("PRAGMA index_list(entities)").fetchall()}
            relation_indexes = {row["name"] for row in conn.execute("PRAGMA index_list(relations)").fetchall()}
            link_indexes = {row["name"] for row in conn.execute("PRAGMA index_list(context_entity_links)").fetchall()}
            memory_indexes = {row["name"] for row in conn.execute("PRAGMA index_list(memory_entries)").fetchall()}

        self.assertIn("idx_entities_canonical_name", entity_indexes)
        self.assertIn("idx_relations_subject_entity_id", relation_indexes)
        self.assertIn("idx_relations_object_entity_id", relation_indexes)
        self.assertIn("idx_context_entity_links_entity_id", link_indexes)
        self.assertIn("idx_memory_entries_memory_type", memory_indexes)

    def test_semantic_similarity_ranks_related_text_above_unrelated_text(self):
        related = semantic_similarity(
            "persistencia inicial com baixo atrito operacional",
            "usar SQLite como banco inicial para reduzir complexidade operacional",
        )
        unrelated = semantic_similarity(
            "persistencia inicial com baixo atrito operacional",
            "planejamento de ferias e roteiro de viagem internacional",
        )

        self.assertGreater(related, unrelated)
        self.assertGreater(related, 0.2)

    def test_hybrid_retrieval_combines_graph_and_semantic_context(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SEMANTIC_LINKER_NOTE,
            source_path="notes/variacao-semantica.md",
        )

        graph_context = hybrid_retrieval(
            db_path,
            "Qual banco inicial reduz atrito operacional no MVP?",
            [],
        )

        combined_text = " ".join(
            [
                *graph_context.entities,
                *graph_context.decisions,
                *graph_context.evidence,
                *graph_context.inferences,
            ]
        )
        self.assertIn("SQLite", combined_text)
        self.assertTrue(graph_context.inferences or graph_context.evidence)

    def test_prune_old_memories_archives_weak_entries_and_consolidates_duplicates(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        store_learned_pattern(db_path, "Qual decisao devo tomar?", "usar SQLite no MVP", True)

        old_timestamp = "2024-01-01T00:00:00+00:00"
        with connect(db_path) as conn:
            compartment_id = get_or_create_compartment(conn, "system-memory", name="System Memory")
            conn.execute(
                """
                INSERT INTO memory_entries (
                    id, compartment_id, memory_type, related_entity_id, content,
                    valid_from, valid_to, priority, score, confidence_score, frequency,
                    last_used_at, feedback_balance, normalized_key, is_unstable, created_at
                ) VALUES (?, ?, 'decision_pattern', NULL, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_uuid(),
                    compartment_id,
                    "Padrao aceito: usar SQLite no MVP | aceitas=1 | rejeitadas=0 | ultima_ocorrencia=2024-01-01",
                    old_timestamp,
                    20,
                    0.4,
                    0.6,
                    1,
                    old_timestamp,
                    1,
                    "usar sqlite mvp",
                    0,
                    old_timestamp,
                ),
            )
            conn.execute(
                """
                INSERT INTO memory_entries (
                    id, compartment_id, memory_type, related_entity_id, content,
                    valid_from, valid_to, priority, score, confidence_score, frequency,
                    last_used_at, feedback_balance, normalized_key, is_unstable, created_at
                ) VALUES (?, ?, 'decision_pattern', NULL, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_uuid(),
                    compartment_id,
                    "Padrao rejeitado: usar banco documental | aceitas=0 | rejeitadas=3 | ultima_ocorrencia=2024-01-01",
                    old_timestamp,
                    5,
                    0.1,
                    0.1,
                    3,
                    old_timestamp,
                    -3,
                    "usar banco documental",
                    0,
                    old_timestamp,
                ),
            )
            conn.commit()

        stats = prune_old_memories(db_path)
        self.assertGreaterEqual(stats["consolidated"], 1)
        self.assertGreaterEqual(stats["archived"], 1)

        with connect(db_path) as conn:
            active_patterns = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM memory_entries
                WHERE memory_type = 'decision_pattern'
                  AND valid_to IS NULL
                """
            ).fetchone()["total"]
        self.assertEqual(active_patterns, 1)

    def test_metrics_are_logged_during_question_flow(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        reset_metrics()
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        ask_question(db_path, "Qual decisao devo tomar sobre persistencia?")
        ask_question(db_path, "Qual decisao devo tomar sobre persistencia?")
        metrics = get_metrics_snapshot()

        self.assertIn("query_time_ms", metrics)
        self.assertIn("context_build_time_ms", metrics)
        self.assertIn("llm_time_ms", metrics)
        self.assertIn("context_size_chars", metrics)
        self.assertIn("cache_used", metrics)
        self.assertGreater(metrics["query_time_ms"], 0.0)
        self.assertEqual(metrics.get("graph_cache_hit"), 1.0)

    def test_cli_supports_metrics_and_cache_clear_commands(self):
        db_path = self.temp_dir / "test.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )
        ask_question(db_path, "O que eu sei sobre SQLite?")

        runner = CliRunner()
        metrics_result = runner.invoke(cli, ["metrics", "--db", str(db_path)])
        self.assertEqual(metrics_result.exit_code, 0, metrics_result.output)
        payload = json.loads(metrics_result.output)
        self.assertIn("metrics", payload)
        self.assertIn("cache", payload)

        clear_result = runner.invoke(cli, ["cache", "clear"])
        self.assertEqual(clear_result.exit_code, 0, clear_result.output)
        self.assertIn("cleared", clear_result.output.lower())
