"""Tests for the noisy-entity wake filter."""

import sys
import unittest
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent.parent / "abode_ai_autonomy_steward"
sys.path.insert(0, str(PKG_DIR))

import wake_filter  # noqa: E402


class WakeFilterTests(unittest.TestCase):
    def test_normal_entity_wakes(self):
        f = wake_filter.WakeFilter()
        self.assertTrue(f.should_wake("sensor.ok", now=1000.0))
        self.assertTrue(f.should_wake("sensor.ok", now=1010.0))

    def test_bursty_entity_is_suppressed(self):
        f = wake_filter.WakeFilter()
        threshold = wake_filter.WAKE_BURST_THRESHOLD
        # Just under the threshold: every wake is allowed.
        for i in range(threshold - 1):
            self.assertTrue(f.should_wake("sensor.noisy", now=1000.0 + i))
        # The next wake crosses the threshold and is suppressed.
        self.assertFalse(f.should_wake("sensor.noisy", now=1000.0 + threshold - 1))
        # During cooldown, further wakes stay suppressed.
        self.assertFalse(f.should_wake("sensor.noisy", now=1000.0 + threshold))

    def test_cooldown_expires(self):
        f = wake_filter.WakeFilter()
        threshold = wake_filter.WAKE_BURST_THRESHOLD
        for i in range(threshold):
            f.should_wake("sensor.noisy", now=1000.0 + i)
        # Well after cooldown + window, a single wake is allowed again.
        later = 1000.0 + threshold + wake_filter.NOISY_COOLDOWN_SECONDS + wake_filter.WAKE_WINDOW_SECONDS
        self.assertTrue(f.should_wake("sensor.noisy", now=later))

    def test_suppression_is_per_entity(self):
        f = wake_filter.WakeFilter()
        threshold = wake_filter.WAKE_BURST_THRESHOLD
        for i in range(threshold):
            f.should_wake("sensor.noisy", now=1000.0 + i)
        # A different entity is unaffected.
        self.assertTrue(f.should_wake("sensor.other", now=1000.0 + threshold))


if __name__ == "__main__":
    unittest.main()
