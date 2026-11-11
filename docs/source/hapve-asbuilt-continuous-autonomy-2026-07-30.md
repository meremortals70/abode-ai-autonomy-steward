# As-built — Continuous Autonomy app + Continuous Autonomy Config integration

**Supersedes:** nothing — first as-built for this component. `abode_autonomy`
(custom_component, never deployed) and Sentinel (HGA's rule-execution engine)
were both considered and rejected as the mechanism; neither is superseded by
this because neither was ever the thing running. See the handover document
dated 2026-07-30 for why this build itself is now also being superseded in
design, if not yet in code.

**Repo:** `https://github.com/meremortals70/ha-continuous-autonomy`, `main`
branch. Root contains `continuous_autonomy/` (app), `custom_components/
continuous_autonomy_config/` (integration), `hacs.json`, `repository.yaml`.

---

## 1. Status

**Component verified.** The app installs from the HA App Store via the repo
URL, starts, and authenticates against HA Core over the Supervisor-proxied
WebSocket. The integration installs via HACS custom repository, its config
flow renders a real entity picker, and submitting it creates
`sensor.continuous_autonomy_config` with the submitted attributes. This was
confirmed by Jason directly (screenshot, 2026-07-30) — integration installed,
one entity selected in the `watched_entities` field.

**Not system verified.** No end-to-end run has been confirmed against actual
household events with a log paste showing `Config applied: ...` /
`Watching [...] ...` and a correct decision. A notification was observed
firing after config submission, but its content and the app's log at that
timestamp were never captured before this document was requested — so the
one live behaviour observed so far is **unconfirmed as correct or
incorrect**, not verified either way.

**Known wrong at the design level.** Per Jason (2026-07-30, this session):
what got built reasons per watched-entity state change, not "about what is
happening in the autonomous home" as a whole. See the handover document —
this as-built records what exists; it does not claim the design is right.

---

## 2. Role

Two files make up this component:

- **`continuous_autonomy`** — an HA App (Supervisor-managed container),
  independent of HA Core's own restart cycle. Holds a charter and an
  approved-action-types list in memory for the life of the process. Calls
  `ai_task.generate_data` over the Core WebSocket API whenever a watched
  entity's state changes.
- **`continuous_autonomy_config`** — a custom_component (runs inside HA
  Core, restarts with it). Exists solely because Supervisor App options have
  no entity-picker schema type (confirmed against the current App
  configuration docs: only str/bool/int/float/email/url/password/port/
  match/list/device are available). Exposes its config-flow output as
  `sensor.continuous_autonomy_config`'s attributes, which the app reads live.

---

## 3. Configuration — verbatim

### `continuous_autonomy/config.yaml`

```yaml
name: "Continuous Autonomy"
version: "0.1.0"
slug: "continuous_autonomy"
description: "Continuous AI reasoning over live entity state — decides fresh on every relevant event, gates a new kind of action once for approval, then acts on that kind autonomously forever after. Runs as its own app so an HA Core restart never interrupts it. REQUIRES the companion 'Continuous Autonomy Config' integration (installed separately via HACS) to be configured first — see DOCS.md."
url: "https://github.com/meremortals70/ha-continuous-autonomy"
arch:
  - aarch64
  - amd64
init: false
homeassistant_api: true
startup: services
boot: auto
```

Note the description line is itself evidence of the design gap: "decides
fresh on every relevant event" is the reactive, per-entity model Jason has
said is not the intent.

### `continuous_autonomy/Dockerfile`

```dockerfile
FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3 py3-pip
RUN pip install --no-cache-dir --break-system-packages aiohttp

COPY continuous_autonomy.py /continuous_autonomy.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
```

`FROM ghcr.io/home-assistant/base:latest` is explicit, not `ARG BUILD_FROM` /
`FROM $BUILD_FROM` — Supervisor 2026.04.0 stopped auto-injecting `BUILD_FROM`
[V, current App build docs]. Using the old pattern was the root cause of the
app not appearing in the store on first upload; fixed same day.

### `continuous_autonomy_config/manifest.json`

```json
{
  "domain": "continuous_autonomy_config",
  "name": "Continuous Autonomy Config",
  "version": "0.1.0",
  "config_flow": true,
  "iot_class": "local_push",
  "codeowners": [],
  "requirements": [],
  "dependencies": []
}
```

### `continuous_autonomy_config/config_flow.py` (schema portion)

```python
def _schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_WATCHED_ENTITIES,
                default=defaults.get(CONF_WATCHED_ENTITIES, []),
            ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
            vol.Required(
                CONF_NOTIFY_SERVICE,
                default=defaults.get(CONF_NOTIFY_SERVICE, vol.UNDEFINED),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="notify")),
            vol.Optional(
                CONF_MIN_CONFIDENCE,
                default=defaults.get(CONF_MIN_CONFIDENCE, 0.70),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1, step=0.01)
            ),
        }
    )
```

Singleton entry enforced via `async_set_unique_id(DOMAIN)` +
`_abort_if_unique_id_configured()`. Options flow reuses the same schema
pre-filled with current values, so reconfiguring doesn't require removing
the integration.

### `continuous_autonomy.py` — reasoning trigger (the part now in question)

```python
if event_type == "state_changed":
    ev_data = event.get("data", {})
    entity_id = ev_data.get("entity_id", "")
    new_state_obj = ev_data.get("new_state") or {}
    new_state = new_state_obj.get("state")

    if entity_id == CONFIG_ENTITY_ID:
        self._apply_config(new_state_obj.get("attributes") or {})
        continue

    if entity_id in self.watched_entities and new_state is not None:
        asyncio.create_task(self.reason_about(entity_id, new_state))
```

This is the literal trigger: one specific entity changes state → one
`ai_task.generate_data` call scoped to that single event. There is no
periodic or whole-home reasoning pass, and no mechanism for the AI to review
or propose replacing an already-approved behaviour — approved
`action_type`s execute directly (see §4 below) with no re-evaluation of
whether that type is still the best approach.

### `CHARTER` constant — current content

```
You are not waiting to be asked. You continuously form your own judgment
about whether something in this home warrants action, using the live
state you're given. This is not a rule external to you — it is how you
operate, every time you're invoked.

When you conclude an action is warranted, follow this exactly:

1. Decide what KIND of action this is. Give it a short, stable
   action_type name...
2. If you have not been told this action_type is already approved, treat
   it as new: set action_needed true, name the type, explain your
   reasoning in one sentence, and propose the action...
3. If you have been told this action_type IS already approved..., you may
   act without asking — but you must still decide, fresh, right now,
   whether the current situation actually calls for it...
4. Never generalize an approval beyond what was granted...
5. If nothing is warranted right now, set action_needed to false...
```

No boundary/prohibition content exists in the charter at all — no equivalent
of "never cast explicit content to a TV" or "never turn on all lights at
night absent an intruder." The charter only tells the model how to name and
gate actions; it does not define what the home is, how it should behave, or
what it is forbidden from doing.

---

## 4. Decisions

```
DECISION: App (Supervisor container) + companion custom_component, not a
          single custom_component
DATE: 2026-07-30
CHOSE BECAUSE: custom_components restart with HA Core; this must survive
               Core restarts/updates [reasoned, not measured]
REJECTED: Sentinel (HGA) — read docs/sentinel.md at installed tag v3.21.3:
          approved rules execute via deterministic condition checks, not
          fresh LLM reasoning per instance [M, source read]
EVIDENCE CLASS: [V] — HA App/Supervisor docs on restart independence
FALSIFIED IF: an HA Core restart is observed to interrupt the app's process
              (not yet tested)
```

```
DECISION: Approval gate is per action_type string, not per instance
DATE: 2026-07-30 (carried from earlier design discussion)
CHOSE BECAUSE: Jason's explicit requirement — approve once per kind of
               action, then autonomous forever for that kind, AI still
               reasons fresh each time
REJECTED: per-instance approval (defeats "autonomous"); static automation
          YAML (defeats "continuous reasoning, not rigid rules")
EVIDENCE CLASS: [A] — matches stated intent, not yet validated against a
                real decision sequence
FALSIFIED IF: the AI is observed reusing an action_type name across two
              decisions that are not actually the same kind of action, or
              failing to re-ask when it should generalize narrowly instead
```

```
DECISION: Trigger reasoning on watched-entity state_changed events
DATE: earlier in this project, not re-litigated until 2026-07-30
CHOSE BECAUSE: assumed equivalent to "reasoning about what's happening in
               the home" [A — this assumption is now explicitly rejected
               by Jason, see handover]
REJECTED: nothing else was considered at the time — this is the gap
EVIDENCE CLASS: [A] — assumption, not a decision made against stated intent
FALSIFIED IF: Jason states this is not what "reasoning about the autonomous
              home" means — TRUE, 2026-07-30. This decision is FALSIFIED.
              The reasoning error: "watch entities and react to their state
              changes" was treated as an implementation detail of continuous
              reasoning, when it is actually a different, narrower
              architecture (reactive/event-scoped vs. continuous/holistic).
```

---

## 5. Verification

| Check | Result | Conditions | Not tested |
|---|---|---|---|
| App appears in HA App Store from repo URL | Pass | after Dockerfile/config.yaml fix, confirmed by Jason screenshot | — |
| App installs and starts | Pass [M, Jason, 2026-07-30] | — | log output not captured |
| Integration installs via HACS custom repository | Pass [M, Jason, 2026-07-30] | — | — |
| Config flow renders real entity picker | Pass [M, Jason screenshot, 2026-07-30] | `watched_entities` field showed and accepted "Hallway" | `notify_service` and `min_confidence` not yet submitted at time of screenshot |
| `sensor.continuous_autonomy_config` created with correct attributes | **Not tested** | form not yet submitted | — |
| App reads config live via `get_states` / `state_changed` on the config sensor | **Not tested** | — | no log paste obtained |
| `ai_task.generate_data` call succeeds against this HA Core version | **Not tested** | — | no log paste obtained |
| Notification fires with correct title/message/actions on new action_type | **Unverified — one notification observed, content not captured** | Jason reported "why is it notifying me?" after config screen appeared | content, and whether this is the approval-gate notification or something else, unknown |
| Approval action round-trip (tap Approve → type persisted → service called) | **Not tested** | — | — |
| Persistence across app restart (`/data/approved_action_types.json`) | **Not tested** | — | — |
| HA Core restart does not interrupt the app | **Not tested** | — | — |

---

## 6. Quirks

- Supervisor App options schema has no entity type — confirmed against
  current docs, not assumed. This is why the companion integration exists
  at all.
- `BUILD_FROM` is no longer auto-injected as of Supervisor 2026.04.0 — any
  future app in this repo needs `FROM ghcr.io/home-assistant/base:latest`
  explicit, not the old `ARG BUILD_FROM` pattern.
- GitHub's "Create new file" with a typed path only creates folders
  relative to whatever directory you're currently browsing, not always the
  repo root — this caused a folder to nest one level too deep during setup
  (`continuous_autonomy_config/custom_components/continuous_autonomy_config/`).
  Fixed by deleting the six wrongly-placed files via each file's
  `/blob/` → `/delete/` URL and re-uploading the correct
  `custom_components/continuous_autonomy_config/` tree via drag-and-drop
  from a locally-prepared folder structure — the same method that worked
  cleanly for the app folder originally.
- GitHub's per-file "..." menu in this account's current UI does not show
  a "Delete file" option; the reliable path is editing the file's own URL
  (`/blob/<ref>/<path>` → `/delete/<ref>/<path>`), which opens a delete
  confirmation page with its own commit button.

---

## 7. Open questions

**Q1.** Does the design need to change from "react to watched-entity state
changes" to "continuously reason over the whole autonomous home state"? —
Jason has stated yes (2026-07-30). What triggers a reasoning pass in the
corrected design (periodic tick? every state change home-wide? something
else?) is not yet decided. See handover.

**Q2.** How does an approved action_type get *revised* — the intent
includes "until the AI thinks of something better," which implies the AI
can propose changing or retiring something already approved, not just
adding new approved types. No mechanism for this exists in the current
code. Not yet designed.

**Q3.** What form does the "charter... how it behaves and the boundaries of
what the AI is allowed to do" take — Jason's examples (no explicit content
cast to TV; no whole-home lighting at night absent an intruder) are hard
boundaries, not learned/approved behaviours. The current `CHARTER` constant
has no boundary/prohibition section at all. Not yet designed.

**Q4.** What actually fired the notification Jason saw after submitting the
config screen — never captured (title, message, log timestamp). Needed
before any claim about current behaviour, correct or incorrect, can be made.
