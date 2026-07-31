# Abode AI Autonomy Steward

A Home Assistant App that continuously reasons about your home's current state, proposes actions for one-time approval, then acts autonomously - bounded by an append-only constraint layer that only ever grows stricter.

Abode AI Autonomy Steward is the continuous reasoning layer of your autonomous home (System 2,
in the four-layer architecture this project settled on: System 0 is
perception - Home Assistant's sensors, and later Frigate/Tara; System 1 is
fast deterministic automations; System 2 is Abode AI Autonomy Steward; and a separate,
independent constraint layer gates everything Abode AI Autonomy Steward proposes before it
can execute).

## This App requires a companion integration

This App's own options have no entity/service selector type, so
`notify_service` and the AI Task entity are **not** configured here.
Install and configure `custom_components/abode_ai_autonomy_steward_config`
first (Settings → Devices & Services → Add Integration → search
"Abode AI Autonomy Steward Config") - it provides real entity/service pickers
validated against your actual HA data, and exposes the result as
`sensor.abode_ai_autonomy_steward_config`, which this App reads.

## What it does

Abode AI Autonomy Steward subscribes to Home Assistant's event stream and
actively waits - it is never on a timer, never polling. When anything
changes, it wakes, pulls the complete current state fresh - not a diff,
not an accumulated history, the whole picture as it stands right now -
and reasons about whether anything is worth doing. A burst of several
changes at once coalesces into a single reasoning pass rather than firing
one per event, but the wake condition is always "something changed,"
never "time has passed."

If it decides something is warranted:

- **New kind of action:** it proposes it to you (a mobile notification with
  Approve / Deny / Never). It does not act until you approve.
- **Already-approved kind of action:** it still decides fresh, every time,
  whether this specific moment actually calls for it - approval of a kind
  of action isn't a standing order to fire whenever a similar trigger
  appears.
- **A better way to do something already approved:** it can propose
  retiring or replacing an approved action, which goes through the same
  approval step.

## The constraint layer

Separate from Abode AI Autonomy Steward's own reasoning entirely. Every proposed action is
checked against `constraints.yaml` before it's allowed to execute - even
one you've already approved. Tapping **Never** on any proposal doesn't
just decline it once, it permanently appends a new rule to that file.
Nothing in the running system can ever remove a constraint once added -
that file only grows stricter over time. The only way a constraint goes
away is you editing `constraints.yaml` directly.

## Configuration

| Field | Where it's set | Description |
|---|---|---|
| `notify_service` | Companion integration (entity selector) | Real `notify.*` service used for approval prompts |
| `ai_task_entity` | Companion integration (entity selector) | Real `ai_task.*` entity used for reasoning passes |
| `min_confidence` | This App's Configuration tab | Won't act or propose below this confidence (0-1) |

## Status

Second build. First build wrongly used a fixed polling interval;
corrected to genuine event-driven wake. Unexercised in production either
way. Frigate and Tara are not yet wired in as input sources, but the code
is structured so adding them later doesn't require redesigning the
reasoning loop.
