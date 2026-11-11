# Architecture Thesis — addendum 2: levels formalized, the Vigil bus

**Date:** 2026-08-01, continuation of the same session as
`hapve-architecture-thesis-addendum-vigil-2026-08-01.md` and
`hapve-architecture-five-layer-lock-2026-08-01.md`.

**Supersedes, precisely:** the phrase *"five layers, locked"* in
`hapve-architecture-five-layer-lock-2026-08-01.md` — corrected below to the
rank/component distinction that document's own diagram already showed
correctly but its headline phrase didn't capture. Nothing else in either
prior document changes; this extends them.

---

## 1. CORRECTION — four ranks, five components, not "five layers"

```
CORRECTION: "five layers, locked" (five-layer-lock doc, same session)
            overstated the case. The architecture is FOUR RANKS in the
            data-flow (who feeds whom) and FIVE COMPONENTS (five
            distinct named, built-or-to-build things)
DATE: 2026-08-01
WHY THIS MATTERS: Reflex and Vigil sit at the same rank - both consume
            Senses directly, neither feeds the other. Calling this "five
            layers" invites reading them as stacked in sequence, which
            is the wrong mental model and was already flagged as a risk
            when first raised
LEVEL NUMBERING, FORMALIZED (bottom-up, per architect's framing):
  Level 0 - Senses     (outside the middleware boundary entirely -
                        supplied by existing applications, HA/Frigate,
                        not ours to build or claim)
  Level 1 - Reflex + Vigil (same rank, both inside the middleware
                        boundary, both consume Level 0 directly)
  Level 2 - Steward
  Level 3 - the Ward
EVIDENCE CLASS: [A] - architect correction, this session
```

## 2. DECISION — domains cross-cut Reflex and Vigil, owned by neither alone

```
DECISION: The six domains (safety, security, comfort, pattern deviation,
          resource stewardship, household operations) are not internal
          structure belonging to Vigil alone. They span Reflex and
          Vigil - each domain has a Reflex slice (discrete, unambiguous
          cases, no judgment needed) and a Vigil slice (ambiguous,
          context-dependent cases, judgment required)
DATE: 2026-08-01
CHOSE BECAUSE: the appliance-failure worked example breaks a
          Vigil-owns-all-domains framing directly - a leak sensor
          triggering (safety domain) is handled entirely by Reflex
          today, no judgment involved; a stopped wash cycle needing
          context (pattern-deviation domain) is Vigil's job. Same
          domain, different layer, because what varies is ambiguity,
          not subject matter
REJECTED: domains as Vigil-internal-only structure - doesn't survive the
          worked example above
NOT YET DECIDED: for each domain, exactly where the Reflex/Vigil line
          sits. Likely uneven across domains (Safety may be mostly
          Reflex already with a thin Vigil slice; Household Operations
          may be almost entirely Vigil's, or may turn out to be nearly
          all Reflex once actually examined - the domain flagged as
          most at risk of being Reflex in disguise)
NOT CHANGED, FLAGGED EXPLICITLY: Steward stays domain-agnostic once
          woken - synthesis across domains remains System 2's job, per
          the first Vigil addendum, unchanged by this decision. The
          Ward stays domain-blind - gates by service/target/type,
          not by which domain proposed the action
EVIDENCE CLASS: [A] - reasoned through one worked example, not tested
          against a real device fault or a range of domains
```

## 3. DECISION — the AI Engine is a shared substrate, not a rank

```
DECISION: The AI Engine (LXC 252, Lemonade, Gemma-4-26B, GPU engine) is
          drawn and treated as infrastructure supplied to the
          middleware - same treatment as Senses - not a fifth rank in
          the Senses -> Vigil -> Steward -> Ward data flow
DATE: 2026-08-01
CHOSE BECAUSE: Vigil and Steward both call it; Reflex and the Ward
          correctly never do (Reflex is pure determinism, the Ward is a
          deterministic gate) - drawing it as a rank would misstate
          which components actually need it
HARDWARE CONSTRAINT MADE EXPLICIT ON THE DIAGRAM, NOT JUST IN
          DOCUMENTATION: the GPU engine is the shared resource Vigil and
          Steward compete for; the NPU engine is reserved for Frigate
          GenAI (still gated on Frigate 0.18 GA) and is not available to
          either. This is a real, already-established hardware fact
          (current-state-correction doc, 30 Jul) - restated here because
          it's about to become load-bearing the moment Vigil's domain
          calls are sized
EVIDENCE CLASS: [M] for the hardware allocation (as-built, 26/30 Jul);
          [A] for treating it as non-rank infrastructure (architect
          decision, this session)
```

## 4. DECISION — domains are independent parallel functions, not OS containers

```
DECISION: "Separating functions which are not dependent on each other"
          (architect's own phrasing) means logical/functional
          independence between the six domains - each with its own
          scope, own trigger conditions, own cost profile - not OS-level
          containerization (separate LXCs/processes per domain)
DATE: 2026-08-01
CHOSE BECAUSE: (1) checked directly against ZenOS-AI's actual scheduler
          pattern (dojotools_scheduler.yaml, read from source) - its
          "bounded slice per component" isolation (own
          trigger_subscriptions, own scoped context) is logical
          isolation within one HA-native runtime, not separate OS
          containers; there was never OS-level isolation in the source
          this claim was checked against; (2) this project's own
          single-purpose-appliance principle explicitly rejects
          multi-tenant assumptions - "concurrency sized for one
          household, not many users" - and OS containers exist
          specifically to isolate tenants or enable independent scaling,
          neither of which applies on hapve; (3) every domain's Vigil
          call ultimately queues on the same single shared GPU-backed AI
          Engine regardless of what process it's issued from -
          containerizing the callers doesn't parallelize the actual
          constraint; (4) matches existing project convention -
          abode_tools is already one deployed component serving four
          distinct tools, not four separate processes
REJECTED: separate LXC/OS-level containers per domain
EVIDENCE CLASS: [V] for the ZenOS-AI claim (source read directly, this
          session); [A] for the rest, reasoned against already-decided
          project principles, not measured
```

## 5. Domains likely have asymmetric resource cost — flagged, not measured

```
NOTED, NOT DECIDED: independent functions aren't necessarily equal cost.
          Safety plausibly wants the cheapest, fastest possible check
          (latency matters most for danger). Pattern Deviation plausibly
          needs more context per call (judging deviation requires
          comparing against a baseline/history). Both are guesses,
          explicitly marked as such on the diagram - not measured, not
          to be treated as settled sizing
DATE: 2026-08-01
SOURCE: architect's own observation ("one function needs more physical
          grunt to do its job"), this session
```

## 6. DECISION — the Vigil bus / access controller, positioned but not designed

```
DECISION: A bus/access-controller sits above the six domain functions,
          inside Vigil (Level 1), arbitrating their shared access to the
          AI Engine. It is deterministic, not a judgment component - the
          same category as the Ward, not the same category as a domain
DATE: 2026-08-01
CHOSE BECAUSE: §3's test (thesis) asks whether a component is genuine
          judgment or a rule in disguise - arbitrating whose GPU call
          goes first isn't a judgment about the house at all, it's
          resource arbitration, so it doesn't need to pass Vigil's own
          bar. Once domains are accepted as independent and parallel
          (§4 above), competing for one shared constrained resource,
          SOME arbitration is a structural necessity, not optional -
          the only real question was whether to name and position it
          now or leave it implicit
DRAWS ON: ZenOS-AI's scheduler (read from source) - priority-based
          load-shedding under queue pressure (shed_ambient_at /
          shed_keeper_at) and a fast-path tier that bypasses delay
          entirely for the highest-priority class (pipeline_tier:
          super). Named as the shape to design against, not adopted as
          a ready-made scheme
EXPLICITLY NOT DONE HERE, AND WHY: no QCI-style priority classes were
          defined. Designing them now would mean scheduling against
          guessed-at domain costs (§5) rather than real ones - the same
          mistake S2/S4 already made once each this project (fixing a
          mechanism before observing what it actually needs to handle).
          Blocked on: real per-domain call cost and frequency, which
          doesn't exist until Q13's implementation question is answered
          and at least one domain is actually built
EVIDENCE CLASS: [A] - reasoned from §3's test plus the ZenOS-AI
          precedent; not built, not measured
```

## 7. Process note — diagram errors, three times, worth naming as a pattern

Three diagram errors this session, all caught by the architect, none by
any check on this end before presenting:

1. Two diagrams drew Vigil above Steward in the vertical stack —
   backwards against the locked bottom-up level order (§1).
2. The corrected full-stack diagram's Level 0-3 text labels were
   positioned one band too high each — "LEVEL 3" sat next to the
   actuation output box instead of the Ward, leaving Reflex/Vigil's
   actual band unlabeled entirely, the opposite of what the labels were
   added to show. Found and fixed after this document was first written.

Different failure shapes (whole-diagram inversion vs. label/band
misalignment) but the same root cause both times: box and label
coordinates were not checked against each other before presenting.
Recorded here not as a technical decision but as a known failure mode:
before presenting any further diagram of this architecture, verify each
label's y-position falls inside its intended box or band's y-range, and
state the intended level order explicitly, first — both checks were
skipped every time and are the direct cause of all three errors.

## 8. Diagrams superseded / current

**Corrected in review, same session:** `hapve-full-stack-with-ai-engine.svg`
and `hapve-levels-diagram.svg` were two near-identical files — the second
was the first with Level 0-3 boundary lines added on top, so the first was
a strict subset of the second and redundant as a separate "current" file
the moment the second existed. Consolidated to one canonical name rather
than left as two files claiming current status.

- `hapve-full-stack-diagram.svg` — **current, canonical.** Correct level
  order, includes the AI Engine as non-rank infrastructure (§3 above) and
  the Level 0-3 boundary lines. Supersedes both
  `hapve-full-stack-with-ai-engine.svg` and `hapve-levels-diagram.svg`,
  which no longer exist as separate files.
- `hapve-vigil-domains-parallel.svg` — **superseded**, Vigil drawn above
  Steward (the error in §7)
- `hapve-vigil-domains-parallel-v2.svg` — current, corrected order
  (Steward above, Vigil/bus/domains below), includes the Vigil bus (§6)

## 9. Open questions, updated

**Q13, narrowed further.** Still the implementation question (separate
resident models vs. one model with domain-routed prompts, per the first
addendum) - now also explicitly the blocker for §6's Vigil bus design.
Nothing about scheduling can be designed until at least one domain's real
call cost exists to schedule against.

**Q16, new.** Where does the Reflex/Vigil line actually sit, per domain?
Flagged in §2 as "likely uneven across domains" but not examined for any
domain except the one worked example (appliance failure, pattern
deviation). Not designed. A natural next step once Q13 is picked up -
probably needs answering domain-by-domain rather than all at once, given
§2's own finding that the split may not look the same in each domain.

## 10. Supersedes

Corrects the headline phrase of `hapve-architecture-five-layer-lock-2026-08-01.md`
(§1 above) — that document's own diagram and topology description stand
unchanged. Extends `hapve-architecture-thesis-addendum-vigil-2026-08-01.md`
— nothing in it is contradicted, §2 above narrows how domains relate to
Vigil specifically (cross-cutting Reflex too, not Vigil-owned), which
wasn't yet decided when that document was written.
