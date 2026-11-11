# ZenOS-AI review — fourth pass addendum

**Date:** 2026-08-01, continuation of the same session.
**Covers:** `dojotools_core.yaml` header + `zen_dojotools_filecabinet_gc`
script (~130 of 710 lines) — the GC mechanism flagged unread in the first
addendum.

## The GC mechanism itself — competent, not novel

TTL-based hide→delete lifecycle (`meta.expires_after`), a `recycle` mode
that hides a drawer and resets its expiry rather than deleting outright,
protection via `_`/`.` prefix convention plus an explicit named
allow-list, `dry_run` support that reports what would be evicted without
acting. Nothing here that isn't a reasonable design most engineers would
converge on; not flagging it as a pattern to import.

## What's actually worth reporting: verification records embedded in source

The file header carries a dated UAT block, directly in the comments, not
in a separate document:

```
# === UAT PASS — 2026-03-03 ===
# Auditor: Claude (Anthropic, Sonnet 4.6)
# HALMark: 0.9.10-draft — PASS Level 3 (Steward Safe) — 13/14 PASS, 1 KNOWN BEHAVIOR
# UAT Cases: 7/7 PASS
#   zen_dojotools_filecabinet_gc:
#     dry_run=true, stale present → would_evict populated, nothing deleted ✓
#     [... five more named cases with pass marks ...]
#
# KNOWN BEHAVIOR:
#   all_drawers references kata_entity as a sibling key in the same variables step.
#   Works correctly in all tested scenarios. Flag for review at migration time.
#
# PENDING LIVE VERIFICATION (no stale drawers available at UAT time):
#   - Actual eviction path (delete loop + filecabinet response)
#   - post_supersummary=true with evictions (supersummary chain fires)
#   - max_age_hours custom value
#   - volume_entity_id override
```

This is Document Standard Rule 1 and Rule 2 (conditions recorded, not just
results; component-tested vs. never-observed kept separate) — but
implemented by writing it into the file the behaviour lives in, not a
separate as-built that can drift out of sync with the code as it changes.
The "PENDING LIVE VERIFICATION" block is functionally identical to our own
"not covered" line, in the one place it's guaranteed to be read: right
above the code it describes, every time someone opens the file to change
it.

**This is worth taking, on its own merits, independent of anything else in
either review tonight.** Our own as-builts are separate documents (this
project's own document-standard.md exists because of exactly the failure
mode this pattern prevents — a result recorded without its conditions,
read as proven next session). A header block that states what's been
UAT-tested, what's still pending, and what known-but-unfixed behaviour
exists — living in the script/config file itself — would survive a
context switch between sessions in a way a separate document depends on
being re-read to survive.

**Not proposing this as a decision** — just flagging it as a candidate
worth you weighing against the current document-per-change convention,
since it changes *where* Rule 1/2/7 records live, not what they say.

## Scope note

Did not go further into Room Manager or Security Manager this pass —
stopped on finding something concrete rather than continuing to scan.
Both remain unread; still available if wanted.
