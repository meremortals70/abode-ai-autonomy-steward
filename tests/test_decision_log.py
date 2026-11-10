"""Tests for the append-only decision log."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PKG_DIR = Path(__file__).resolve().parent.parent / "abode_ai_autonomy_steward"
sys.path.insert(0, str(PKG_DIR))

import decision_log  # noqa: E402


class DecisionLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "decision_log.jsonl"
        self._patcher = mock.patch.object(decision_log, "DECISION_LOG_PATH", self.path)
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def test_empty_when_no_file(self):
        self.assertEqual(decision_log.read(), [])

    def test_append_records_in_order(self):
        decision_log.append({"kind": "decision", "outcome": "proposed", "action_type": "a"})
        decision_log.append({"kind": "approval", "action_type": "a"})
        entries = decision_log.read()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["kind"], "decision")
        self.assertEqual(entries[1]["kind"], "approval")
        self.assertIn("recorded_at", entries[0])

    def test_append_is_additive_only(self):
        decision_log.append({"kind": "decision", "outcome": "proposed"})
        first = decision_log.read()
        decision_log.append({"kind": "never"})
        second = decision_log.read()
        self.assertEqual(len(second), len(first) + 1)
        self.assertEqual(second[0], first[0])


if __name__ == "__main__":
    unittest.main()
