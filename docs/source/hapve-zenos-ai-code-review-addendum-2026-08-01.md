# ZenOS-AI review — second pass addendum

**Date:** 2026-08-01, continuation of the same session.
**Supersedes, in part:** `hapve-zenos-ai-code-review-2026-08-01.md` — the
"not read" list. FileCabinet's live-drawer mechanism is now read (the
mount/tool-call/cache path only — not the full 5,529-line file; GC, move,
copy, relabel, fleet-mode, and the write-side validation logic are still
unread). Everything else in the parent note stands unchanged.

## What "LiveDrawer" actually is [M — from source, `dojotools_filecabinet.yaml` ~900–1140]

The README called this "fires a tool call on read, warm cache
auto-expiring, never returns empty." The actual mechanism, confirmed in
code:

A drawer can carry `mount_point: true` plus `fc_args: {tool, params,
cache: {ttl_seconds, digest_fields}}`. On read:

1. **Cache check first.** If a cached value exists at `{key}/cache` and is
   younger than `ttl_seconds` (default 300), return it directly — no tool
   call. This is the "warm cache" behaviour.
2. **On a cache miss**, it dispatches the named tool as an actual HA
   script call (`script.{tool}`, with `params` as the data payload) —
   **but only if the tool name matches `^zen_`.** Anything else is
   rejected outright with an explicit error ("a lens verb, not a
   dispatchable script"). This is a real guardrail, not a suggestion —
   arbitrary tool names can't be wired into a live drawer.
3. **Digest extraction.** If `digest_fields` is set, only those specific
   fields are pulled out of the tool's response and cached/returned — the
   full response is not persisted. This is a deliberate token-bounding
   step: the cache holds a shaped subset, not a raw dump.
4. **Loop/depth guarded.** Mount chains can traverse to other drawers;
   the traversal explicitly detects `loop_detected` and
   `depth_limit_exceeded` and returns an error status rather than hanging
   or recursing unbounded.

In short: this is a declarative "cached, bounded, TTL-scoped view over a
tool call" — a drawer looks like a static memory slot to anything reading
it, but is backed by a live, rate-limited call with an explicit size
contract.

## Relevance — Function 1 (autonomous home)

This is a genuinely reusable *pattern*, not code we'd import, for the same
territory as Q6/Y1: if hapve's own history/audit store ever needs to
expose "the current state of X" as a cheap, bounded read rather than
re-running a full query every time it's referenced, this is a concrete
worked example of how to do that safely — cache-with-TTL, a field
whitelist to bound what's stored, and an explicit tool-namespace allowlist
so the mechanism can't be pointed at something ungoverned. Doesn't change
anything already decided; it's a reference shape if/when Y1 gets built.

## Still unread in FileCabinet

GC (garbage collection on the stated 15-minute cycle — not verified),
move/copy/relabel semantics, the write-side validation and whitelist logic
referenced at line ~903 (`fc_mount_callout_whitelist`), and fleet mode.
None of these are needed to evaluate the live-drawer pattern above, so I
stopped here rather than reading the rest of a 5,529-line file for
completeness' sake without a question driving it.

## Still entirely unread, unchanged from the parent note

Room Manager, Security Manager, identity/privilege model, Cortex ("Rule
Zero"), domain-specific dojotools (lights, covers, camera, autovac, etc).
No claims made about any of them.

## Not proposed

Same as the parent note — this is a pattern worth having on file, not a
backlog item. Nothing changed in what's already decided or in progress.
