from pathlib import Path
import sys
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from click.testing import CliRunner

from brain4me.cli import cli
from tests.conftest import SAMPLE_NOTE, WorkspaceTempDirTestCase


class CliTests(WorkspaceTempDirTestCase):
    def test_cli_runs_init_ingest_and_explain_flow(self):
        db_path = self.temp_dir / "brain4me.db"
        note_path = self.temp_dir / "banco-mvp.md"
        note_path.write_text(SAMPLE_NOTE, encoding="utf-8")

        runner = CliRunner()

        init_result = runner.invoke(cli, ["init-db", "--db", str(db_path)])
        self.assertEqual(init_result.exit_code, 0, init_result.output)
        self.assertIn("initialized", init_result.output.lower())

        ingest_result = runner.invoke(
            cli,
            ["ingest-markdown", "--db", str(db_path), "--file", str(note_path)],
        )
        self.assertEqual(ingest_result.exit_code, 0, ingest_result.output)
        self.assertIn("entities_created", ingest_result.output)

        explain_result = runner.invoke(
            cli,
            ["explain-topic", "--db", str(db_path), "--topic", "SQLite"],
        )
        self.assertEqual(explain_result.exit_code, 0, explain_result.output)
        self.assertIn("usar SQLite no MVP", explain_result.output)
        self.assertIn("Neo4j", explain_result.output)

    def test_cli_ask_handles_natural_language_question(self):
        db_path = self.temp_dir / "brain4me.db"
        note_path = self.temp_dir / "banco-mvp.md"
        note_path.write_text(SAMPLE_NOTE, encoding="utf-8")

        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])
        runner.invoke(cli, ["ingest", "--db", str(db_path), str(note_path)])

        ask_result = runner.invoke(
            cli,
            ["ask", "--db", str(db_path), "O que eu sei sobre SQLite?"],
        )
        self.assertEqual(ask_result.exit_code, 0, ask_result.output)
        self.assertIn("usar SQLite no MVP", ask_result.output)

    def test_cli_explain_returns_rich_sections(self):
        db_path = self.temp_dir / "brain4me.db"
        note_path = self.temp_dir / "revisao-contextual.md"
        from tests.conftest import NATURAL_NOTE

        note_path.write_text(NATURAL_NOTE, encoding="utf-8")

        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])
        runner.invoke(cli, ["ingest", "--db", str(db_path), str(note_path)])

        explain_result = runner.invoke(
            cli,
            ["explain", "--db", str(db_path), "SQLite"],
        )
        self.assertEqual(explain_result.exit_code, 0, explain_result.output)
        self.assertIn("Relations:", explain_result.output)
        self.assertIn("Context:", explain_result.output)
        self.assertIn("History:", explain_result.output)
        self.assertIn("Conflicts:", explain_result.output)

    def test_cli_help_lists_prompt_contract_commands(self):
        runner = CliRunner()
        help_result = runner.invoke(cli, ["--help"])
        self.assertEqual(help_result.exit_code, 0, help_result.output)
        self.assertIn("ingest", help_result.output)
        self.assertIn("ask", help_result.output)
        self.assertIn("decide", help_result.output)
        self.assertIn("log", help_result.output)
        self.assertIn("fact", help_result.output)
        self.assertIn("explain", help_result.output)

    def test_cli_summary_reports_database_and_graph_counts(self):
        db_path = self.temp_dir / "brain4me.db"
        note_path = self.temp_dir / "banco-mvp.md"
        note_path.write_text(SAMPLE_NOTE, encoding="utf-8")

        runner = CliRunner()

        init_result = runner.invoke(cli, ["init-db", "--db", str(db_path)])
        self.assertEqual(init_result.exit_code, 0, init_result.output)

        ingest_result = runner.invoke(
            cli,
            ["ingest-markdown", "--db", str(db_path), "--file", str(note_path)],
        )
        self.assertEqual(ingest_result.exit_code, 0, ingest_result.output)

        summary_result = runner.invoke(
            cli,
            ["summary", "--db", str(db_path)],
        )
        self.assertEqual(summary_result.exit_code, 0, summary_result.output)
        self.assertIn("Compartments:", summary_result.output)
        self.assertIn("Entities:", summary_result.output)
        self.assertIn("Knowledge Graph:", summary_result.output)
        self.assertIn("Context Graph:", summary_result.output)

    def test_cli_decide_creates_decision_that_can_be_explained(self):
        db_path = self.temp_dir / "brain4me.db"
        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])

        decide_result = runner.invoke(
            cli,
            [
                "decide",
                "--db",
                str(db_path),
                "--compartment",
                "arquitetura",
                "--project",
                "Brain4me",
                "--problem",
                "escolher persistencia inicial",
                "--evidence",
                "reduz complexidade operacional",
                "--alternative",
                "Neo4j",
                "--risk",
                "revisar quando o grafo crescer",
                "usar SQLite no MVP",
            ],
        )
        self.assertEqual(decide_result.exit_code, 0, decide_result.output)
        self.assertIn("entities_created", decide_result.output)

        explain_result = runner.invoke(
            cli,
            ["ask", "--db", str(db_path), "SQLite"],
        )
        self.assertEqual(explain_result.exit_code, 0, explain_result.output)
        self.assertIn("usar SQLite no MVP", explain_result.output)
        self.assertIn("Neo4j", explain_result.output)

    def test_cli_fact_and_log_create_manual_sources(self):
        db_path = self.temp_dir / "brain4me.db"
        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])

        fact_result = runner.invoke(
            cli,
            ["fact", "--db", str(db_path), "--compartment", "inbox", "SQLite reduz setup local"],
        )
        log_result = runner.invoke(
            cli,
            ["log", "--db", str(db_path), "--compartment", "inbox", "Analisei trade-offs de persistencia"],
        )
        self.assertEqual(fact_result.exit_code, 0, fact_result.output)
        self.assertEqual(log_result.exit_code, 0, log_result.output)

        with sqlite3.connect(db_path) as conn:
            source_paths = {
                row[0]
                for row in conn.execute(
                    "SELECT source_path FROM sources ORDER BY source_path"
                ).fetchall()
            }

        self.assertTrue(any(path.startswith("manual://fact/") for path in source_paths))
        self.assertTrue(any(path.startswith("manual://log/") for path in source_paths))

    def test_cli_ask_supports_json_output(self):
        db_path = self.temp_dir / "brain4me.db"
        note_path = self.temp_dir / "banco-mvp.md"
        note_path.write_text(SAMPLE_NOTE, encoding="utf-8")

        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])
        runner.invoke(cli, ["ingest", "--db", str(db_path), str(note_path)])

        ask_result = runner.invoke(
            cli,
            ["ask", "--db", str(db_path), "--json", "O que eu sei sobre SQLite?"],
        )
        self.assertEqual(ask_result.exit_code, 0, ask_result.output)

        payload = json.loads(ask_result.output)
        self.assertIn("question", payload)
        self.assertIn("answer", payload)
        self.assertIn("degraded", payload)
        self.assertIn("sources", payload)
        self.assertIn("structured", payload)
        self.assertEqual(payload["structured"]["topic"], "O que eu sei sobre SQLite?")
        self.assertIn("usar SQLite no MVP", payload["structured"]["decisions"])
        self.assertIn("Neo4j", payload["structured"]["alternatives"])

    def test_cli_explain_supports_json_output(self):
        db_path = self.temp_dir / "brain4me.db"
        note_path = self.temp_dir / "banco-mvp.md"
        note_path.write_text(SAMPLE_NOTE, encoding="utf-8")

        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])
        runner.invoke(cli, ["ingest", "--db", str(db_path), str(note_path)])

        explain_result = runner.invoke(
            cli,
            ["explain", "--db", str(db_path), "--json", "SQLite"],
        )
        self.assertEqual(explain_result.exit_code, 0, explain_result.output)

        payload = json.loads(explain_result.output)
        self.assertEqual(payload["entity"], "SQLite")
        self.assertIn("usar SQLite no MVP", payload["decisions"])
        self.assertIn("relations", payload)
        self.assertIn("context", payload)

    def test_cli_summary_supports_json_output(self):
        db_path = self.temp_dir / "brain4me.db"
        note_path = self.temp_dir / "banco-mvp.md"
        note_path.write_text(SAMPLE_NOTE, encoding="utf-8")

        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])
        runner.invoke(cli, ["ingest", "--db", str(db_path), str(note_path)])

        summary_result = runner.invoke(
            cli,
            ["summary", "--db", str(db_path), "--json"],
        )
        self.assertEqual(summary_result.exit_code, 0, summary_result.output)

        payload = json.loads(summary_result.output)
        self.assertIn("counts", payload)
        self.assertIn("graphs", payload)
        self.assertGreaterEqual(payload["counts"]["Entities"], 1)
        self.assertGreaterEqual(payload["graphs"]["knowledge"]["nodes"], 1)
        self.assertGreaterEqual(payload["graphs"]["context"]["edges"], 1)

    def test_cli_export_returns_snapshot_json(self):
        db_path = self.temp_dir / "brain4me.db"
        note_path = self.temp_dir / "banco-mvp.md"
        note_path.write_text(SAMPLE_NOTE, encoding="utf-8")

        runner = CliRunner()
        runner.invoke(cli, ["init-db", "--db", str(db_path)])
        runner.invoke(cli, ["ingest", "--db", str(db_path), str(note_path)])

        export_result = runner.invoke(
            cli,
            ["export", "--db", str(db_path)],
        )
        self.assertEqual(export_result.exit_code, 0, export_result.output)

        payload = json.loads(export_result.output)
        self.assertIn("counts", payload)
        self.assertIn("entities", payload)
        self.assertIn("relations", payload)
        self.assertIn("context_nodes", payload)
        self.assertIn("context_edges", payload)
        self.assertIn("memory_entries", payload)
        self.assertGreaterEqual(len(payload["entities"]), 1)
        self.assertTrue(any(item["entity_type"] == "Decision" for item in payload["entities"]))
