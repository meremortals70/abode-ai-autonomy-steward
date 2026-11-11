# Architecture Thesis — addendum: layer naming and the Vigil tier

**Date:** 2026-08-01, same session as the parent thesis.
**Supersedes, in part:** `hapve-architecture-thesis-2026-08-01.md` §6 — Q13
and Q14 are not closed, but this addendum narrows Q13 substantially: the
awareness tier now has a name, a proposed internal shape (domain-scoped,
multi-agent), and a first domain list. What remains open in Q13 is
implementation (§4 below), not concept or shape. Nothing else in the parent
document changes.

---

## 1. DECISION — the five layers are named, not just numbered

```
DECISION: Formal names for all five architectural layers, System 0/1/2
          numbering retained (Figure Helix citation preserved)
DATE: 2026-08-01
NAMES:
  System 0            -> Senses   (perception substrate - Frigate, HA
                                    sensors; external, unowned, nothing
                                    to build)
  System 1             -> Reflex   (fast deterministic HA automations;
                                    name deliberately reused from Eden's
                                    own deterministic tier, jayzuccarelli,
                                    reviewed 1 Aug - same job, same term)
  new tier, this addendum -> Vigil (domain-scoped salience/awareness
                                    tier - decides what wakes Steward;
                                    see §2-3 below; not yet built)
  System 2             -> Steward  (formalizes the App's existing name,
                                    ai_autonomy_steward - no change)
  constraint layer      -> the Ward (independent gate on every proposed
                                    action before execution; enforces
                                    the constitution the charter defines)
CHOSE BECAUSE: a named, undefined layer is easier to accidentally build
               as a rule later without noticing - the same failure mode
               this project's own Document Standard exists to prevent
               for requirements generally, applied here to naming
REJECTED: "Sentinel" for the new tier - name is poisoned in this
          project's history (HGA/Sentinel, rejected twice on separate
          grounds, 30 Jul)
NOT CHANGED: no file, class, or repo name changes as a result of this -
             constraint_layer.py, ai_autonomy_steward, etc. stay exactly
             as they are unless separately decided
EVIDENCE CLASS: [A] - architect approval, this session
```

## 2. DECISION — Vigil is domain-scoped and multi-agent, not one generalist judge

```
DECISION: The awareness/salience tier (Vigil) is structured as several
          narrow, domain-scoped judgments, not one generalist salience
          model evaluating every event through a single lens
DATE: 2026-08-01
CHOSE BECAUSE: (1) the corrected HA-blog finding (31 Jul) found the
               actual failure in HA's own rejected multi-task-agent
               experiment was TASK-type diversity in one agent, not
               state-input breadth - a single judge holding "is this
               dangerous," "is this wasteful," "is this suspicious" all
               in one prompt is closer to that rejected shape than
               several narrow domain judges would be; (2) ZenOS-AI's
               scheduler (read from source, 1 Aug) dispatches each
               component only against its own declared
               trigger_subscriptions, explicitly not one service
               reasoning over the whole house; (3) O-RAN's Near-RT RIC
               hosts multiple narrow xApps, not one generalist fast
               agent
REJECTED: one generalist Vigil judgment evaluating all events against
          all domains at once - risks exactly the task-diversity
          confusion HA's own experiment found, and doesn't match any of
          the three precedents above
NOT DECIDED HERE: whether "domain-scoped" means separate resident
          models, or one cheap resident model served with N
          domain-scoped prompts (a routing question, not a multiply-
          the-VRAM-budget question) - this is Q13's remaining open
          half, see §4
EVIDENCE CLASS: [A] - reasoned from three independent sources already in
          project knowledge, not measured; Vigil does not exist yet
FALSIFIED IF: once built, domain-scoped judgments are observed to miss
          cross-domain situations a single generalist pass would have
          caught (e.g. a safety-adjacent comfort issue that no single
          domain lens flags alone) at a rate that outweighs the
          task-diversity risk being guarded against here
```

## 3. Domains — six, one reframed this session

```
DECISION: Domain 4 is "pattern deviation" (covers both residents and
          devices), not "wellbeing/routine" (residents only)
DATE: 2026-08-01
CHOSE BECAUSE: the appliance-failure test case (a stopped washing
               machine, an oven not reaching temperature) required the
               identical judgment shape as a resident deviating from
               their normal pattern - noticing deviation from an
               established baseline, then judging whether the deviation
               is worth surfacing given context. Forcing appliance
               faults into "household operations" instead would have
               repeated the "domain most at risk of being System 1 with
               extra steps" problem flagged when operations was first
               proposed
REJECTED: a seventh domain for appliance/device faults specifically -
          the judgment mechanism is the same as domain 4's, only the
          subject differs
EVIDENCE CLASS: [A] - reasoned through a single worked example this
          session, not tested against a real device fault
```

Domains, as they stand now:

1. **Safety** - fire/smoke, gas, water leak/flood, falls, structural
2. **Security** - intrusion, unrecognized presence lingering, unsecured entries
3. **Comfort** - temperature, air quality, light, noise
4. **Pattern deviation** *(reframed this session)* - a resident or a device
   deviating from its established baseline, where the deviation's
   significance depends on context a fixed threshold can't resolve
5. **Resource stewardship** - energy/water waste, cost
6. **Household operations** - anticipating routine needs; still flagged as
   the domain most at risk of being Reflex in disguise, watch closely
   when this one is actually designed

## 4. The Reflex/Vigil boundary - a worked example, not yet a rule

Established via the appliance-failure discussion, worth keeping as the
reference case when Vigil is actually designed:

- **Reflex's job:** discrete, unambiguous state transitions with a
  known-correct response - a leak sensor triggering, smoke detected, a
  freezer door left open. No reasoning needed, shouldn't wait on Vigil at
  all. Already how System 1 works today; unchanged.
- **Vigil's job:** ambiguous context a state check can't resolve on its
  own - a stopped wash cycle could be deliberate (paused, forgotten,
  resident went out) or a real fault, and the answer depends on context
  (six hours stopped in a warm room vs. twenty minutes) a hard-coded
  threshold can't judge. This is the shape of problem domain-scoped
  judgment exists for; a rule can't do it, Vigil's whole premise is that
  it can.

## 5. Open questions

**Q13, narrowed.** Concept and domain shape are decided (§2, §3). What
remains open: the actual implementation on this hardware - separate
resident models per domain vs. one cheap resident model routed across
domain-scoped prompts - gated on the same LXC 252 memory/VRAM budget
question already flagged for HA-RAGent's embedding model (1 Aug),
unmeasured either way.

**Q15, new.** Where do the baselines domain 4 (pattern deviation) judges
against actually come from, and where do they live? A resident's "usually
up by 7" and a washing machine's "cycle normally runs 52 minutes" are both
learned or configured facts that need to persist somewhere and be
comparable against live state. This is squarely the autonomous home's
*operational memory* - per the two-function split, a learned fact that
changes how a judgment behaves, never a document fact - and connects
directly to Y1 (the audit/history store, still not designed, per backlog
v3's critical path: "Memory is the larger prize but it compounds the
payload problem, and it should not be designed before a pass has been
watched"). Not designed here. Flagged so Y1, when it's picked up, is
understood to also be Vigil's dependency, not only Steward's.

## 6. Supersedes

Extends `hapve-architecture-thesis-2026-08-01.md` §6 (Q13/Q14) as
described above. Nothing else in the parent document changes.
