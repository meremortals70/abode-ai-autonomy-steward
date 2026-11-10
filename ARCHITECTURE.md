> Living document. Update when layers, boundaries, or wake model change.
> The full design specification is `docs/architecture.md`; design rules are in `docs/decisions/D###.md`.

# Architecture — Abode AI Autonomy Steward

## Purpose

System 2 in the autonomous home: continuous, stateless, goal-level reasoning that proposes or executes actions, gated by an append-only constraint layer.

## Tech stack

| Layer | Technology |
| ----- | ---------- |
| App runtime | Python 3 (Alpine), `aiohttp`, `pyyaml`, Supervisor token |
| Platform | Home Assistant OS / Supervisor (App) |
| Companion | Home Assistant custom integration (Probatio form) |
| Persistence | `/data/approved_action_types.json`, `/data/constraints.yaml` |

## Directory structure

```text
abode_ai_autonomy_steward/               # the App (Supervisor-managed container)
  abode_ai_autonomy_steward.py           #   event-driven reasoning loop (System 2)
  constraint_layer.py                    #   append-only constraint engine
  decision_log.py                        #   append-only decision log
  charter.py                             #   charter loader (seed + read)
  charter.md                             #   shipped charter, seeded to /data
  config.yaml                            #   App options — min_confidence only
  constraints.yaml                       #   shipped charter defaults (seed)
  Dockerfile                             #   App image
  run.sh                                 #   entrypoint — exports MIN_CONFIDENCE
  DOCS.md                                #   App documentation
  icon.png                               #   App icon

custom_components/
  abode_ai_autonomy_steward_config/      # companion integration (runs inside HA Core)
    __init__.py                          #   sensor platform setup
    config_flow.py                       #   config + options flow (Probatio)
    llm.py                               #   three LLM tools (config, charter, trigger)
    sensor.py                            #   config sensor exposing attributes
    const.py                             #   DOMAIN and config keys
    manifest.json                        #   integration metadata (v0.5.0)
    translations/en.json                 #   UI translations
    brand/                               #   brand assets

README.md                                # project overview
hacs.json                                # HACS metadata
repository.yaml                          # App-store repository metadata
LICENSE

docs/
  architecture.md                        # full design specification
  decisions/                             # design rules D000–Dnnn

tests/
  test_constraint_layer.py               # constraint matching + append-only
  test_decision_log.py                   # decision log append + order
  test_charter.py                        # charter seed + append semantics
```

## Layer rules

1. **System 2 never polls.** It subscribes to HA's event stream and wakes only when something changes. A short debounce coalesces bursts.
2. **Stateless per pass.** Every reasoning pass fetches the complete current state, not a delta.
3. **Constraint layer is independent.** It checks every proposed action deterministically, including already-approved ones.
4. **Constraints are append-only.** `add_never_rule()` appends; no runtime API edits or deletes rules.
5. **Two-part install.** The App depends on the companion integration for `notify_service` and `ai_task_entity` selectors.
6. **Companion integration registers LLM tools** for inspecting config, explaining charter, and triggering a reasoning pass.

## Data flow

1. App starts and authenticates against HA via Supervisor token.
2. App reads `sensor.abode_ai_autonomy_steward_config` for `notify_service` and `ai_task_entity`.
3. App subscribes to HA event stream; on any event it debounces for `DEBOUNCE_SECONDS`.
4. After debounce, App fetches complete state snapshot.
5. App calls the configured `ai_task.*` service with the state snapshot and charter.
6. AI returns a structured decision: `action_needed`, `action_kind`, `action_type`, `service`, `target_entity`, `service_data`, `reasoning`, `confidence`.
7. If confidence < `MIN_CONFIDENCE`, do nothing.
8. Constraint layer checks `is_blocked(service, target_entity, action_type)`.
9. If blocked, log and do nothing.
10. If action type not approved, send notification (Approve / Deny / Never).
11. On Approve: execute service and record `action_type` as approved.
12. On Never: append a narrow constraint rule.
13. On Deny: do nothing.
14. If already approved and warranted: execute service.

## Cross-cutting concerns

- **Determinism:** Constraint layer has no model, no randomness, no external state except the YAML file.
- **Safety:** Every execution, including already-approved actions, passes the constraint layer.
- **Minimal options:** Only `min_confidence` is configured in the App. Entity/service selectors live in the companion integration.
- **Decision trace:** Every action decision and its outcome is appended to an append-only log (`decision_log.py`), so the steward's behaviour is auditable after the fact.
- **Approval nonce:** An approval or Never is honoured only with the single-use nonce of a pending proposal.
- **Extensibility:** Frigate and Tara perception inputs are not yet wired in, but the reasoning loop is structured to accept them later.

## Decisions

The numbered design rules are in `docs/decisions/`. A short summary:

| Rule | Decision |
| ---- | -------- |
| D002 | Event-driven wake instead of polling |
| D010 | Append-only constraints |
| D003 | Stateless, complete-state passes |
| D013 | Companion integration for selectors |
| D018 | Execute the model's service parameters, parsed strictly |
| D019 | Approvals bound to a single-use proposal nonce |
| D020 | Append-only decision log |

## Known issues / next work

- Frigate and Tara integration as System 0 inputs.
- Production exercise of the approval flow.
- See `docs/architecture.md` for the full list of known gaps and unverified behaviour.
