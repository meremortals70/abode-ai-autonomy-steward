# ZenOS-AI ("Friday's Party") — source code review

**Date:** 2026-08-01, same session as the HA-RAGent review above.
**Source:** `github.com/nathan-curtis/zenos-ai`, cloned and read directly.
README used for orientation only (project structure map, persona-name
glossary); behaviour claims below are sourced to the actual YAML
scripts/Jinja templates, file and line-referenced.
**Status:** findings only, no decision.

## Scale — and what was and wasn't read [stated honestly, per doc standard]

This is not comparable in size to HA-RAGent. `packages/zenos_ai/dojotools/`
alone is **72,754 lines** across 33 YAML files (1,066 commits total). Full
read-through in one session is not realistic and I'm not going to claim
one. **What was actually read:**

- `dojotools_index.yaml` — the core query/retrieval engine ("HyperIndex" /
  "ZQ-1"), ~350 of 2,966 lines, covering the compact-index build, staleness
  check, and set-logic/filter query path.
- `dojotools_summarizers.yaml` — ~250 of 1,895 lines, covering how the
  per-component summarizer resolves its own scoped context before calling
  the LLM.
- `dojotools_scheduler.yaml` — ~100 of 578 lines, covering trigger-
  subscription dispatch and load-shedding.

**Not read, and therefore no behavioural claim is made about them:**
FileCabinet itself (5,529 lines — the actual memory/drawer read-write
mechanics), Room Manager, Security Manager, identity/privilege model,
Cortex ("Rule Zero"), or any of the domain-specific dojotools (lights,
covers, camera, autovac, etc). The README's framing of these (Flynn,
Monastery, personas) is marketing language over an unread implementation —
I'm reporting it as unverified description, not fact.

---

## What the parts I read actually do [M — from source]

**HyperIndex (`dojotools_index.yaml`) is label-based, not embedding-based.**
This is the single biggest architectural difference from HA-RAGent. There
is no vector database and no semantic similarity anywhere in this file. It
builds a "compact index" — every HA label in use, with entity counts —
cached in a drawer and rebuilt only when stale (>600s old, checked at
query time, not on a timer). Queries then do deterministic set logic over
that index: `label_1`/`label_2` combined with `AND | OR | NOT | XOR`,
narrowed further by a `filter_json` block (domain, state, state
thresholds), with an optional "hypergraph" output mode (nodes/edges/
adjacency) for reasoning about relationships rather than flat lists. Labels
are human-assigned in HA, same as ours — this is retrieval by a curated
taxonomy Jason defines, not by what an embedding model thinks is similar.

**The summarizer pipeline is scoped per-component, not global.**
`zen_dojotools_ninja_summarizer` reads exactly one Kung Fu Component's own
drawer (its `index_call`, `trigger_subscriptions`, `drift_threshold`,
`staleness_minutes`), runs *that* component's own HyperIndex query to
build its context, and only then calls `ai_task.generate_data` — same
mechanism §3/Q8 already settled on for us. It is explicitly not one
service reasoning over the whole house at once; each component (security,
water, energy, hot tub) gets its own bounded slice.

**Scheduling is trigger-subscription driven, with real load-shedding.**
`dojotools_scheduler.yaml` dispatches each component only when the fired
trigger is in that component's own declared `trigger_subscriptions` list
— no hardcoded dispatch table. Under queue pressure it sheds lower-priority
("ambient") components first via a configured threshold
(`shed_ambient_at`/`shed_keeper_at`), and a `pipeline_tier: super` class
bypasses delay entirely. This is a real answer to "what happens when more
wants to run than can run at once" — something neither of our closed
defects (S3/S4) has needed to answer yet, but will once more than one
reasoning source exists.

---

## Mapped to hapve's two functions

### Function 1 (autonomous home) — more directly relevant than HA-RAGent was

This is the closer prior art of the two repos reviewed tonight, and for a
specific reason: HyperIndex's label-based retrieval is a **non-embedding
answer to the same problem X1 is trying to solve** — narrowing which
entities/state matter to a given reasoning pass, using a curated taxonomy
rather than a full dump or a semantic guess. That's a genuinely different
mechanism from anything already decided here, and unlike HA-RAGent it
*is* event-driven (trigger-subscription per component) rather than
question-driven, so the query-vs-event mismatch that ruled out HA-RAGent
for Function 1 doesn't apply here.

**Caution, stated plainly, not glossed over:** this is unverified as
*working* — I read the dispatch and context-scoping logic, not evidence
that it produces correct decisions in a running house. The `drift_threshold`
/ `emission_cooldown_minutes` mechanism resembles exactly the shape of
problem our own S3/S4 defect was (debounce logic that can starve a
component of ever running) — I have no evidence either way whether this
project has the same bug or has actually solved it. Worth comparing once
S3/S4 are fixed here, not worth trusting on the strength of reading the
code once.

### Function 2 (voice/records) — plugins exist for exactly this

`plugins/paperless_ngx/`, `plugins/firefly_iii/`, `plugins/grocy/` are
working examples (per the README's own changelog, not verified in code
this session) of narrow, purpose-shaped integrations against household
record systems, exposed to the conversation agent as tools — structurally
the same shape as the `find_item`/Homebox tool already scoped 28 Jul, just
built out further and for different backends (finance, inventory,
documents) than ours.

---

## A difference from our own stated principles, worth naming rather than resolving

The README's own hardware guidance targets "~64K context... single 16G
GPU" and a many-persona, many-integration system explicitly optimised for
flexibility and breadth. That's the opposite trade-off from this project's
stated optimisation target — latency for one household, not throughput or
general-purpose flexibility. Not a reason to dismiss the ideas (HyperIndex
and the scoped-summarizer pattern are still architecturally sound on their
own terms), but a reason not to import this project's overall shape
wholesale — the parts worth taking are the two mechanisms above, not the
system.

## Not proposed

Nothing here is a candidate backlog item yet — unlike the HA-RAGent note,
which proposed two. This needs your read before it's turned into anything
concrete, given how much of the source is still unread.
