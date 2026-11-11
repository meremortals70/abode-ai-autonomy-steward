# Handover — architecture session, 1 August 2026

**Supersedes:** no prior document. Companion to, not a replacement for,
the five documents this session produced. This is the fast path in; the
five documents are the actual record.

**Why this exists:** this session was itself a direct response to the
problem it also solved — Jason: *"this is the same with every new chat
session... why I cannot trust you to do the job without my constant
intervention."* The fix wasn't just writing down decisions (the project
already does that) — it was writing down the standing *thesis* those
decisions get checked against, so a future session has something to check
proposals against before proposing, not just a list of what was already
decided. This handover exists so that thesis and everything built on it
today is findable in one place, in the right order.

---

## 1. Read in this order — later documents correct earlier ones

1. `hapve-architecture-thesis-2026-08-01.md` — the core thesis. §1-§3
   define what an autonomous home is and the test every proposal touching
   reasoning/triggers/architecture must be checked against, stated
   explicitly, every session. This is the document named directly in the
   project instructions now.
2. `hapve-architecture-thesis-addendum-vigil-2026-08-01.md` — layer
   naming (Senses, Reflex, Vigil, Steward, the Ward), the six domains,
   the pattern-deviation reframe.
3. `hapve-architecture-five-layer-lock-2026-08-01.md` — **read with
   caution, its headline phrase is wrong.** "Five layers, locked" is
   corrected by document 4 to "five ranks, six components." The topology
   description and diagram concept in this document are still valid; the
   phrase in its title is not.
4. `hapve-architecture-thesis-addendum2-vigil-bus-2026-08-01.md` — the
   rank/component correction, Level 4 (HA service calls), domains
   confirmed to cross-cut Reflex too (not Vigil-owned), the Vigil bus,
   and a logged pattern of diagram-construction errors worth reading
   before producing any further diagram of this architecture.
5. `hapve-architecture-thesis-addendum3-q18-automation-authoring-2026-08-01.md`
   — Q18, findings from reading two external repos' actual source
   (`Tara Assistant`, `ai_automation_suggester`), including one
   correction of a wrong claim made earlier in the same session, stated
   plainly rather than replaced quietly.

Two current diagrams, referenced across documents 3-5:
`hapve-full-stack-diagram.png` (the whole architecture, Level 0-4) and
`hapve-vigil-domains-parallel-v2.png` (Vigil's six domains, the bus, and
Reflex's own domain slice, side by side).

## 2. What's locked as of today

- **Five ranks, six components:** Senses (0) -> Reflex + Vigil, same
  rank (1) -> Steward (2) -> the Ward (3) -> HA service calls (4).
  Senses and HA service calls both sit outside the middleware boundary,
  symmetric - HA's, not ours.
- **Domains (six) cross-cut Reflex and Vigil**, not owned by either alone
  - each domain has a discrete/unambiguous slice (Reflex's job, no
  judgment) and an ambiguous/context-dependent slice (Vigil's job).
  Domain 4 is "pattern deviation" (residents and devices both), reframed
  from "wellbeing/routine" during the appliance-failure worked example.
- **The Vigil bus** is positioned (arbitrates domain access to the
  shared AI Engine, deterministic like the Ward, not a judgment
  component) but not designed - blocked on real per-domain call cost,
  which doesn't exist until at least one domain is built.
- **Existing Reflex automations already sort into the six domains**,
  just not formally tagged that way yet - a concrete, cheap first step
  on Q16 whenever it's picked up.

## 3. Open questions, consolidated (scattered across documents 2-5 individually)

**Q13.** Vigil's implementation - separate resident models per domain vs.
one model with domain-routed prompts. Gated on LXC 252's memory/VRAM
budget, unmeasured. Also now the blocker for the Vigil bus's actual
design (no real call costs to schedule against yet).

**Q15.** Where domain 4's baselines (a resident's routine, a device's
normal cycle time) actually live - this is the autonomous home's
*operational* memory, connects to Y1 (the still-undesigned audit/history
store per backlog v3's own critical path).

**Q16.** Where the Reflex/Vigil line sits, per domain - likely uneven,
only examined for one worked example (appliance failure) so far. First
concrete step identified: audit existing automations by domain.

**Q18.** Whether to build an automation-authoring function at all, and
if so, whether it draws on `ai_automation_suggester`'s prompt-budget and
parsing methods, Tara's statistical pre-filter method, both, or neither.
Seven specific reusable techniques identified from source, none adopted.
Worth noting explicitly: #1 and #3 in that document suggest this may not
be a new pattern to design - it may be the same cheap-filter/expensive-
judgment shape already locked for Vigil/Steward, applied to a different
timescale. Not confirmed, flagged for whenever this is picked up.

## 4. A process lesson worth carrying forward on its own

Three diagram errors this session (documented in full in document 4,
§7/§11) - two whole-diagram inversions, one label/band misalignment, one
box overlapping another box - all from the same root cause: coordinates
not checked against each other before presenting. The fix stated there
holds for any future diagram of this architecture: verify each label and
box falls where it's meant to, and state the intended layout explicitly,
before presenting it.

## 5. Next action

None of Q13/Q15/Q16/Q18 is picked up yet - all four require a decision
on which to tackle first, not a default next step. Whoever opens the
next session on this thread should read documents 1-5 in order (§1
above) before proposing anything touching reasoning, triggers, or the
architecture, per the thesis's own §7 - and should state which of Q13/
Q15/Q16/Q18 is being addressed, if any, before building toward it.
