# Backlog — open items, 31 July 2026 (rev 3)

**Supersedes:** `hapve-backlog-2026-07-31-v2.md`. Same three-section structure
(WORK / DECISION / VERIFICATION), extended with the steward findings from the
second half of 31 July.

| Section type | What it holds |
|---|---|
| **WORK** | Things to build or do. |
| **DECISION** | Waiting on Jason, not on effort. |
| **VERIFICATION** | Built but unproven. A confidence register. |

**Status values:** `BLOCKED`, `READY`, `DECIDE`, `VERIFY`, `CLOSED`, `DEFERRED`.

---

## 0. WHAT 31 JULY FOUND — read this first

Three defects, all of the same shape: **a broken state and a working state
looked identical in the logs.** None would have been found without being
tested for directly.

1. **`search_entities` reported `count: 20` against a real total of 52.** The
   tool lied to the model; the model reported faithfully. Fixed in
   `abode-ai-tools` 0.4.0, verified live.

2. **The constraint layer had never enforced anything.** `constraints.yaml`
   was in the repo but the Dockerfile never copied it, and nothing but
   `add_never_rule()` ever wrote `/data/constraints.yaml`. `_load()` returned
   `[]`, `is_blocked()` returned `(False, "")` for every action, silently,
   since the App was first built. Fixed in steward 0.4.1, verified live.

3. **`_reason()` has effectively never run.** The debounce cancels and
   restarts on every event, so a pass requires 5 full seconds of silence
   across the entire house. Measured against the real log: 342 wake triggers
   in 211 s, 97/min, **median gap 0.00 s**, and only 3 gaps ≥ 5 s — two of
   which were the 94 s window when Core was down. **Not yet fixed.**

Finding 3 is the significant one. Every assumption about System 2's
behaviour — pass duration, prompt size, whether `min_confidence: 0.70` is
sane — rests on passes that have never happened.

---

## A. WORK — `abode-ai-tools`

| # | Item | Status |
|---|---|---|
| A1 | `state` filter + true total count | **CLOSED** 0.4.0, verified V3 |
| A2 | Area matching via the area registry, bidirectional, alias-aware | **CLOSED** 0.4.0, verified V5 |
| A3 | `known_areas` returned on an unmatched area | **CLOSED** 0.4.0, verified V6 |
| A5 | **Prefer exact area matches.** Bidirectional matching over-matches when one area name is a prefix of another: "downstairs bathroom" matched area `Downstairs` and pulled in a scene and two front-door sensors | READY — deferred, avoided by N1 |
| A6 | `device_class` parameter | **WITHDRAWN** — not justified by testing; the model self-corrects when a better query exists (V6) |
| A7 | Truncation note is domain-blind ("narrow with state" is useless for `sensor`) | READY, low value |

## B. WORK — repositories

| # | Item | Status |
|---|---|---|
| B4 | `abode-ai-tools` repo description and topics still empty; HACS uses the description in its UI | READY |
| B5 | `manifest.json` → `documentation` points at HA's `llm.py`, not the repo. `codeowners` empty. Applies to **both** repos | DECIDE — GitHub handle |
| B6 | `hacs.json` → `"homeassistant": "2025.5.0"` is **[A]**, copied from the steward, never checked | READY |
| B8 | Brand images cannot work in the **HACS store listing** — files aren't on disk until after download, so HACS falls back to the CDN. Only a brands PR fixes it, which falls under the OHF policy and step 4a | DEFERRED |
| B9 | Steward `config.yaml` and `repository.yaml` pointed at `ha-ai-autonomy-steward`, a repo that does not exist. Corrected to `abode-ai-autonomy-steward` in 0.4.0 | CLOSED |

## S. WORK — steward

| # | Item | Status |
|---|---|---|
| S1 | Rename to Abode AI Autonomy Steward; domain, slug, entity id, repo, brand assets | **CLOSED** 0.4.0, installed and verified |
| S2 | Seed `/data/constraints.yaml`; refuse to start on zero rules; log rule count | **CLOSED** 0.4.1, verified V13 |
| S3 | **Log when a reasoning pass starts, completes, and what it decided.** A pass that never fires currently looks identical to one that fires and proposes nothing — the same failure shape as S2. Evidence-gathering, not a design commitment | **READY — do this first** |
| S4 | **The debounce starves under real load.** `_schedule_reasoning_pass()` cancels and recreates the task on every event, so a pass needs 5 s of total silence. Blocked on S3: no pass has ever been observed, so pass duration and cost are unknown, and fixing the trigger before seeing a pass repeats the mistake that produced S2 | BLOCKED on S3 |
| S5 | **Attribute-only updates are treated as state changes.** `old_state` is never read. Per `core.py` `async_set_internal` (lines 2455–2495): same state + same attributes fires `state_reported` only, but same state + *different* attributes fires `state_changed` anyway. Measured impact: 16 of 342 events (~5%) — real, but not the cause of S4 | READY, low value |

## C. DECISION — outstanding

| # | Item | Status |
|---|---|---|
| C1 | **Is Paperless in scope for `abode-ai-tools`?** Asked three times on 31 Jul, unanswered. `paperless.py` ships on Claude's assumption, not a decision. Costs nothing while unconfigured | **DECIDE** |
| C2 | Measure core `mcp` client against paperless-mcp; token count decides whether `paperless.py` lives, dies, or moves to its own component. May be blocked on whether paperless-mcp was ever deployed | DECIDE + VERIFY |
| D2 | App slug change cost — **now answered by evidence.** `/data` held only `options.json` (27 bytes). Nothing else was ever written. Cost of the slug change was zero | CLOSED |
| E2 | Is HACS OHF-governed? Classified upstream-bound precautionarily, unverified | READY |

## X. DESIGN — the wake question

The largest open architectural question, and the one that should get a fresh
session rather than the tail of a long one.

**X1 — What should make System 2 stop and look?**

Established on 31 Jul, in order:

- **Filtering alone does not fix liveness.** Modelled against the real log: a
  domain allowlist cuts 342 events to 93 (27%) and lifts completed passes
  from 3 to 8 in 211 s. Better odds, not a guarantee.
- **A max-wait cap is a timer with an event-shaped excuse.** Rejected on
  Jason's standing principle that the steward is not timer-driven.
- **"Telemetry is not an event" was wrong.** A solar counter incrementing can
  absolutely mean something: generation falling below consumption, with the
  battery under reserve and price high, is one of the strongest autonomy
  cases in this house. Claude proposed the event/telemetry split and Jason
  correctly rejected it.
- **The real distinction is sample versus threshold crossing.** 793.516 →
  793.525 is not a fact about the house. "Solar deficit while battery is
  under reserve and price is high" is a fact, is discrete, and is rare.
- **Therefore the wake set is derived state, not raw state.** HA already has
  threshold helpers, template binary sensors, trend and statistics sensors.
  System 2 wakes on `binary_sensor.solar_deficit` transitioning, not on the
  counter beneath it.
- **Threshold crossings are naturally seconds-to-minutes apart, so the
  debounce completes on its own.** No cap, no clock, no forcing. The current
  mechanism is not wrong; it is being fed the wrong thing.

**Critically: filtering the wake set removes no information from reasoning.**
`_reason()` calls `gather_state()`, which issues a fresh `get_states` and
hands the model *"Current complete state"* — every entity, every value. The
event stream decides *when*; the snapshot decides *what is seen*. These were
conflated for most of the discussion and they are separate.

Which makes the current behaviour worse than it first appeared: a solar
counter schedules a pass, the next increment cancels it, the pass never runs,
and **the snapshot that would have shown the deficit is never built. The
telemetry is starving the reasoning it exists to feed.**

**Open input needed from Jason:** which conditions in this house constitute
something worth stopping to look at. Energy first, on his own argument.

## Y. DESIGN — memory

**Y1 — System 2 has no past.**

`get_states` is instantaneous. "Solar generation has *fallen*" is a claim
about time, and nothing in the current design carries time. The model is
handed a frozen present and asked whether action is warranted — it cannot
know whether the battery has been draining for an hour or just started,
whether someone has been out all day or just walked out.

**The database already exists and is already reachable.** Verified in HA
source, 31 Jul, over the same authenticated WebSocket the App already uses:

| Command | Source | Gives |
|---|---|---|
| `recorder/statistics_during_period` | `components/recorder/websocket_api.py:268` | `statistic_ids`, `start_time`, `period` of `5minute`/`hour`/`day`/`week`/`month`/`year`; returns `min`, `max`, `mean`, `sum`, `change`, `state` |
| `recorder/list_statistic_ids` | same, line 320 | what is available |
| `history/history_during_period` | `components/history/websocket_api.py:98` | raw state history for named entities, with `significant_changes_only`, `no_attributes`, `minimal_response` |

Every sensor with a `state_class` is already in long-term statistics —
Powerwall, consumption, price. "Has generation fallen" is one call.

**A separate state database is rejected**, on three grounds:

1. Duplication — a second copy of numbers HA already keeps, with its own
   retention, corruption and backup story.
2. `/data` is not durable. The slug change demonstrated exactly that.
3. It cannot live on the intranet regardless. Postgres and Qdrant are
   available there, but hapve carries no home-automation dependency on the
   intranet by design, and that principle does not bend for convenience.

**What is missing is the call, not the database.**

**Open design questions, none trivial:**

- Which entities get history, over what window
- Statistics versus raw history — statistics are pre-aggregated and far
  cheaper, and for energy strictly better than raw samples
- Payload. This is the `abode-ai-tools` problem again: 212 active entities,
  an already-large snapshot, and prefill becoming the constraint on **every
  reasoning pass** rather than every voice turn
- Whether "what changed since the last pass" is the right frame — which would
  require the App to remember when the last pass was, the first genuinely
  stateful thing it would do

## N. STANDING RULES

| # | Rule |
|---|---|
| N1 | **No area name may be a prefix of another.** Verified clean across all 18 areas, 31 Jul. A future "Deck Chairs" beside "Deck" would hit it silently — wrong results, no error. A5 remains the durable fix |
| N2 | **Versioning.** Patch (`0.x.N`) for fixes that break nothing. Minor (`0.N.0`) for features **or** anything that breaks an existing install. Mixed changes take the highest bump |
| N3 | **Hand-write a component only where result size must be capped in code**; use HA core's native `mcp` client everywhere else |
| N4 | Domains use underscores; repos use hyphens |
| N5 | **System 2 gains no outbound write capability to any OHF-governed repository** |
| N6 | n8n not on hapve until a specific workflow demands it |
| N7 | **No manual workarounds.** Every fix ships as a full repo update with a new version. No hand-placed files, no seeding by hand — 31 Jul |
| N8 | **hapve carries no home-automation dependency on the intranet.** Reaffirmed 31 Jul against the convenience of reusing Postgres/Qdrant for state history |

## V. VERIFICATION REGISTER

### Closed 31 July — measured

| # | Item | Evidence |
|---|---|---|
| V1 | Config flow loads; entry created; `single_config_entry` accepted | [M] |
| V2 | **Reload works** — the unregister callable on `entry.runtime_data`. Reloaded twice, no "API already registered" | [M] — the load-bearing claim of the config-flow rewrite, pure source-reading until this point |
| V3 | `state` filter + true count. Ground truth `['light.hallway']`/48; tool returned 1, `count: 1`; assistant named it; **Jason confirmed visually** | [M] 02:02 |
| V4 | The 0.3.1 failure captured deliberately before fixing: 4 lights on, assistant named 1, `count: 20` against 52 | [M] 01:37 |
| V5 | Area resolution, including entities inheriting area via device | [M] 02:39 |
| V6 | `known_areas` on unmatched area, **and model self-correction** — "cellar" → error + 12 rooms → model issued a *second* call and answered from verified data | [M] 04:52 |
| V7 | Local `brand/` images work on the integrations page, no brands PR (HA 2026.3+) | [M] |
| V13 | **Constraint seeding and fatal-on-zero.** `Seeded /data/constraints.yaml from shipped charter defaults` then `Constraint layer active: 2 rule(s) in force` | [M] 15:45:55 |

### Still unproven

| # | Item | Status |
|---|---|---|
| V8 | **Bidirectional and alias area matching unexercised.** No area in this house is longer-spoken-than-named; no aliases set. Ten standalone unit cases pass, but that is Claude's harness, not this house | **[A]** |
| V9 | **No spoken turn has ever completed.** All latency figures are text through the Assist dialog. STT/TTS unmeasured; five ESPHome satellites offline (Q9) | **VERIFY** |
| V10 | **Constraint layer blocking a real action.** Now testable for the first time — rules exist as of 0.4.1 — but entangled with V11 | **Not tested** |
| V11 | **A reasoning pass has never been observed.** See §0 finding 3. Blocks V10, and every parameter that depends on pass behaviour | **Not tested** |
| V12 | `sensor.abode_ai_autonomy_steward_config` attributes read in Developer Tools | Partially closed — the App logged `Config applied: notify via notify.jason_s_tablet, AI Task entity ai_task.abode_ai_lemonade_gemma_4_26b_a4b_it_gguf_ai_task`, so the attributes are confirmed present and correct |

## P. PERFORMANCE — 31 July, text path only

| Query | Tool result | First token | Total |
|---|---|---|---|
| "which lights are on" (0.3.1) | 20 records | 3.9 s | 4.37 s |
| "which lights are on" (0.4.0) | 1 record | ~1.3 s | **1.79 s** |
| "what sensors do we have" | 20 records + note | 3.13 s | 7.69 s |
| "temperature in the cellar" | 2 calls | 3.6 s | 5.30 s |

**Prefill is no longer the constraint; decode is.** Tool-result size drives
both time-to-first-token and total.

**Time-to-first-token matches felt experience on the text path** because
output streams at reading speed. It will not for voice: TTS cannot begin
until there is something to synthesise, and whether the pipeline streams to
Kokoro is untested (V9).

**Steward event load, measured:** 342 wake triggers / 211 s / 97 per minute /
212 distinct entities / median gap 0.00 s. By domain: `sensor` 45%,
`binary_sensor` 13%, `update` 13%, `light` 10%. No single culprit — the
noisiest entity accounts for 18. This is a large, well-instrumented house
behaving normally.

## Q. CARRIED FORWARD

| # | Item |
|---|---|
| Q1 | **ANSWERED.** Which entities drive frequent wakes: 212 of them, spread across the estate, dominated by numeric telemetry. Not one misbehaving integration |
| Q3 | Frigate and Tara not wired in as System 0 inputs; both stubbed |
| Q4 | **ANSWERED and superseded.** `DEBOUNCE_SECONDS = 5` is not merely an unmeasured placeholder — the mechanism does not survive contact with this house. See S4/X1 |
| Q5 | **ANSWERED.** Entity filtering is needed — but as a *wake* filter only, not a filter on what the model sees |
| Q9 | Five ESPHome satellites offline, blocking all spoken-turn measurement |
| Q17 | **Confirmed in the wild.** Renovation lights reported `on` while physically disconnected; ground truth itself was stale. Resolved by disabling, not by code. General problem stands for any device that drops off without going `unavailable` |

## R. HOUSEHOLD DISCIPLINE

Not Claude's work, but what the tool's performance scales with.

- **Entities with no area cannot be reached by area filtering** — only by name
  or an unfiltered scan, the shape that hits the 20-cap. Substantial progress
  31 Jul: PIRs moved from `area: ""` to Living Room and Outside
- **Sensors reporting `unknown` are pure cost** — cap slots and decode time,
  never an answer. Four exposed PIRs were in this state
- **One exposed temperature sensor per area.** Living Room had two
- Group members removed from exposure; renovation entities disabled
- New entities are not exposed by default — invisible to the assistant until
  someone exposes them and gives them a speakable name

---

## Critical path

**S3 first.** Log when a pass starts, completes and decides. Everything about
System 2 is currently inference from an absence, and fixing the wake
mechanism before seeing a single pass would repeat exactly the mistake that
left the constraint layer empty for a day.

**Then X1** — which conditions are worth stopping for — with real passes to
reason about rather than a model of them.

**Y1 after that.** Memory is the larger prize but it compounds the payload
problem, and it should not be designed before a pass has been watched.

**C1 remains the only thing gating `abode-ai-tools`.**

**V9 remains the largest untouched gap.** Every latency figure is text
through a chat dialog. Nothing about the actual voice path — wake word, STT,
TTS, satellite round-trip — has ever been measured, and the 1–3 s target was
always about a spoken turn.
