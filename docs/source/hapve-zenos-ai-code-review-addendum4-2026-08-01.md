# ZenOS-AI review — fifth pass addendum

**Date:** 2026-08-01, continuation of the same session.
**Covers:** `dojotools_room_manager.yaml`, the `context_slices` mechanism
(~500 of 3,778 lines — the flag-parsing and per-slice fetch blocks; area
topology/registration logic and the rest of the file still unread).

## A third distinct retrieval mechanism — opt-in named slices

This makes three genuinely different answers, across the two repos
reviewed tonight, to "how much context does the model get":
HA-RAGent = embedding similarity, HyperIndex = label set-logic, and now
Room Manager = **explicit named categories, requested by the caller.**

`zen_dojotools_room_manager mode=get area={id}` takes a `context_slices`
string like `+topo,+light,+climate,+covers,+media` — a fixed taxonomy of
about a dozen categories (topology, light, climate, covers, media,
inventory, chores, tasks, calendar, security, wiki, tickets, catalog).
**Each slice is fetched only if its flag is present**, confirmed in code:
every slice sits behind a `choose`/`condition: template` gate on `_show_X`
before any backend call is made (e.g. the chores slice at line ~850 only
calls `zen_dojotools_inventory` if `_show_chores` is true). An unrequested
slice costs nothing — no call, no data, no tokens.

This is a materially different trade-off from the other two mechanisms:

- **vs. embeddings (HA-RAGent):** no vector DB, no similarity guess. The
  categories are a closed, human-designed taxonomy, not an open-ended
  semantic space. Whoever calls this (the model, or a wrapper on its
  behalf) has to know which named category it wants — reliable when the
  taxonomy fits the domain, brittle if a real need doesn't map cleanly to
  one of the dozen flags.
- **vs. label set-logic (HyperIndex):** HyperIndex answers "which
  entities match this label combination"; this answers "which *kinds* of
  information about this one area do I want." Different axis — HyperIndex
  slices across entities, this slices across information categories for
  a location already known.

## Relevance — Function 1, directly, on the §1/X1 question

This is a third worked answer to the same question X1 is solving, and
unlike HA-RAGent it doesn't require an embedding model as a second
resident process — the cost is just conditional branches and existing
tool calls, already running on the LLM already in use. If a taxonomy of
"kinds of context relevant to a state-change reasoning pass" fits our own
domains reasonably (e.g. `+security`, `+climate`, `+presence`, `+media`),
this is a lower-infrastructure-cost pattern than semantic retrieval for
narrowing what `_reason()` sees, worth weighing against HyperIndex's
label-based approach once X1 is actually being designed rather than
surveyed.

## Not proposed

Same caveat as every other finding tonight: this is a pattern on file, not
a chosen approach. Three real options now exist in the survey (embeddings,
labels, named slices) for the same problem; picking between them is a
design decision for when X1 is actually built, not something to resolve
by reading more prior art.

## Scope note

Area topology/registration itself, and everything past line ~1230 (media,
security, wiki, tickets, catalog slice implementations, and the rest of
the 3,778-line file), remain unread.
