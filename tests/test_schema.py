from pathlib import Path
import sys
import sqlite3
import uuid

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from brain4me.storage import initialize_database
from tests.conftest import WorkspaceTempDirTestCase


class SchemaTests(WorkspaceTempDirTestCase):
    def test_initialize_database_creates_core_tables(self):
        db_path = self.temp_dir / "brain4me.db"

        initialize_database(db_path)

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()

        table_names = {name for (name,) in rows}

        self.assertTrue(
            {
                "compartments",
                "sources",
                "notes",
                "entities",
                "relations",
                "context_nodes",
                "context_edges",
                "context_entity_links",
                "memory_entries",
                "ingest_logs",
            }.issubset(table_names)
        )

    def test_initialize_database_creates_source_quality_and_score_columns(self):
        db_path = self.temp_dir / "brain4me.db"

        initialize_database(db_path)

        with sqlite3.connect(db_path) as conn:
            sources_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()
            }
            entities_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(entities)").fetchall()
            }
            relations_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(relations)").fetchall()
            }
            context_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(context_nodes)").fetchall()
            }
            memory_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(memory_entries)").fetchall()
            }

        self.assertTrue({"source_origin_type", "source_reliability"}.issubset(sources_columns))
        self.assertIn("score", entities_columns)
        self.assertIn("score", relations_columns)
        self.assertIn("score", context_columns)
        self.assertIn("score", memory_columns)

    def test_initialize_database_uses_text_ids_for_core_tables(self):
        db_path = self.temp_dir / "brain4me.db"

        initialize_database(db_path)

        with sqlite3.connect(db_path) as conn:
            entities_columns = {
                row[1]: row[2] for row in conn.execute("PRAGMA table_info(entities)").fetchall()
            }
            relations_columns = {
                row[1]: row[2] for row in conn.execute("PRAGMA table_info(relations)").fetchall()
            }
            context_columns = {
                row[1]: row[2] for row in conn.execute("PRAGMA table_info(context_nodes)").fetchall()
            }

        self.assertEqual(entities_columns["id"].upper(), "TEXT")
        self.assertEqual(relations_columns["id"].upper(), "TEXT")
        self.assertEqual(context_columns["id"].upper(), "TEXT")

    def test_ingested_records_receive_uuid4_ids(self):
        from brain4me.ingest import ingest_markdown_note
        from tests.conftest import SAMPLE_NOTE

        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        ingest_markdown_note(
            db_path=db_path,
            markdown_text=SAMPLE_NOTE,
            source_path="notes/banco-mvp.md",
        )

        with sqlite3.connect(db_path) as conn:
            ids = []
            ids.extend(row[0] for row in conn.execute("SELECT id FROM entities").fetchall())
            ids.extend(row[0] for row in conn.execute("SELECT id FROM relations").fetchall())
            ids.extend(row[0] for row in conn.execute("SELECT id FROM context_nodes").fetchall())
            ids.extend(row[0] for row in conn.execute("SELECT id FROM memory_entries").fetchall())

        self.assertTrue(ids)
        for raw_id in ids:
            parsed = uuid.UUID(str(raw_id))
            self.assertEqual(str(parsed), str(raw_id))
