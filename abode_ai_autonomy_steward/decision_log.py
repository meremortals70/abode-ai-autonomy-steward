"""
Decision log — append-only record of every action decision.

System 2 is explainable only if there is a durable record of what it decided
and why, and what happened to each decision. This module appends one JSON
line per event. Like the constraint layer, it only grows: nothing removes or
edits an entry.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger("abode_ai_autonomy_steward")

DECISION_LOG_PATH = Path("/data/decision_log.jsonl")


def append(entry: dict) -> None:
    """Append one decision record. Entries are never edited or removed."""
    record = {"recorded_at": datetime.now(timezone.utc).isoformat()}
    record.update(entry)
    DECISION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def read() -> list:
    """Return all recorded entries, oldest first. For inspection and tests."""
    if not DECISION_LOG_PATH.exists():
        return []
    entries = []
    for line in DECISION_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries
