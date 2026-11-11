# ZenOS-AI review — third pass addendum

**Date:** 2026-08-01, continuation of the same session.
**Covers:** `dojotools_identity.yaml` (header + `zen_dojotools_identity`
mode list, ~120 of 2,799 lines) and `dojotools_postman.yaml`'s
authority-stack override/logging path (~90 of 2,275 lines). Everything
else in both files, and everything not yet mentioned across all three
notes, remains unread.

## Identity/privilege model — not a match for our constraint layer, said plainly

I went in expecting this might be comparable to `constraint_layer.py`'s
approve-once-per-action-type model, since the README implied a
"privilege gating by identity" system. It isn't the same thing. What's
actually there is a **household roster and delegation system**: who's a
household member vs. family member (nested to a capped depth), a
`link_partners` mechanism where two entities (human or AI persona) get
bidirectional delegation ACLs so one can act on the other's behalf, and a
`prompt`/`render_prompt` inspection mode. This governs *whose identity the
system is reasoning as* and *who can speak for whom* — not *whether an
action is allowed*. No action-authorization logic found in the part read.
Not carrying this forward as related to Q7 or the constraint layer; it
answers a different question than either.

**One genuinely useful piece, unrelated to what I went looking for:**
`mode: render_prompt` renders the exact assembled system prompt a live
agent would receive — all sections, as sent — on demand, for inspection.
That's a direct, built-in answer to the exact failure class the Document
Standard itself exists to prevent here (the 166 vs. 7,006-token gap,
22–23 July). Worth considering as a diagnostic capability on our own
system independent of anything else in this review — the ability to ask
"what does the model actually see right now" without inferring it from
logs after the fact.

## Authority-stack override — relevant to Q7

`dojotools_postman.yaml`'s `direct_dispatch` mode requires an explicit
`override: true` field to bypass its policy gate (quiet hours/work hours),
described in the field help as "the 'I know what I'm doing' switch" —
**and the code logs blocked attempts regardless of whether override is
set.** That's a concrete instance of a bypass mechanism that can't be used
silently: attempting to bypass is itself always recorded, whether or not
the bypass succeeds. Relevant to Q7 (should `constraint_layer.is_blocked()`
get a second independent check) — not as a design to copy outright, since
Q7 stays correctly gated behind S3/S4 per the standing sequencing, but as
a concrete example of what "redundant" can mean in practice: not always a
second check of the same kind, sometimes an always-logged bypass path
instead of a silent one.

## Not proposed

Neither finding here changes anything already decided. The render_prompt
idea is a candidate worth raising on its own merits when useful; it isn't
tied to either HA-RAGent or ZenOS-AI and doesn't need this review as its
justification.
