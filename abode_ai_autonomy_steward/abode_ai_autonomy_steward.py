"""
Abode AI Autonomy Steward - continuous, stateless, goal-level reasoning.
System 2 in the four-layer architecture (System 0: perception, System 1:
fast deterministic automations, System 2: this app, plus an independent
constraint layer gating everything System 2 proposes).

Trigger model, corrected 30 Jul 2026: NOT a polling timer, NOT a schedule.
This app subscribes to HA's event stream and stays blocked, actively
waiting, until something actually changes. When a change arrives it wakes,
pulls the COMPLETE current state fresh (not the delta that woke it - the
whole picture, stateless per pass, per the reactive-control-loop design),
reasons over it, then goes back to waiting. Rapid bursts of related events
are coalesced into a single reasoning pass via a short debounce - this is
event coalescing, not a timer; the wake condition is always "something
changed," never "time has passed."

Configuration: min_confidence lives in this App's own native options
(plain float, no entity relationship). notify_service and the AI Task
entity are NOT configured here - they come from the companion
'abode_ai_autonomy_steward_config' integration's config flow, which provides
real entity/service selectors validated against live HA data. This app
reads sensor.abode_ai_autonomy_steward_config's attributes once at startup and
again on every change to that sensor, so reconfiguring through the
integration's UI updates this app live.
"""

import asyncio
import json
import os
import logging
import sys
import time
from pathlib import Path

import aiohttp

import constraint_layer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("abode_ai_autonomy_steward")

SUPERVISOR_TOKEN = os.environ["SUPERVISOR_TOKEN"]
WS_URL = "ws://supervisor/core/websocket"
DATA_PATH = Path("/data/approved_action_types.json")
CONFIG_ENTITY_ID = "sensor.abode_ai_autonomy_steward_config"
TRIGGER_EVENT = "abode_ai_autonomy_steward_config.trigger_reasoning"

MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.70"))
DEBOUNCE_SECONDS = 5  # coalesces a burst of simultaneous events into one reasoning pass - not a schedule, see module docstring

CHARTER = """
PURPOSE

You perceive the current, complete state of this home on every reasoning
pass - not what changed, the whole picture, fresh each time. Your job is
to notice things a resident would want handled, and either act (if
already approved) or propose (if new).

You exist to make residents' lives easier. If nothing currently warrants
action, say so and do nothing. A quiet home is a correct outcome.

Some inputs may be unavailable on a given pass (e.g. Frigate or Tara not
yet connected). Reason from whatever you're given; do not assume missing
inputs mean something is wrong.

BOUNDARIES

The charter's boundaries are enforced by a separate, deterministic
constraint layer outside your control - it will block anything that
crosses a known boundary regardless of what you decide. You should still
never knowingly propose crossing one: never cast inappropriate content to
a shared screen, never make the whole home maximally visible/audible at
night without evidence of an intruder or emergency, never touch alarm or
lock state in a way that could trap or endanger a resident, never propose
a costly or irreversible action without flagging the cost/irreversibility
explicitly in your reasoning, never treat a child or vulnerable resident
differently without a guardian's explicit approval. When uncertain,
propose rather than act.

APPROVAL PROTOCOL

1. Decide what KIND of action this is - a short, stable action_type name
   for the class of situation and response, not this one instance.
2. If not yet approved: propose it, name it, state your reasoning in one
   sentence, describe the specific action. Do not act.
3. If already approved: decide fresh, every time, whether this specific
   moment actually calls for it before acting.
4. Never generalize an approval beyond what was granted.
5. You may propose retiring or replacing an approved action_type if you
   judge a better approach exists - set action_kind to
   "revise_approved_type". This goes through the same approval step.
6. If nothing is warranted, set action_needed false.
"""

DECISION_STRUCTURE = {
    "action_needed": {"description": "Whether an action should be taken right now", "required": True, "selector": {"boolean": None}},
    "action_kind": {"description": "'new_action' or 'revise_approved_type'", "selector": {"text": None}},
    "action_type": {"description": "Short, stable category name for this kind of decision", "selector": {"text": None}},
    "replaces_action_type": {"description": "If revising, the existing type this replaces", "selector": {"text": None}},
    "service": {"description": "HA service to call, e.g. light.turn_on", "selector": {"text": None}},
    "target_entity": {"description": "The entity_id the service should target", "selector": {"text": None}},
    "reasoning": {"description": "One sentence explaining the decision", "selector": {"text": None}},
    "confidence": {"description": "Confidence from 0 to 1", "selector": {"number": {"min": 0, "max": 1, "step": 0.01}}},
}


def _load_approved() -> dict:
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            LOGGER.exception("Could not read %s, starting empty", DATA_PATH)
    return {}


def _save_approved(approved: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(approved, indent=2))


class AIAutonomySteward:
    def __init__(self):
        self.approved_types: dict = _load_approved()
        self._msg_id = 0
        self._pending = {}
        self.ws = None

        # Populated from sensor.abode_ai_autonomy_steward_config - see _apply_config.
        self.notify_service: str = ""
        self.ai_task_entity: str = ""

        self._debounce_task: asyncio.Task | None = None

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def _send(self, payload: dict) -> dict:
        msg_id = self._next_id()
        payload["id"] = msg_id
        fut = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = fut
        await self.ws.send_json(payload)
        return await fut

    async def call_service(self, domain, service, service_data, target=None, return_response=False):
        payload = {"type": "call_service", "domain": domain, "service": service, "service_data": service_data}
        if target:
            payload["target"] = target
        if return_response:
            payload["return_response"] = True
        return await self._send(payload)

    # ---- config, from the companion integration - not from App options ----

    def _apply_config(self, attrs: dict) -> None:
        self.notify_service = attrs.get("notify_service") or ""
        self.ai_task_entity = attrs.get("ai_task_entity") or ""
        LOGGER.info("Config applied: notify via %s, AI Task entity %s", self.notify_service, self.ai_task_entity)

    async def fetch_config(self) -> None:
        result = await self._send({"type": "get_states"})
        for state in (result.get("result") or []):
            if state.get("entity_id") == CONFIG_ENTITY_ID:
                self._apply_config(state.get("attributes") or {})
                return
        LOGGER.warning(
            "%s not found. Install and configure the 'Abode AI Autonomy Steward Config' "
            "integration first (Settings -> Devices & Services -> Add Integration).",
            CONFIG_ENTITY_ID,
        )

    # ---- System 0 access: extensible, per "don't hard-code today's limits" ----

    async def _source_ha_state(self) -> dict:
        result = await self._send({"type": "get_states"})
        states = (result.get("result") or [])
        return {"ha_entities": {s["entity_id"]: s.get("state") for s in states}}

    async def _source_frigate(self) -> dict | None:
        # Not wired yet - Frigate does not exist on hapve as of 30 Jul 2026.
        return None

    async def _source_tara(self) -> dict | None:
        # Not wired yet - Tara (LXC 251) is installed but not plumbed into
        # the AI engine as of 30 Jul 2026.
        return None

    async def gather_state(self) -> dict:
        snapshot = {}
        for source_fn in (self._source_ha_state, self._source_frigate, self._source_tara):
            fragment = await source_fn()
            if fragment:
                snapshot.update(fragment)
        return snapshot

    # ---- the reasoning pass - triggered by a wake, not a timer ----

    async def _reason(self):
        if not self.ai_task_entity:
            LOGGER.warning("No AI Task entity configured yet - skipping pass")
            return

        snapshot = await self.gather_state()
        approved_summary = (
            {k: v.get("description", "") for k, v in self.approved_types.items()}
            if self.approved_types else "(none yet)"
        )
        instructions = (
            f"{CHARTER}\n\n"
            f"Already-approved action types: {json.dumps(approved_summary)}\n\n"
            f"Current complete state: {json.dumps(snapshot, default=str)}\n\n"
            "Decide, per the charter above, whether an autonomous action is warranted right now."
        )

        service_data = {
            "task_name": "ai autonomy steward reasoning pass",
            "instructions": instructions,
            "structure": DECISION_STRUCTURE,
            "entity_id": self.ai_task_entity,
        }
        try:
            result = await self.call_service(
                "ai_task", "generate_data",
                service_data,
                return_response=True,
            )
        except Exception:
            LOGGER.exception("ai_task.generate_data call failed")
            return

        # ai_task.generate_data returns its response directly under the
        # service result as {"data": ..., "conversation_id": ...}, not nested
        # under a "response" key.
        data = ((result or {}).get("result") or {}).get("data") or {}
        if not data:
            LOGGER.debug("ai_task.generate_data returned empty data; raw result: %s", result)
        await self._handle_decision(data)

    async def _handle_decision(self, data: dict):
        if not data.get("action_needed"):
            return
        if float(data.get("confidence", 0) or 0) < MIN_CONFIDENCE:
            LOGGER.info("Below confidence floor: %s", data.get("reasoning", ""))
            return

        action_type = data.get("action_type", "")
        service = data.get("service", "")
        target = data.get("target_entity", "")

        if not (action_type and service and target):
            LOGGER.warning("Incomplete decision, discarding: %s", data)
            return

        blocked, why = constraint_layer.is_blocked(service, target, action_type)
        if blocked:
            LOGGER.error("Blocked by constraint layer: %s (attempted: %s -> %s)", why, service, target)
            return

        is_revision = data.get("action_kind") == "revise_approved_type"

        if not is_revision and action_type in self.approved_types:
            LOGGER.info("Executing pre-approved '%s': %s -> %s", action_type, service, target)
            domain, svc = service.split(".", 1)
            await self.call_service(domain, svc, {}, target={"entity_id": target})
            return

        await self._propose(data, is_revision)

    async def _propose(self, data: dict, is_revision: bool):
        if not self.notify_service:
            LOGGER.warning("No notify_service configured yet - cannot request approval for: %s", data)
            return

        action_type = data.get("action_type", "")
        service = data.get("service", "")
        target = data.get("target_entity", "")
        reasoning = data.get("reasoning", "")
        replaces = data.get("replaces_action_type", "") if is_revision else ""

        approve_action = f"S2_APPROVE::{action_type}::{service}::{target}::{replaces}"
        never_action = f"S2_NEVER::{action_type}::{service}::{target}"

        notify_domain, notify_svc = (
            self.notify_service.split(".", 1) if "." in self.notify_service else ("notify", self.notify_service)
        )
        await self.call_service(
            notify_domain, notify_svc,
            {
                "title": "Your home wants to act" if not is_revision else f"Your home wants to replace '{replaces}'",
                "message": reasoning or f"Proposing: {action_type}",
                "data": {"actions": [
                    {"action": approve_action, "title": "Approve"},
                    {"action": "S2_DENY", "title": "Deny"},
                    {"action": never_action, "title": "Never"},
                ]},
            },
        )

    async def handle_notification_action(self, action: str) -> None:
        if action.startswith("S2_APPROVE::"):
            _, action_type, service, target, replaces = action.split("::")
            if replaces:
                self.approved_types.pop(replaces, None)
                LOGGER.info("'%s' retired, replaced by '%s'", replaces, action_type)
            self.approved_types[action_type] = {"approved_at": time.time(), "description": service}
            _save_approved(self.approved_types)
            LOGGER.info("'%s' approved", action_type)
            domain, svc = service.split(".", 1)
            await self.call_service(domain, svc, {}, target={"entity_id": target})

        elif action.startswith("S2_NEVER::"):
            _, action_type, service, target = action.split("::")
            constraint_layer.add_never_rule(service, target, action_type, reasoning=f"Rejected: {action_type}")
            LOGGER.info("Constraint added: '%s' (%s -> %s) is now permanently forbidden", action_type, service, target)

    # ---- wake-on-change, with burst coalescing ----

    def _schedule_reasoning_pass(self):
        if self._debounce_task is not None:
            self._debounce_task.cancel()
        self._debounce_task = asyncio.create_task(self._debounced_reason())

    async def _debounced_reason(self):
        try:
            await asyncio.sleep(DEBOUNCE_SECONDS)
            await self._reason()
        except asyncio.CancelledError:
            pass

    async def _receiver(self):
        async for msg in self.ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            data = json.loads(msg.data)
            mtype = data.get("type")

            if mtype == "result" and data.get("id") in self._pending:
                self._pending.pop(data["id"]).set_result(data)
                continue

            if mtype == "event":
                event = data.get("event", {})
                event_type = event.get("event_type")

                if event_type == "state_changed":
                    ev_data = event.get("data", {})
                    entity_id = ev_data.get("entity_id", "")
                    new_state_obj = ev_data.get("new_state") or {}

                    if entity_id == CONFIG_ENTITY_ID:
                        self._apply_config(new_state_obj.get("attributes") or {})
                        continue

                    # Any HA state change wakes the reasoning pass - actively
                    # waiting, not polling. A burst of changes coalesces via
                    # the debounce above into a single pass. Logged per-entity
                    # so noisy/high-frequency entities can be identified and
                    # filtered, rather than guessed at.
                    LOGGER.info("Wake trigger: %s changed to %s", entity_id, new_state_obj.get("state"))
                    self._schedule_reasoning_pass()

                elif event_type == "mobile_app_notification_action":
                    action = event.get("data", {}).get("action", "")
                    asyncio.create_task(self.handle_notification_action(action))

                elif event_type == TRIGGER_EVENT:
                    LOGGER.info("Wake trigger: %s requested by LLM tool", TRIGGER_EVENT)
                    self._schedule_reasoning_pass()

    async def run(self):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WS_URL) as ws:
                self.ws = ws
                first = json.loads((await ws.receive()).data)
                assert first["type"] == "auth_required"
                await ws.send_json({"type": "auth", "access_token": SUPERVISOR_TOKEN})
                auth_result = json.loads((await ws.receive()).data)
                if auth_result["type"] != "auth_ok":
                    raise RuntimeError(f"Auth failed: {auth_result}")
                LOGGER.info("Authenticated against Home Assistant Core")

                receiver = asyncio.create_task(self._receiver())

                await self.fetch_config()
                await self._send({"type": "subscribe_events", "event_type": "state_changed"})
                await self._send({"type": "subscribe_events", "event_type": "mobile_app_notification_action"})
                await self._send({"type": "subscribe_events", "event_type": TRIGGER_EVENT})
                LOGGER.info(
                    "Abode AI Autonomy Steward started, actively waiting for changes. %d approved type(s): %s",
                    len(self.approved_types), list(self.approved_types.keys()),
                )
                await receiver


async def main():
    while True:
        try:
            await AIAutonomySteward().run()
        except Exception:
            LOGGER.exception("Connection lost, retrying in 10s")
            await asyncio.sleep(10)


def _require_constraints() -> int:
    """Seed the constraint file if absent, then refuse to run with zero rules.

    Deliberately outside main()'s retry loop: main() catches Exception and
    retries every 10s, so raising in there would spin forever instead of
    stopping. A System 2 that reasons and acts with no constraint layer is a
    worse outcome than a System 2 that does not start.
    """
    constraint_layer.seed_if_absent()
    count = constraint_layer.rule_count()

    if count == 0:
        LOGGER.critical(
            "Refusing to start: 0 constraints loaded from %s. System 2 will "
            "not reason or act without an enforced boundary. Reinstall the "
            "App, or place a valid constraints.yaml at that path.",
            constraint_layer.CONSTRAINTS_PATH,
        )
        sys.exit(1)

    LOGGER.info("Constraint layer active: %d rule(s) in force.", count)
    return count


if __name__ == "__main__":
    _require_constraints()
    asyncio.run(main())
