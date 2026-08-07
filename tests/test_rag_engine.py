"""Smoke tests for local data loading and configuration."""

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import rag_engine  # noqa: E402


class RagEngineDataTests(unittest.TestCase):
    def test_project_paths_are_rooted_correctly(self):
        self.assertEqual(Path(rag_engine.DATA_DIR), PROJECT_ROOT / "data")
        self.assertEqual(Path(rag_engine.VECTORSTORE_DIR), PROJECT_ROOT / "vectorstore")

    def test_knowledge_base_documents_load(self):
        documents = rag_engine.load_documents()

        self.assertGreater(len(documents), 0)
        self.assertTrue(all(document["content"] for document in documents))

    def test_feedback_rows_load(self):
        self.assertGreater(len(rag_engine.load_feedback()), 0)


if __name__ == "__main__":
    unittest.main()
