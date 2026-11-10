"""Tests for the household-extendable charter."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PKG_DIR = Path(__file__).resolve().parent.parent / "abode_ai_autonomy_steward"
sys.path.insert(0, str(PKG_DIR))

import charter  # noqa: E402


class CharterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.live_path = Path(self._tmp.name) / "charter.md"
        self.seed_path = Path(self._tmp.name) / "seed.md"
        self._live_patcher = mock.patch.object(charter, "CHARTER_PATH", self.live_path)
        self._seed_patcher = mock.patch.object(charter, "SHIPPED_CHARTER", self.seed_path)
        self._live_patcher.start()
        self._seed_patcher.start()
        self.addCleanup(self._live_patcher.stop)
        self.addCleanup(self._seed_patcher.stop)

    def test_empty_when_no_seed(self):
        self.assertEqual(charter.load(), "")

    def test_seeds_once_and_preserves_household_edits(self):
        self.seed_path.write_text("shipped charter", encoding="utf-8")
        self.assertEqual(charter.load(), "shipped charter")

        # Household appends; a later load must not overwrite it.
        self.live_path.write_text(
            "shipped charter\n\n# household: never announce to the baby's room",
            encoding="utf-8",
        )
        charter.seed_if_absent()
        self.assertIn("never announce to the baby's room", charter.load())

    def test_load_reads_fresh(self):
        self.seed_path.write_text("v1", encoding="utf-8")
        self.assertEqual(charter.load(), "v1")
        self.live_path.write_text("v1 + household additions", encoding="utf-8")
        self.assertEqual(charter.load(), "v1 + household additions")


if __name__ == "__main__":
    unittest.main()
