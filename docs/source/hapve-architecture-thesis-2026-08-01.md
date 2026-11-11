# Architecture Thesis — what an autonomous home is, and the check every proposal must pass

**Status:** standing, load-bearing. Not an as-built, not a decision log for a
single component — this is the document every proposal touching reasoning,
triggers, or the four-layer architecture is checked against, every session,
before any code or design is written. Referenced, not re-derived.

**Why this exists:** reached over one session, 1 Aug 2026, after three
successive proposals each solved a real problem while missing the actual
goal — hardening `constraint_layer.py`'s write path when the live danger was
on the read side; then fixing the debounce mechanism correctly while missing
that, unfiltered, it collapses to a fixed-interval poll under this house's
measured event rate. Each miss required the architect to stop the session and
ask "does this meet the requirement" — a check that should happen before a
proposal is made, not after. This document exists so that check has content
to run against, independent of any one session's memory.

---

## 1. What an autonomous home is

**It is a system that forms judgment about situations it was never explicitly
told how to handle.** Not one that executes more rules, however many,
however cleverly triggered. A house with five hundred automations that fire
correctly every time is not autonomous — it is deterministic, and its ceiling
is exactly the set of situations its author anticipated.

The charter (`ai_autonomy_steward`) already states the real bar:

> "You are not waiting to be asked. You continuously form your own judgment
> about whether something in this home warrants action, using the live state
> you're given."

**Judgment, not lookup.** The test for any proposed mechanism is not "did it
react correctly" — it is "could it have handled a combination of
circumstances nobody wrote a rule for."

This is also the standing reason Q8 (31 Jul) rejected a trained model over
logged outcomes as System 2's mechanism: a model trained on history
interpolates toward the nearest thing it has seen. An LLM reasoning fresh,
against general causal knowledge and the live state, is the only one of the
two that can face something genuinely novel and reason about *why* — not
pattern-match toward the past.

## 2. Judgment is not the same as constant deliberation

Continuous judgment does not mean the expensive reasoner runs on every event.
No intelligent system — biological, industrial, or otherwise surveyed on this
project — works that way. What it needs is **two different kinds of
continuity, working together, not one:**

- **Continuous awareness** — cheap, constant, watching everything, never off.
- **Deliberate reasoning** — expensive, selective, engaged only when
  awareness judges something actually warrants it.

This is not a compromise on "true AI-driven." It is what makes deliberate
reasoning possible at all without drowning it in noise. It is independently
confirmed, not invented for this document, by every domain surveyed on this
project:

- **O-RAN** — Near-RT RIC (fast, continuous, per-event) vs Non-RT RIC (slow,
  selective, policy-level), never serialised behind each other.
- **AV architecture** — Perception runs continuously at its own cadence and
  does not wait for the scene to stabilise before producing output; Planning
  only engages once Perception has judged something is there to plan for.
- **`saccade`** (jayzuccarelli, reviewed 1 Aug) — Glance (cheap, ~1Hz,
  "worth a closer look?") gates Focus (expensive, "what do I do about it?").
  Its own hard rule, stated almost as a rebuke of the mistake this document
  exists to prevent: *"No hand-coded decision rules. The only judgments are
  the two model calls."*

## 3. The test every proposal must pass — stated as a question, not a checklist

**Before proposing anything that touches what triggers reasoning, what gates
an action, or how the four layers hand off to each other, state explicitly:
which of the two tiers above does this belong to, and is the judgment in it
actually a judgment — or is it a rule wearing a different hat?**

A static entity allowlist ("ignore `sensor.*`, watch these forty entities")
is not an awareness tier. It is a human deciding in advance what is allowed
to matter — System 1 wearing a different hat, not the salience judgment an
autonomous home needs. The honest version of a "wake filter" is not a filter
at all: it is a cheap, fast, model-driven judgment running continuously,
deciding what is worth the expensive reasoner's attention, the same shape as
Glance.

This test is what a fix for the debounce mechanism (§4 below) passed
mechanically but failed on the actual requirement: correct rate-limiting
behaviour sitting on top of an unfiltered firehose does not become
event-driven judgment just because the rate-limiter is well engineered.

## 4. Decisions reached this session

```
DECISION: Replace the hand-rolled cancel-and-restart debounce in
          abode_ai_autonomy_steward.py (_schedule_reasoning_pass /
          _debounced_reason) with homeassistant.helpers.debounce.Debouncer
          (cooldown=5, immediate=True)
DATE: 2026-08-01
CHOSE BECAUSE: the hand-rolled version cancels and restarts its timer on
               every single event, requiring 5s of total house-wide silence
               to ever fire — measured at 97 events/min, median gap 0.00s,
               this cannot fire under real load. HA core's own Debouncer
               with immediate=True fires the first event of a burst
               instantly (true real-time response) and fixes the cooldown
               window at burst-start rather than extending it on
               subsequent events (guaranteed trailing pass, cannot starve)
REJECTED: raising DEBOUNCE_SECONDS (makes starvation worse, not better);
          removing the debounce entirely (reintroduces the exact
          pass-storm risk debouncing exists to prevent)
EVIDENCE CLASS: [V] — homeassistant/helpers/debounce.py read directly from
                HA core source this session
FALSIFIED IF: under real load, the trailing pass still fails to fire
              within cooldown + one event interval — not yet tested, App
              not yet modified
STATUS: necessary, NOT sufficient — see next decision
```

```
DECISION: The Debouncer fix above must not be treated as solving the wake
          problem on its own. Without a salience/awareness tier gating what
          is allowed to trigger _schedule_reasoning_pass() at all, a
          correctly-implemented Debouncer collapses to a fixed ~5s poll
          loop under this house's measured event rate (97/min, no gap
          long enough for the cooldown to represent anything but a floor)
DATE: 2026-08-01
CHOSE BECAUSE: §2/§3 above — continuous awareness and deliberate reasoning
               are two different tiers, not one tier plus a rate limiter
REJECTED: treating the Debouncer fix as closing S4 — it closes the
          mechanical half (starvation) and leaves the architectural half
          (unfiltered trigger source) exactly as open as before
EVIDENCE CLASS: [A] — reasoned from the measured event rate (Q1, 31 Jul:
                212 entities, 45% sensor domain, telemetry-dominated) and
                the cooldown value; not yet measured against a live
                Debouncer-based pass
FALSIFIED IF: once built, the trailing-pass cadence under real load is
              observed to correlate with genuinely salient events rather
              than with the fixed cooldown interval — would mean the
              concern here was overstated
STATUS: not yet built. Sharpens Q5 (31 Jul, "entity filtering is needed —
        but as a wake filter only") — Q5 said filtering was needed; this
        session's addition is that the filter itself must be a cheap
        model judgment (Glance-equivalent), not a static allowlist, or it
        is System 1 in a different position in the pipeline
```

## 5. Rejected framings — recorded so they are not re-proposed

- **A rules-engine-with-more/cleverer-triggers, at any level of
  sophistication.** No amount of trigger engineering turns a deterministic
  dispatch table into judgment. This includes a correctly-implemented
  Debouncer sitting alone on top of an unfiltered event stream (§3, §4).
- **A trained model over logged outcomes as System 2's mechanism.** Rejected
  at Q8, 31 Jul, for the reason restated in §1 — interpolation toward
  history is not reasoning about the novel.
- **A static entity allowlist as the wake filter.** Solves the debounce math,
  fails the test in §3 — it is a rule, not a judgment, however well-tuned.

## 6. Open questions this creates

**Q13.** What does the awareness tier actually look like on this hardware —
a second small resident model judging salience per event (matching
`saccade`'s Glance), a cheap non-LLM heuristic that isn't secretly a rule in
disguise, or something else? Not designed. Gated on: whether a second
resident model fits LXC 252's existing memory/VRAM budget alongside Gemma
(same open resource question already flagged for HA-RAGent's embedding
model, 1 Aug) — a measured-on-this-hardware question, not yet answered
either way.

**Q14.** Once an awareness tier exists, does it also resolve X1 (which
state changes are worth reasoning about) more directly than the
label-set-logic or named-slice approaches surveyed from ZenOS-AI — or are
those a separate mechanism for a separate stage (bounding *what the
reasoner sees* once woken, not deciding *whether to wake it*)? Not yet
distinguished.

## 7. How this document is used

Per the project instructions: before proposing anything touching reasoning,
triggers, or the four-layer architecture, state explicitly which requirement
in §1–§3 above the proposal is checked against — before any code or design
is written, not after. A proposal that does not state this check is
incomplete on its face, regardless of whether the mechanism it describes is
correct.

## 8. Supersedes

Nothing. This sits alongside `document-standard.md` — that document governs
how things are recorded; this one states what the system is for. Existing
decisions (Q1–Q12, S1–S5, the four-layer architecture itself) stand
unchanged; this document is the lens they are checked through going forward,
not a replacement for any of them.
