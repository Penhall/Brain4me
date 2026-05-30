from pathlib import Path
import sys
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from brain4me.ingest import ingest_markdown_note
from brain4me.storage import initialize_database
from tests.conftest import FREEFORM_NOTE, WorkspaceTempDirTestCase


class ExtractorTests(WorkspaceTempDirTestCase):
    def test_adaptive_extractor_prefers_llm_provider_when_configured(self):
        from brain4me.extractor import (
            AdaptiveMarkdownExtractor,
            HeuristicMarkdownExtractor,
            LLMJsonExtractor,
        )

        extractor = AdaptiveMarkdownExtractor(
            llm_extractor=LLMJsonExtractor(
                response_provider=lambda _body: """{
                  "entities": [{"type": "Decision", "name": "usar SQLite no MVP"}],
                  "context": []
                }"""
            ),
            heuristic_extractor=HeuristicMarkdownExtractor(),
        )

        payload = extractor.extract("dummy body")

        self.assertEqual(payload.method, "llm_json")
        self.assertIn(("Decision", "usar SQLite no MVP"), payload.entity_items)

    def test_adaptive_extractor_uses_spacy_fallback_before_heuristic(self):
        from brain4me.extractor import AdaptiveMarkdownExtractor, SpacyFallbackExtractor

        class FakeDoc:
            ents = []

            @property
            def noun_chunks(self):
                return []

        extractor = AdaptiveMarkdownExtractor(
            llm_extractor=None,
            spacy_extractor=SpacyFallbackExtractor(
                nlp=lambda _body: FakeDoc(),
                heuristic_extractor=None,
            ),
        )

        payload = extractor.extract(
            "O objetivo atual e validar rapido o Brain4me. O problema imediato e escolher persistencia inicial com baixo atrito."
        )

        self.assertEqual(payload.method, "spacy")
        self.assertIn(("Objective", "validar rapido o Brain4me"), payload.entity_items)
        self.assertIn(
            ("Problem", "escolher persistencia inicial com baixo atrito"),
            payload.entity_items,
        )

    def test_ingest_falls_back_to_heuristic_when_llm_json_is_invalid(self):
        from brain4me.extractor import HeuristicMarkdownExtractor, LLMJsonExtractor

        db_path = self.temp_dir / "brain4me.db"
        initialize_database(db_path)
        extractor = LLMJsonExtractor(
            response_provider=lambda _body: "```json\n{invalid json]\n```",
            fallback_extractor=HeuristicMarkdownExtractor(),
        )

        result = ingest_markdown_note(
            db_path=db_path,
            markdown_text=FREEFORM_NOTE,
            source_path="notes/freeform-persistencia.md",
            extractor=extractor,
        )

        self.assertGreater(result.entities_created, 0)
        self.assertGreater(result.logs_created, 0)

        with sqlite3.connect(db_path) as conn:
            entity_rows = conn.execute(
                "SELECT entity_type, canonical_name FROM entities ORDER BY id"
            ).fetchall()
            log_rows = conn.execute(
                "SELECT stage, level, message FROM ingest_logs ORDER BY id"
            ).fetchall()

        entities = {(row[0], row[1]) for row in entity_rows}
        self.assertIn(("Decision", "SQLite parece melhor que Neo4j"), entities)
        self.assertTrue(any(row[0] == "extractor" for row in log_rows))
        self.assertTrue(any(row[1] == "warning" for row in log_rows))

    def test_llm_json_extractor_accepts_fenced_json_payload(self):
        from brain4me.extractor import LLMJsonExtractor

        extractor = LLMJsonExtractor(
            response_provider=lambda _body: """```json
{
  "entities": [
    {"type": "Decision", "name": "usar SQLite no MVP"},
    {"type": "Evidence", "name": "reduz complexidade operacional"}
  ],
  "context": [
    {"node_type": "evidence", "predicate": "supports", "content": "reduz complexidade operacional"}
  ]
}
```"""
        )

        payload = extractor.extract("dummy body")

        self.assertEqual(payload.method, "llm_json")
        self.assertEqual(payload.warnings, [])
        self.assertIn(("Decision", "usar SQLite no MVP"), payload.entity_items)
        self.assertIn(
            ("evidence", "supports", "reduz complexidade operacional"),
            payload.context_only_items,
        )
