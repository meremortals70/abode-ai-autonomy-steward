# Handover — Continuous Autonomy: original intent vs. what was built

**Supersedes:** nothing standalone — read alongside
`hapve-asbuilt-continuous-autonomy-2026-07-30.md`, which records the code as
it exists. This document exists because the built system does not match the
intent, and that gap needs to be carried forward explicitly rather than
discovered again next session.

---

## 1. Original intent, as Jason described it (2026-07-30)

Quoting directly, not paraphrasing:

> "it is not about watching state changes. Its about watching the autonomous
> home and reasoning based on what is happening I can do this to make the
> residents life easier. presenting that for approval and once approved it
> becomes a permanent part of the autonomous home until the ai thinks of
> something better. It forms a charter for what is the autonomous home, how
> it behaves and the boundaries of what the ai is allowed to do in the home."

Broken into its parts:

1. **The subject of reasoning is the autonomous home as a whole** — its
   ongoing state and what is happening in it — not a specific entity or a
   specific event.
2. **The purpose is explicit**: find ways to make residents' lives easier.
   This is a goal the reasoning is aimed at, not just a trigger to react to.
3. **Approval, once granted, is permanent** — it becomes part of the home's
   standing behaviour, not a one-off action. This matches what was built for
   the action-type gate (§4 of the as-built) — that part is aligned.
4. **The AI can revise its own approved behaviour** — "until the ai thinks
   of something better." An approved behaviour is not fixed forever; the AI
   itself can propose something better to replace it. Nothing in the current
   code allows this — approved types execute the same way indefinitely.
5. **A charter defines the home itself** — what the autonomous home *is*,
   how it behaves in general, and firm **boundaries** on what the AI may
   never do, regardless of any approval. Two examples given:
   - never cast explicit/inappropriate content to a TV
   - never turn on all the home's lights in the middle of the night, unless
     there is an intruder
   These are inviolable constraints on the AI's action space, not behaviours
   that get proposed and approved — they exist prior to and outside the
   approval mechanism entirely.

---

## 2. What was actually built

From the as-built: the app subscribes to `state_changed` for a fixed list of
`watched_entities` (chosen via the companion integration's entity picker).
When one of those specific entities changes state, the app calls
`ai_task.generate_data` once, scoped to that single event, and asks the
model whether *this* event warrants an action. The `CHARTER` constant given
to the model on every call is entirely procedural — it tells the model how
to name and gate a decision, but says nothing about what the home is, how it
should generally behave, or what it is forbidden from doing.

## 3. The gap, explicitly

| Intent | Built | Gap |
|---|---|---|
| Reason about the home as a whole, continuously | Reason about one entity's state change, per event | Architecture is reactive/event-scoped, not continuous/holistic |
| Purpose: make residents' lives easier | No purpose statement in the charter at all | Charter has no "why," only "how to gate an action" |
| Approval becomes permanent | Approval becomes permanent (action_type persisted) | **This part matches intent** |
| AI can later propose something better than an approved behaviour | No mechanism to reconsider or replace an approved action_type | Missing entirely |
| Charter defines the home + firm boundaries (e.g. no explicit content to TV, no whole-home lighting at night without an intruder) | Charter has zero boundary/prohibition content | Missing entirely — this is a safety-relevant gap, not just a completeness one |

**Root cause of the gap:** earlier in this project, "watch specific entities
and react to their state changes" was treated as an implementation detail of
"continuous reasoning over the home," rather than being recognised as a
different, narrower architecture. That substitution was never checked
against Jason's actual words until he corrected it directly on 2026-07-30.
This is recorded as a FALSIFIED decision in the as-built (§4), not silently
replaced.

---

## 4. Confirmed working (evidence class attached)

- App installs from the repo, starts, authenticates to HA Core [M, Jason,
  2026-07-30].
- Companion integration installs via HACS, config flow renders a real entity
  picker, `watched_entities` field accepts a real HA entity [M, Jason
  screenshot, 2026-07-30].
- The approval-is-permanent mechanism (persist `action_type` to
  `/data/approved_action_types.json`, never re-ask for that type) exists in
  code and matches this one part of the stated intent. **Not yet exercised
  live** — no approval has actually been tapped and confirmed persisted.

## 5. Confirmed broken / wrong

- The reasoning trigger is per-watched-entity-state-change, not
  whole-home / continuous, per Jason's explicit correction. This is a
  design defect, not a bug — the code does exactly what it was written to
  do; what it was written to do is not the requirement.
- No mechanism exists for the AI to propose retiring or improving an
  already-approved action_type.
- No charter content defines the home's general behaviour or any firm
  boundary. This is the more serious of the two missing pieces: the two
  examples given (explicit content to a TV; whole-home lighting at night)
  are safety/decency boundaries that should hold regardless of what any
  future approval grants — right now nothing in the system enforces or even
  states them.

## 6. Unverified — labelled loudly, not to be treated as confirmed

- What the notification Jason saw after submitting the config form actually
  said, and whether it came from `reason_about()` firing on a real state
  change to the Hallway entity, or from something else. No log or
  notification text was captured. **Do not assume this was the approval
  gate working correctly** — it has not been checked.
- Whether `sensor.continuous_autonomy_config` was ever actually created —
  the config form's screenshot showed `notify_service` still empty and
  Submit not yet confirmed clicked.
- Whether an HA Core restart leaves the app running uninterrupted — never
  tested.

---

## 7. Open questions (carried from as-built §7, restated here for the
handover)

**Q1.** What should actually trigger a reasoning pass, if not per-entity
`state_changed`? Options not yet evaluated: a periodic tick (e.g. every N
minutes, reasoning over a snapshot of relevant home state); reasoning on any
state_changed home-wide with the model itself deciding relevance rather than
a pre-filtered watch-list; some hybrid. This needs a decision, not an
assumption.

**Q2.** How does "AI thinks of something better" get implemented —
does the AI get shown its own list of currently-approved action_types on
each reasoning pass and get the option to propose retiring/replacing one,
with that proposal going through the same one-time approval gate as a new
action_type?

**Q3.** What is the actual content of the charter's boundary section —
this needs Jason's input directly, since these are value judgments about
what the home must never do, not something to infer. The two examples given
are a start, not an exhaustive list.

**Q4.** Is the current app/integration split (Supervisor app +
custom_component for the entity picker) still the right shape once the
trigger mechanism changes from per-entity to whole-home? The
`watched_entities` concept may not survive a redesign around Q1 — worth
deciding before writing more config-flow code that assumes it will.

---

## 8. Next action, and what gates it

Nothing further should be built until Q1 and Q3 are answered — building a
"better" reasoning trigger without knowing what should trigger it, or
writing charter boundary content without Jason's actual list of
prohibitions, would repeat the same failure mode that produced this gap.
Recommended order: Q3 first (Jason states the boundaries directly — this is
his call, not a technical decision), then Q1 (architecture for what triggers
a reasoning pass), then Q2 (revision mechanism) once the first two are
settled.
