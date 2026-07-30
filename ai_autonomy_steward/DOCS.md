# AI Autonomy Steward

A Home Assistant App that continuously reasons about your home's current state, proposes actions for one-time approval, then acts autonomously - bounded by an append-only constraint layer that only ever grows stricter.


AI Autonomy Steward is the continuous reasoning layer of your autonomous home (System 2,
in the four-layer architecture this project settled on: System 0 is
perception - Home Assistant's sensors, and later Frigate/Tara; System 1 is
fast deterministic automations; System 2 is AI Autonomy Steward; and a separate,
independent constraint layer gates everything AI Autonomy Steward proposes before it
can execute).

## What it does

Every cycle, AI Autonomy Steward pulls the complete current state of your home fresh -
not a diff, not an accumulated history, the whole picture as it stands
right now - and reasons about whether anything is worth doing. If it
decides something is warranted:

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

Separate from AI Autonomy Steward's own reasoning entirely. Every proposed action is
checked against `constraints.yaml` before it's allowed to execute - even
one you've already approved. Tapping **Never** on any proposal doesn't
just decline it once, it permanently appends a new rule to that file.
Nothing in the running system can ever remove a constraint once added -
that file only grows stricter over time. The only way a constraint goes
away is you editing `constraints.yaml` directly.

## Configuration

| Option | Description |
|---|---|
| `notify_service` | The `notify.*` service used for approval prompts, e.g. `notify.mobile_app_your_phone` |
| `min_confidence` | AI Autonomy Steward won't act or propose below this confidence (0-1) |
| `cycle_delay_seconds` | Pause between reasoning passes - a pragmatic throttle on GPU load, not a schedule AI Autonomy Steward waits on |

## Status

First build, unexercised. What AI Autonomy Steward can currently perceive is limited to
Home Assistant's own state - Frigate and Tara are not yet wired in as
input sources, but the code is structured so adding them later doesn't
require redesigning the reasoning loop.
