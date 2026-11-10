# Architecture — Abode AI Autonomy Steward

The full design specification. The numbered design rules are in
[decisions](decisions/). The short living summary is
[ARCHITECTURE.md](../ARCHITECTURE.md).

## Purpose

The Abode AI Autonomy Steward is **System 2** of an autonomous home: it
continuously reasons about the home's whole current state and decides whether
anything is worth doing — then either acts on an already-approved kind of
action, or proposes a new kind for one-time approval. Every decision is gated
by an append-only constraint layer that only ever grows stricter.

It is not a rule engine and not a fast automation. Fast, deterministic
reactions are System 1 (Home Assistant automations, untouched by this project).
The steward is the slow, goal-level reasoner above them.

## The four-layer model

| Layer | What it is | Owned by |
| --- | --- | --- |
| System 0 | Perception — Home Assistant sensors today, Frigate and Tara later | HA, Frigate, Tara |
| System 1 | Fast deterministic automations | Home Assistant automations |
| System 2 | This App — continuous, stateless, goal-level reasoning | Abode AI Autonomy Steward |
| Constraint layer | Independent, append-only rules gating everything System 2 proposes | `constraint_layer.py` |

The four-way split is deliberate: perception, fast reaction, slow reasoning,
and hard constraints are separate concerns. The constraint layer is outside the
model's weights and outside the reasoning loop, so a boundary holds no matter
what the model decides.

## Architecture tree

```text
abode_ai_autonomy_steward/                  # the App (Supervisor-managed container)
  abode_ai_autonomy_steward.py              #   event-driven reasoning loop (System 2)
  constraint_layer.py                       #   append-only constraint engine
  config.yaml                               #   App options — min_confidence only
  constraints.yaml                          #   shipped charter defaults (seed)
  Dockerfile                                #   App image (ghcr.io/home-assistant/base)
  run.sh                                    #   entrypoint — exports MIN_CONFIDENCE
  DOCS.md                                   #   App documentation
  icon.png                                  #   App icon

custom_components/
  abode_ai_autonomy_steward_config/         # companion integration (runs inside HA Core)
    __init__.py                             #   sensor platform setup
    config_flow.py                          #   config + options flow (Probatio form)
    llm.py                                  #   three LLM tools (config, charter, trigger)
    sensor.py                               #   config sensor exposing attributes
    const.py                                #   DOMAIN and config keys
    manifest.json                           #   integration metadata (v0.5.0)
    translations/en.json                    #   UI translations
    brand/                                  #   brand assets

README.md                                   # project overview
hacs.json                                   # HACS metadata
repository.yaml                             # App-store repository metadata
LICENSE

docs/
  architecture.md                           # this document
  decisions/                                # design rules D000–Dnnn
```

## Layer rules

1. **System 2 never polls.** The App subscribes to Home Assistant's event
   stream and wakes only when something changes. `DEBOUNCE_SECONDS = 5`
   coalesces a burst into one pass; the wake condition is always "something
   changed," never "time has passed."
2. **Stateless per pass.** Every pass pulls the complete current state fresh,
   not the delta that woke it, and holds no history between passes.
3. **Constraint layer is independent and deterministic.** No model call, no
   randomness, no external state except the YAML file. Every execution path —
   including already-approved action types — passes through `is_blocked()`.
4. **Constraints are append-only.** `add_never_rule()` appends; there is no
   edit or delete API. The only way a rule goes away is editing
   `/data/constraints.yaml` directly, outside the running App.
5. **Two-part install.** The App depends on the companion integration for the
   two fields that reference live HA data (`notify_service`, `ai_task_entity`),
   because the App options schema has no entity/service selector type.
6. **The App's own options are minimal.** Only `min_confidence` (a plain
   float) lives in the App; entity/service references belong in the companion.

## The reasoning pass

The loop is a reactive control loop: sense fresh, decide, act or propose,
repeat. It is event-driven, not scheduled.

1. The App starts, reads `SUPERVISOR_TOKEN`, and authenticates to HA Core over
   `ws://supervisor/core/websocket` (`run()`).
2. It reads its configuration from `sensor.abode_ai_autonomy_steward_config`
   (`fetch_config()`) and subscribes to three event types:
   `state_changed`, `mobile_app_notification_action`, and
   `abode_ai_autonomy_steward_config.trigger_reasoning`.
3. Any `state_changed` event (other than the config sensor itself, which
   re-applies config) schedules a reasoning pass through a 5-second debounce
   (`_receiver()` → `_schedule_reasoning_pass()` → `_debounced_reason()`).
4. On a pass, `_reason()` gathers the complete state snapshot via
   `gather_state()`, which fans out to pluggable sources — `_source_ha_state`
   today, `_source_frigate` and `_source_tara` returning `None` until wired.
5. It builds the instructions: the `CHARTER`, the list of already-approved
   action types, and the full state snapshot, and calls
   `ai_task.generate_data` with the `DECISION_STRUCTURE` schema.
6. The AI returns a structured decision; `_handle_decision()` applies the gates
   in order: `action_needed` → `confidence` ≥ `MIN_CONFIDENCE` → complete
   fields → constraint layer → approved/revise/propose.

### The decision structure

The AI is asked to return exactly these fields (`DECISION_STRUCTURE`):

| Field | Meaning |
| --- | --- |
| `action_needed` | Whether anything should be done right now (required) |
| `action_kind` | `new_action` or `revise_approved_type` |
| `action_type` | Short, stable category name for this kind of decision |
| `replaces_action_type` | When revising, the existing type this replaces |
| `service` | Home Assistant service, e.g. `light.turn_on` |
| `target_entity` | The `entity_id` the service targets |
| `reasoning` | One sentence explaining the decision |
| `confidence` | 0 to 1 |

A decision with `action_needed` false, below the confidence floor, or missing
`action_type`/`service`/`target_entity` is discarded with no action.

## The approval protocol

Approval is **per action type**, not per instance. The approved list is
persisted to `/data/approved_action_types.json`.

- **New kind** — proposed to the resident by mobile notification with three
  actions; the steward does not act until approved.
- **Already-approved kind** — executed immediately, but only after the steward
  has decided fresh, this pass, that the moment calls for it.
- **A better way** — `action_kind: revise_approved_type` proposes retiring an
  approved type and goes through the same approval step; approving it replaces
  the old type.

The three responses (`handle_notification_action()`):

- **Approve** — records the type and executes the service once.
- **Deny** — declines this proposal only.
- **Never** — appends a permanent constraint for that exact
  `service`/`target_entity`/`action_type` via `add_never_rule()`.

## The constraint layer

`constraint_layer.py` is the deterministic gate. `is_blocked(service,
target_entity, action_type)` returns whether a proposed action matches any
rule in `constraints.yaml`.

A rule matches when the action matches **every non-null field** of its `match`
block; fields left out are wildcards. The shipped `constraints.yaml` seeds the
layer with two charter defaults — never disarm an alarm, never unlock in a way
that could trap a resident — and `seed_if_absent()` copies them into `/data`
on first run only, never overwriting a file the resident has since appended to.

Before starting, `_require_constraints()` refuses to run with zero rules: a
System 2 that reasons and acts with no enforced boundary is a worse outcome
than one that does not start.

## Configuration

| Field | Where | Description |
| --- | --- | --- |
| `notify_service` | Companion integration (entity selector) | `notify.*` service for approval prompts |
| `ai_task_entity` | Companion integration (entity selector) | `ai_task.*` entity for reasoning passes |
| `min_confidence` | App options | Won't act or propose below this (default 0.70) |

The companion integration's config flow uses a Probatio schema with
`EntitySelector` pickers for the two selectors, exposes them as attributes of
`sensor.abode_ai_autonomy_steward_config`, and the App re-reads them on every
change to that sensor.

## The companion integration and LLM tools

`custom_components/abode_ai_autonomy_steward_config` exists for two reasons:
to provide real entity/service selectors, and to expose the steward to Home
Assistant's LLM surface. It registers three tools
(`llm.py`, Home Assistant 2026.10.0 LLM Tool API):

- `abode_ai_autonomy_steward_config__get_configuration` — returns the
  configured `notify_service` and `ai_task_entity`.
- `abode_ai_autonomy_steward_config__explain_charter` — returns the charter,
  boundaries, and approval protocol.
- `abode_ai_autonomy_steward_config__trigger_reasoning` — fires the trigger
  event that asks the App to wake and run a pass immediately.

These are available to Assist and MCP clients. The first two are read-only;
the third is idempotent and not destructive.

## Security model and known gaps

The design's safety comes from the constraint layer being outside the model.
The following gaps are known and unaddressed in the current build:

1. **Approvals are unauthenticated.** `S2_APPROVE::` and `S2_NEVER::` arrive as
   `mobile_app_notification_action` events; any code that can fire an event on
   the HA bus can approve an action or append a constraint. There is no
   per-proposal nonce or origin check.
2. **Services are called with no parameters.** The decision structure has no
   `service_data` field, so execution calls the service with empty data —
   anything requiring an argument (brightness, message text, a delay) is out of
   reach.
3. **The charter is only partly enforced deterministically.** The charter's
   BOUNDARIES list screens, whole-home visibility at night, and costly or
   irreversible actions, but `constraints.yaml` only encodes alarm and lock
   guards. The rest rely on the model "never knowingly proposing" them.
4. **No decision trace.** Approved types are persisted, but there is no
   append-only record of what was decided and why — the audit trail an
   autonomous system needs for explainability is not yet present.
5. **No tests.** The matching logic and debounce have no test suite.

## Not yet verified

The following are true of the current build and are recorded so they are not
treated as confirmed:

- A full reasoning pass returning a real decision has not been observed end to
  end; the approval round-trip, the Never path, the constraint block path, and
  persistence across restart are all unexercised in production.
- `DEBOUNCE_SECONDS = 5` is an unmeasured placeholder, not a considered value.
- The entity or entities driving frequent wakes have not been identified, so no
  allowlist or denylist is in place to bound inference cost.
- Frigate and Tara are not wired in as perception sources.

## Decision history

The design rules are recorded in [decisions/](decisions/). The decisions were
made across the project's Claude sessions; the original rationale, evidence
class, and falsification conditions are in the session as-built documents
(`hapve-asbuilt-ai-autonomy-steward-2026-07-30.md` and its handover).
