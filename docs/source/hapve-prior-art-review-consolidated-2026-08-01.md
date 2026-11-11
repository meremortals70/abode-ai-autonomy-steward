# Prior-art code review — consolidated learnings

**Date:** 2026-08-01
**Scope:** Closes out the HA-RAGent and ZenOS-AI source reviews (two
original notes + six addenda) with one consolidated summary. Supersedes
nothing — this is an index into what's already written, not a
replacement for it. Full detail and file/line sourcing lives in the eight
prior notes; this is the "read this one first" layer.

**Coverage basis:** HA-RAGent — full `custom_components` read (small
enough for complete coverage). ZenOS-AI — every `dojotools/*.yaml` header
read for stated purpose; deep source read wherever a header signaled real
architecture (11 of 33 files); the rest confirmed via header as reusing
already-catalogued patterns, not new ones. `zen_os_1.jinja` (prompt
engine) and `zen_query.jinja` (filter engine) headers/macro inventories
read; full macro bodies not all read. Plugin self-registration pattern
confirmed via Paperless-NGX. FileCabinet's write-side validation,
move/copy/relabel, and fleet mode remain unread — flagged, not guessed at.

---

## Four genuinely different answers to "how much context does the model get"

This was the single most useful thread across both repos — the same
problem (§1's state-breadth question, X1) solved four different ways by
different authors, each with a different cost profile:

1. **Embedding similarity** (HA-RAGent) — vector DB, top-K by cosine
   distance, live-search fallback tool. Requires a second resident
   embedding model. Query-driven, not event-driven — **ruled out for
   Function 1** on that mismatch alone, not on cost.
2. **Label set-logic** (ZenOS-AI HyperIndex) — deterministic AND/OR/NOT/XOR
   over a cached label index, no ML involved. Event-driven, compatible
   with Function 1's shape.
3. **Named opt-in slices** (ZenOS-AI Room Manager) — a fixed,
   human-designed taxonomy (`+topo`, `+climate`, `+security`, …), each
   fetched only if requested, zero infrastructure beyond existing tool
   calls.
4. **Curated context per action-type** (already decided here,
   `constraint_layer.py` / four-layer architecture) — the baseline this
   project already has.

**Consolidated position:** options 2 and 3 are both real candidates for
X1 when it's actually designed, and neither requires new infrastructure
the way option 1 does. This is now a design choice between two concrete,
sourced approaches rather than an open-ended one — worth a deliberate
comparison when X1 is picked up, not before.

## One directly actionable idea, unrelated to retrieval

**`prompt_length_audit()`** (`zen_os_1.jinja`) — a macro that renders
every section of the assembled system prompt independently and returns a
per-section character-length breakdown plus total, callable on demand.
This is a direct, structural answer to the exact failure this project's
own Document Standard exists to prevent (the 166 vs. 7,006-token gap,
22–23 Jul) — not a discipline of writing it down after the fact, but a
tool that answers "how big is what the model is about to see, and which
section is the cost" before it's sent. Paired with the `render_prompt`
inspection mode found in the identity module, this is the strongest
single candidate from either review to consider building here,
independent of anything else surveyed.

## Function 2 (voice/records) — validated and extended, not new

Paperless-NGX registers as a self-describing provider behind a single
broker (`Library`), auto-discovered into a registry, with an explicit
soft-failure contract (`missing/misconfigured provider → status=error,
never raises`) and a rule that **consumers never call providers
directly.** This is the same shape as the 28 Jul decision to give
`abode_tools` narrow retrieval tools rather than a generic MCP surface —
confirmed as sound by a working second implementation, and extended with
a concrete idea (self-registering providers) for whenever a second or
third record source gets added after Homebox.

## Patterns worth having on file, lower stakes, not gating anything

- **Cache-with-TTL + namespace allowlist + digest-field bounding**
  (FileCabinet's live-drawer mechanism) — a worked example for Y1/Q6 if
  a bounded "cheap read of current state" abstraction is ever needed.
- **Bypass-must-log** (Postman's `direct_dispatch` override) — relevant to
  Q7 as one concrete shape "redundant" can take: not a second identical
  check, an always-logged bypass path.
- **Embedded verification records** (the GC script's UAT block, in-source
  rather than a separate as-built) — a candidate worth weighing against
  the current per-change document convention, since it changes *where*
  Document Standard Rule 1/2/7 records live, not what they contain.
- **Event-bus dispatch with correlation IDs** (`dojotools_dispatcher.yaml`)
  — unknown-tool calls return a structured error on the event bus instead
  of hard-faulting the caller; general reliability pattern, not tied to
  either function.

## Confirmed non-matches — said plainly so they don't get re-checked later

- **Identity/privilege model** — household roster and delegation ACLs
  (who can act on whose behalf), not action-type authorization. Does not
  inform Q7 or `constraint_layer.py`.
- **HA-RAGent's whole mechanism** — query-driven, no fit for Function 1's
  event-driven `_reason()`. Only the Function 2 pattern transfers.
- **ZenOS-AI's overall system shape** — optimised for breadth/flexibility
  across many personas and a ~64K context budget on a single 16G GPU,
  the opposite trade-off from this project's stated latency-for-one-
  household target. The two extracted mechanisms above stand on their
  own merits; the system they came from is not a model to follow.

## What remains unread, named so it isn't assumed covered

FileCabinet's write-side validation/whitelist, move/copy/relabel, fleet
mode. Security Manager, Media Manager, Camera, Lights (ZenLux), Covers
(ZenShade), Spa Manager, Autovac, AlertManager, ZenZork, KungFu Loader,
Manifest broker, Scribe, AdminTools (beyond the one rollback note),
Profile/Provisioner/Labels/History, Ectoplasm, SystemTools, Office/Todo/
Calendar, Image Generator, Home Mode — all header-confirmed as
domain-specific or utility CRUD reusing catalogued patterns, not deep-read
line by line. If a specific one becomes relevant to a real backlog item
later, it gets read then, on that question — not speculatively.

## Nothing here is a decision

Every item above is a candidate, sourced and ready to be picked up when
the backlog item it touches is actually being designed (X1, Y1, Q6, Q7,
or the prompt-length-audit idea on its own). This note closes the review,
it doesn't open new work.
