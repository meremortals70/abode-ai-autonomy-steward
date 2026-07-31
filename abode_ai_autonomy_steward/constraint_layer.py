"""
Constraint layer — deterministic, append-only, independent of System 2's
reasoning. Same design as before, just relocated into the native-App
package: no model call, no delete/edit function anywhere in this file,
System 2 can only append via add_never_rule().
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

CONSTRAINTS_PATH = Path("/data/constraints.yaml")


def _load() -> list:
    if not CONSTRAINTS_PATH.exists():
        return []
    with open(CONSTRAINTS_PATH) as f:
        return yaml.safe_load(f) or []


def is_blocked(service: str, target_entity: str, action_type: str):
    """Returns (blocked, reason). Checked on every execution, including
    already-approved action types - a boundary holds regardless of any
    approval, past or future."""
    for rule in _load():
        match = rule.get("match", {})
        service_prefix = match.get("service_prefix")
        target = match.get("target_entity")
        rule_action_type = match.get("action_type")

        service_ok = service_prefix is None or (service or "").startswith(service_prefix)
        target_ok = target is None or target == target_entity
        action_type_ok = rule_action_type is None or rule_action_type == action_type

        if service_ok and target_ok and action_type_ok:
            return True, rule.get("description", rule.get("id", "unnamed constraint"))
    return False, ""


def add_never_rule(service: str, target_entity: str, action_type: str, reasoning: str) -> None:
    """Append-only. Derives a precise, narrow rule from the exact rejected
    action's structured fields."""
    rules = _load()
    rules.append({
        "id": f"never-{uuid.uuid4().hex[:8]}",
        "added_at": datetime.now(timezone.utc).isoformat(),
        "source": "user_never",
        "description": f"Rejected by resident: {reasoning or action_type}",
        "match": {
            "service_prefix": service,
            "target_entity": target_entity,
            "action_type": action_type,
        },
    })
    CONSTRAINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSTRAINTS_PATH, "w") as f:
        yaml.safe_dump(rules, f, sort_keys=False)
