"""Charter — the steward's operating instructions.

The charter is prose, not code. It ships as `charter.md`, is seeded to
`/data/charter.md` on first run, and the household may append their own
lines to that file. The steward reads the whole file as its instructions,
so household-specific rules ("never announce to the baby's room") live
alongside the product charter without a code change. The seed is not the
source of truth: once `/data/charter.md` exists it is never overwritten.
"""

import logging
import shutil
from pathlib import Path

LOGGER = logging.getLogger("abode_ai_autonomy_steward")

CHARTER_PATH = Path("/data/charter.md")
"""The live charter. Persists across restarts and is household-extendable."""

SHIPPED_CHARTER = Path("/charter.md")
"""The product charter baked into the image by the Dockerfile."""


def seed_if_absent() -> None:
    """Copy the shipped charter into /data on first run only."""
    if CHARTER_PATH.exists():
        return

    if not SHIPPED_CHARTER.exists():
        LOGGER.error(
            "No charter at %s and no shipped charter at %s to seed from.",
            CHARTER_PATH, SHIPPED_CHARTER,
        )
        return

    shutil.copyfile(SHIPPED_CHARTER, CHARTER_PATH)
    LOGGER.info("Seeded %s from shipped charter.", CHARTER_PATH)


def load() -> str:
    """Return the current charter text, seeding it first if absent.

    Read fresh on every call so a household edit to /data/charter.md takes
    effect on the next reasoning pass, matching the constraint layer.
    """
    seed_if_absent()
    if not CHARTER_PATH.exists():
        return ""
    return CHARTER_PATH.read_text(encoding="utf-8")
