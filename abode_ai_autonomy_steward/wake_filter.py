"""Wake filter — auto-suppress noisy entities.

A single high-frequency entity (a flapping sensor, a fast-updating power
meter) can keep the steward reasoning on every debounce cycle, forever. The
steward detects this per entity: if one entity wakes it more than a burst
threshold within a short window, that entity is suppressed for a cooldown so
the loop is not driven non-stop. Detection is automatic and self-healing — a
quiet entity wakes normally again once the cooldown lapses.
"""

import logging
import time

LOGGER = logging.getLogger("abode_ai_autonomy_steward")

WAKE_WINDOW_SECONDS = 60
WAKE_BURST_THRESHOLD = 20
NOISY_COOLDOWN_SECONDS = 300


class WakeFilter:
    def __init__(self) -> None:
        self._wake_times: dict = {}
        self._noisy_until: dict = {}

    def should_wake(self, entity_id: str, now: float | None = None) -> bool:
        """Return True if this entity's change should trigger a reasoning pass."""
        now = time.time() if now is None else now

        times = self._wake_times.setdefault(entity_id, [])
        times.append(now)
        cutoff = now - WAKE_WINDOW_SECONDS
        self._wake_times[entity_id] = [t for t in times if t >= cutoff]

        if now < self._noisy_until.get(entity_id, 0.0):
            return False

        if len(self._wake_times[entity_id]) >= WAKE_BURST_THRESHOLD:
            self._noisy_until[entity_id] = now + NOISY_COOLDOWN_SECONDS
            LOGGER.warning(
                "Suppressing noisy entity %s for %ds (%d wakes in the last %ds)",
                entity_id, NOISY_COOLDOWN_SECONDS,
                len(self._wake_times[entity_id]), WAKE_WINDOW_SECONDS,
            )
            return False

        return True
