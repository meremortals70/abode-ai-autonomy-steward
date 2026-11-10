"""Tests for the append-only constraint layer."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PKG_DIR = Path(__file__).resolve().parent.parent / "abode_ai_autonomy_steward"
sys.path.insert(0, str(PKG_DIR))

import yaml  # noqa: E402

import constraint_layer  # noqa: E402


def _write(path: Path, rules: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(rules, f)


class ConstraintLayerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.live_path = Path(self._tmp.name) / "constraints.yaml"
        self.seed_path = Path(self._tmp.name) / "seed.yaml"
        self._live_patcher = mock.patch.object(constraint_layer, "CONSTRAINTS_PATH", self.live_path)
        self._seed_patcher = mock.patch.object(constraint_layer, "SHIPPED_DEFAULTS", self.seed_path)
        self._live_patcher.start()
        self._seed_patcher.start()
        self.addCleanup(self._live_patcher.stop)
        self.addCleanup(self._seed_patcher.stop)

    def test_empty_when_no_file(self):
        blocked, _ = constraint_layer.is_blocked("light.turn_on", "light.x", "x")
        self.assertFalse(blocked)
        self.assertEqual(constraint_layer.rule_count(), 0)

    def test_prefix_and_wildcard_matching(self):
        _write(self.live_path, [
            {"match": {"service_prefix": "alarm_control_panel.alarm_disarm"}},
            {"match": {"service_prefix": "lock.unlock", "target_entity": "lock.front_door"}},
            {"match": {"service_prefix": "light.", "action_type": "night_lighting"}},
        ])

        # Service-only rule: any target matches (wildcard).
        self.assertTrue(constraint_layer.is_blocked("alarm_control_panel.alarm_disarm", "alarm_control_panel.home", "anything")[0])
        # Service + target both match.
        self.assertTrue(constraint_layer.is_blocked("lock.unlock", "lock.front_door", "anything")[0])
        # Target differs -> no match.
        self.assertFalse(constraint_layer.is_blocked("lock.unlock", "lock.back_door", "anything")[0])
        # Service prefix + action_type both match.
        self.assertTrue(constraint_layer.is_blocked("light.turn_on", "light.bedroom", "night_lighting")[0])
        # action_type differs -> no match.
        self.assertFalse(constraint_layer.is_blocked("light.turn_on", "light.bedroom", "daytime")[0])

    def test_add_never_rule_appends(self):
        self.assertEqual(constraint_layer.rule_count(), 0)
        constraint_layer.add_never_rule("switch.turn_on", "switch.kettle", "unattended", reasoning="rejected")
        constraint_layer.add_never_rule("switch.turn_on", "switch.oven", "unattended", reasoning="rejected")
        self.assertEqual(constraint_layer.rule_count(), 2)

        blocked, why = constraint_layer.is_blocked("switch.turn_on", "switch.kettle", "unattended")
        self.assertTrue(blocked)
        self.assertIn("Rejected", why)

    def test_seed_if_absent_seeds_once_and_never_overwrites(self):
        _write(self.seed_path, [{"id": "seed-1", "match": {"service_prefix": "lock.unlock"}}])
        constraint_layer.seed_if_absent()
        self.assertEqual(constraint_layer.rule_count(), 1)

        # A resident-added rule must survive a later re-seed attempt.
        constraint_layer.add_never_rule("switch.turn_on", "switch.kettle", "x", reasoning="r")
        constraint_layer.seed_if_absent()
        self.assertEqual(constraint_layer.rule_count(), 2)


if __name__ == "__main__":
    unittest.main()
