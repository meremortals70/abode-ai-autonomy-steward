> Living document. Update when layers, boundaries, or wake model change.
> The full design specification is `docs/architecture.md`; design rules are in
> `docs/decisions/D###.md`; the original architecture theses are in `docs/source/`.

# Architecture — Abode AI Autonomy Steward

## Purpose

System 2 in the autonomous home — the **Steward** — continuous, stateless,
goal-level reasoning that proposes or executes actions, gated by the **Ward**
(an append-only constraint layer). The Steward is one component of a larger
middleware.

## The five components, four ranks

| Rank | Component | Role | Status |
| --- | --- | --- | --- |
| 0 | **Senses** | Perception substrate (Frigate, HA sensors) — external | existing apps |
| 1 | **Reflex** | Deterministic automations, zero reasoning, act directly | HA automations |
| 1 | **Vigil** | Cheap domain-scoped salience — decides what wakes the Steward | **not built** |
| 2 | **Steward** | Slow full reasoning — proposes actions | this App |
| 3 | **the Ward** | Deterministic gate on every proposal | `constraint_layer.py` |
| 4 | HA service calls | Actuation — outside the middleware | HA |

Reflex and Vigil are the **same rank** — both consume Senses directly, neither
feeds the other. Reflex bypasses the Steward and the Ward.

```
Senses (0)
  ├── Reflex (1) ──────────────────────────► HA service calls (4)   [bypass]
  └── Vigil (1) ──► Steward (2) ──► Ward (3) ─► HA service calls (4)
        │                  │
        └─── AI Engine ◄───┘   (LXC 252 Lemonade — shared substrate, not a rank)
```

## The six functional domains

Domains cross-cut Reflex and Vigil — each has a Reflex slice (discrete,
unambiguous) and a Vigil slice (ambiguous, judgment required):

**Safety** · **Security** · **Comfort** · **Pattern deviation** · **Resource
stewardship** · **Household operations**

See `docs/architecture.md` for the full definition of each.

## Steward data flow

1. Authenticate to HA Core over the Supervisor WebSocket; read config from
   `sensor.abode_ai_autonomy_steward_config`.
2. Subscribe to `state_changed` / `mobile_app_notification_action` / trigger.
3. Any state change schedules a reasoning pass through a debounce (a
   `wake_filter` suppresses noisy entities — a stop-gap until Vigil exists).
4. `_reason()` gathers the state snapshot and calls the AI Engine
   (`ai_task.generate_data`) with the charter, approved types, and snapshot.
5. `_handle_decision()` gates: confidence → completeness → Ward → execute
   (approved) or propose (new).

## Layer rules

1. **Steward never polls.** Wakes on events only; a debounce coalesces bursts.
2. **Stateless per pass.** Every pass fetches the complete current state, not
   a delta.
3. **The Ward is independent and append-only.** It checks every proposed
   action deterministically; nothing in the running system can edit or remove
   a rule.
4. **Two-part install.** The App depends on the companion integration for
   `notify_service` / `ai_task_entity` selectors.
5. **Approvals are nonce-bound and per action type**, never per instance.
6. **The charter is household-extendable data**, seeded to
   `/data/charter.md`; the Ward enforces the hard prohibitions, the model
   honours the conditional boundaries.

## Key principles (from the thesis)

- **Judgment, not lookup** — the home must handle situations nobody wrote a
  rule for.
- **Awareness ≠ deliberation** — cheap continuous salience gates expensive
  selective reasoning.
- **Wake on derived state, not raw state** — threshold crossings, not raw
  counter increments.
- **The Steward has no past** — history exists in HA's recorder, reachable
  over WebSocket; what's missing is the call, not the database.

## Decisions

The numbered design rules are in `docs/decisions/`. The five-component model
and six domains were locked 1 Aug 2026 in the architecture theses under
`docs/source/`.

## Known issues / next work

- **Vigil is not built** — the wake filter is a stop-gap.
- **No history wired in** (Y1).
- Frigate and Tara not wired as System 0 inputs.
- See `docs/architecture.md` for the full gap list and open questions.
