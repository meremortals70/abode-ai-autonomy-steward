# AI Autonomy Steward

A Home Assistant App that continuously reasons about your home's current
state, proposes actions for one-time approval, then acts autonomously -
bounded by an append-only constraint layer that only ever grows stricter.

Part of the Abode AI Autonomy system. In its four-layer architecture:
System 0 is perception (Home Assistant's sensors, and later Frigate/Tara),
System 1 is fast deterministic automations, **System 2 is this App**, and a
separate, independent constraint layer gates everything it proposes before
execution.

## What it does

Every cycle, it pulls the complete current state of your home fresh - not
a diff, the whole picture, every time - and reasons about whether anything
is worth doing.

- **New kind of action:** proposed to you via mobile notification
  (Approve / Deny / Never). It does not act until approved.
- **Already-approved kind of action:** still decides fresh, every cycle,
  whether this specific moment actually calls for it.
- **A better way to do something already approved:** it can propose
  retiring or replacing an approved action, subject to the same approval
  step.

## The constraint layer

Independent of the reasoning above. Every proposed action - including
already-approved ones - is checked against `constraints.yaml` before it's
allowed to execute. Tapping **Never** on any proposal permanently appends
a new rule. Nothing in the running system can remove a constraint once
added; the file only ever grows stricter. Constraints are only ever
removed by editing `constraints.yaml` directly, outside the running app.

## Installation

1. Settings → Add-ons → Add-on Store → ⋮ → Repositories → add this repo's
   URL.
2. Find **AI Autonomy Steward** in the store → Install.
3. Configuration tab → set `notify_service` to your real notify target
   (e.g. `notify.mobile_app_your_phone`).
4. Confirm the `AI_TASK_ENTITY` constant near the top of
   `ai_autonomy_steward.py` matches your actual AI Task entity's
   `entity_id` before first start.
5. Start the app, check the Log tab for confirmation it authenticated
   against HA Core and began its reasoning cycle.

## Configuration

| Option | Description |
|---|---|
| `notify_service` | The `notify.*` service used for approval prompts |
| `min_confidence` | Won't act or propose below this confidence (0-1) |
| `cycle_delay_seconds` | Pause between reasoning passes - a throttle on GPU load, not a schedule it waits on |

## Status

First build, unexercised in production. Frigate and Tara are not yet
wired in as input sources - the code is structured so they can be added
later without redesigning the reasoning loop.

## License

MIT
