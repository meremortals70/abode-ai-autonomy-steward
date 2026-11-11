# HA-RAGent — source code review

**Date:** 2026-08-01 (overnight, while Jason asleep — nothing built, nothing
decided, no files touched on any hapve system)
**Source:** `github.com/youngaileaderslinz/HA-RAGent`, cloned and read
directly (`custom_components/ha_ragent/src/**/*.py`), README used only for
install/config context, per the source-of-truth rule — behaviour claims
below are from the code, not the README.
**Status:** findings only. Not a DECISION record — nothing chosen, nothing
rejected. Two candidate open items are proposed at the end for the backlog;
they are not yet numbered or accepted.

---

## What it actually does, mechanically [M — read from source]

Two separate stages, cleanly decoupled:

**1. Indexing (setup-time, not per-turn).** `DeviceExtractor.async_embed_all_exposed_devices()`
and `ToolExtractor.async_embed_all_exposed_tools()` pull every entity/tool
HA already exposes to conversation, embed *static metadata only* — friendly
name, domain, area, aliases, labels, available services — never live state
or attributes — and write the vectors to a local FAISS index on disk (or
Mongo/Chroma). This is a full collection rebuild, not incremental, and runs
outside the request path entirely.

**2. Retrieval (per-turn).** On a user utterance, `_async_embed_query()`
embeds the new text plus prior turns from the same conversation, combined
into one query vector via a logarithmic recency-decay weighted average —
not fed back through the LLM, just averaged embedding vectors, so it costs
N cheap embedding calls, not N expensive LLM calls. That single vector is
then used for two independent top-K nearest-neighbour lookups against the
pre-built indexes: `_async_retrieve_devices()` and `_async_retrieve_tools()`,
each bounded by a configured N (`CONF_NUM_DEVICES_TO_EXTRACT`,
`CONF_NUM_TOOLS_TO_EXTRACT`). Only for the retrieved candidate devices does
it then call `hass.states.get()` to attach live state — state is fetched
fresh, never embedded stale.

**3. Failsafe.** Regardless of what top-K missed, the LLM is always also
given two live tools — `search_devices`, `search_tools`
(`search_tool_api.py`) — that re-run the same embed-and-retrieve step
mid-turn on a query the model itself writes, if it decides the pre-fetched
candidates don't have what it needs. This is the part that stops "wrong
top-K" from being a silent failure mode: there's an explicit LLM-driven
widen-the-search escape hatch, not just a fixed cutoff.

**4. One thing not to copy.** Tool calls are parsed by regex out of free
text (`TOOL_REGEX_PATTERN`) rather than using native structured tool
calling. That's a compatibility choice for models without tool-call
support — it directly contradicts our own measured finding on LXC 252
(22 Jul as-built) that `finish_reason: tool_calls` with clean JSON args is
what's reliable on our hardware. Flagging this so it doesn't get carried
over by habit if any of this gets built here.

## Resource cost — not measured, flagged not assumed

The embedding backend is a *second* resident model (Ollama, an
embedding-capable model, e.g. `mxbai-embed-large`), separate from the
conversation LLM. Per this project's own operating principle — everything
pinned resident, nothing evicted for idleness, sized for this appliance —
adding this is not free: it is a second model that would need to sit
resident on Lemonade/hapve permanently alongside Gemma. Whether that fits
in the existing memory/VRAM budget on LXC 252 is a measured-on-this-hardware
question, not something to assume either way. [A] — unmeasured, not a
premise for anything yet.

---

## Mapped to hapve's two functions — kept separate, per standing rule

### Function 2 (voice — business-as-usual record queries): directly relevant

This is close to exactly what was scoped in the 28 Jul session for
`abode_tools` retrieval — a narrow, purpose-shaped tool wrapping Homebox/
Paperless search, not a generic MCP surface. HA-RAGent doesn't hand you
that tool (it embeds HA entities and HA tools, not Homebox/Paperless
records — different domain, not directly reusable code), but the *pattern*
is worth taking: pre-embed once at index-time, retrieve by relevance to the
question at query-time, and give the model a live-search fallback tool
rather than trusting top-K alone. That maps onto "when did we buy the
brushcutter" style queries more naturally than a fixed `MAX_RESULTS`
truncation would.

### Function 1 (autonomous home): mismatch, not a fit — said plainly rather than forced

The whole mechanism is **query-driven**: something is embedded because a
user asked a question, and retrieval ranks by relevance *to that question*.
`_reason()` has no question — it runs on a state-change trigger, not an
utterance. There is nothing here to embed a query from. This does **not**
answer X1 ("which state changes are worth reasoning about") or the
§1-adjacent question about whether a wide *state* snapshot itself degrades
reasoning quality independent of task-type — this project doesn't face that
problem because it never hands the model a state snapshot at all, only
retrieved-then-live-fetched candidates for a known question. Recording this
mismatch explicitly so it isn't mistakenly cited later as prior art for
Function 1's wake-filtering problem — it isn't.

---

## Candidate backlog items — not yet numbered, not yet accepted

1. Whether an embedding-based retrieval pattern (indexed once, retrieved by
   relevance, live-search fallback) is worth building into the Function 2
   voice/records retrieval tools, versus the current fixed-truncation
   approach in `abode_tools.search_entities`. Gated on the resource
   question above being answered first.
2. Whether the same pattern has anything to offer the *voice* device-control
   path specifically (narrowing which of N exposed entities go in the
   prompt for "turn on the reading lamp") — separate from Function 1, this
   is Function 2/voice-control territory, and would compete directly with
   the already-built and already-fixed `search_entities` MAX_RESULTS
   approach. Needs a real comparison, not an assumption that semantic
   retrieval is better than what's already measured and working.

Nothing here is proposed as done. Both wait for you.
