"""
System 2 — continuous, stateless, goal-level reasoning.

Native Supervisor App (not AppDaemon) - talks to HA Core directly over the
Supervisor-proxied WebSocket API, same mechanism the original
continuous_autonomy app used, since that part of the earlier design was
never the problem.

Architecture position (30 Jul four-layer decision):
- System 0 (perception): HA state today, via VM 244. Frigate and Tara are
  not plumbed in yet - INPUT_SOURCES below is written so they add as new
  entries later without touching the loop itself.
- System 1 (fast deterministic automations): untouched, not represented
  here.
- System 2 (this file): reasons continuously, stateless per cycle - pulls
  the CURRENT complete state fresh every pass. Nothing about "what
  changed" is carried between cycles; only the persisted approved-types
  list survives across cycles.
- Constraint layer (constraint_layer.py): separate component. Every
  proposed action is checked there before execution, including
  already-approved types, every single cycle - never trusted to System 2's
  own judgement alone.
"""

import asyncio
import json
import os
import logging
import time
from pathlib import Path

import aiohttp

import constraint_layer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("system2")

SUPERVISOR_TOKEN = os.environ["SUPERVISOR_TOKEN"]
WS_URL = "ws://supervisor/core/websocket"
DATA_PATH = Path("/data/approved_action_types.json")

NOTIFY_SERVICE = os.environ.get("NOTIFY_SERVICE", "notify")
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.70"))
CYCLE_DELAY_SECONDS = int(os.environ.get("CYCLE_DELAY_SECONDS", "15"))
AI_TASK_ENTITY = "ai_task.gemma_4_26b_a4b_it_ggu_f_ai_task"  # confirm exact entity_id in HA before first run

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

    # ---- System 0 access: extensible, per "don't hard-code today's limits" ----
    #
    # Each source is an async function returning a dict fragment for the
    # snapshot, or None if unavailable. Frigate/Tara get added as new
    # entries here later - nothing else about the loop changes.

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

    # ---- the stateless loop ----

    async def cycle(self):
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

        try:
            result = await self.call_service(
                "ai_task", "generate_data",
                {
                    "task_name": "system2 reasoning pass",
                    "instructions": instructions,
                    "structure": DECISION_STRUCTURE,
                },
                target={"entity_id": AI_TASK_ENTITY},
                return_response=True,
            )
        except Exception:
            LOGGER.exception("ai_task.generate_data call failed")
            return

        data = ((result or {}).get("result") or {}).get("response", {}).get("data") or {}
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
        action_type = data.get("action_type", "")
        service = data.get("service", "")
        target = data.get("target_entity", "")
        reasoning = data.get("reasoning", "")
        replaces = data.get("replaces_action_type", "") if is_revision else ""

        approve_action = f"S2_APPROVE::{action_type}::{service}::{target}::{replaces}"
        never_action = f"S2_NEVER::{action_type}::{service}::{target}"

        notify_domain, notify_svc = (
            NOTIFY_SERVICE.split(".", 1) if "." in NOTIFY_SERVICE else ("notify", NOTIFY_SERVICE)
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
                if event.get("event_type") == "mobile_app_notification_action":
                    action = event.get("data", {}).get("action", "")
                    asyncio.create_task(self.handle_notification_action(action))

    async def _cycle_loop(self):
        # Continuous - not a schedule. Always immediately queues the next
        # cycle after the previous one finishes. CYCLE_DELAY_SECONDS is a
        # pragmatic throttle so an idle home doesn't hammer the GPU engine
        # with back-to-back full reasoning calls - not the trigger
        # mechanism itself. Revisit once real cycle cost is measured.
        while True:
            await self.cycle()
            await asyncio.sleep(CYCLE_DELAY_SECONDS)

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

                await self._send({"type": "subscribe_events", "event_type": "mobile_app_notification_action"})
                receiver = asyncio.create_task(self._receiver())
                LOGGER.info(
                    "System 2 started. %d approved type(s): %s",
                    len(self.approved_types), list(self.approved_types.keys()),
                )
                await asyncio.gather(receiver, self._cycle_loop())


async def main():
    while True:
        try:
            await AIAutonomySteward().run()
        except Exception:
            LOGGER.exception("Connection lost, retrying in 10s")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
