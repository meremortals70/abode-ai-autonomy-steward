# Architecture Thesis — addendum 3: Q18, automation-authoring function

**Date:** 2026-08-01, continuation of the same session.

**Corrects, explicitly, before being recorded anywhere else:** the prior
message in this session characterized Tara Assistant as "AI-driven
pattern-mining and automation-authoring." That was wrong, said plainly
rather than quietly replaced — it was asserted from the as-built doc's
description, not from reading the source. Read directly this session:
Tara's pattern-to-automation pipeline (`app/patterns/detector.py`,
`suggestions.py`) contains no LLM call anywhere - grepped the entire
`patterns/` module for any provider/LLM reference, none found. It is
deterministic statistics (occurrence counts, `statistics.stdev()` against
a time window) and template-based YAML generation. Tara's LLM powers a
separate conversational-agent function, not this pipeline.

**Source for everything below: [V] - read directly from
`github.com/TaraHome/taraassistant-public` and
`github.com/ITSpecialist111/ai_automation_suggester`, cloned and read this
session, not from either project's README or marketing description.**

---

## Q18 — should our middleware include an automation-authoring function, and what should it draw on

```
QUESTION: should the middleware include a function that uses the AI
          Engine to propose new Reflex automations across the six
          domains, distinct from Vigil (live-event judgment) and
          Steward (live-event reasoning)?
STATUS: open, not decided
WHY IT'S A DIFFERENT KIND OF FUNCTION, NOT A VARIANT OF VIGIL/STEWARD:
          operates on history, offline/periodic, not on a live event in
          real time. Its output is a new standing automation, not an
          action on the house. Checked against thesis §3: proposing
          which patterns are worth formalizing into a rule is genuine
          judgment (does this generalize safely, is it worth the
          resident's attention), not disguised rule-following, so it
          passes the bar for legitimate autonomous-home work
NOT YET DECIDED: build fresh, fork one of the two repos below, or draw
          methods from both without adopting either wholesale
```

## What each repo's actual mechanism is, corrected and precise

**Tara Assistant's pattern engine is Reflex-category work, not AI
judgment** - deterministic statistics and templates. If ever used, it
belongs conceptually alongside Reflex (a smarter rule-writer), not as
part of an AI-judgment function. Its genuine value is elsewhere: the
conversational-agent code (`app/agents/`), unrelated to this question.

**`ai_automation_suggester` is genuinely LLM-driven and is the real
candidate for Q18** - `coordinator.py` builds an actual prompt from live
entity/automation/script context and dispatches it to a configured
provider; `suggestions.py` parses real model output. It is also a native
HA `custom_component`, the same architectural shape as `abode_tools` and
`abode_ai_autonomy_steward_config` already use - no external-app boundary
to preserve, unlike Tara.

## Specific reusable methods identified - not a decision to adopt either system, a list of extractable techniques

**From Tara Assistant:**

1. **Statistical pattern detection as a cheap pre-filter.** Even though
   Tara's pipeline itself isn't AI, the detection *method* (group events
   by entity+action, require a minimum occurrence count, check `stdev`
   within a time window) is a legitimate, cheap way to surface candidate
   patterns before spending an LLM call on any of them - structurally the
   same two-tier shape already chosen for Vigil/Steward (cheap filter,
   then expensive judgment), just applied to a different problem.
   Worth considering as the "cheap tier" feeding an LLM-based "expensive
   tier" (`ai_automation_suggester`-style) reasoning step, rather than
   adopting either repo's suggestion pipeline whole.
2. **Per-pattern feedback tracking** (`UserPreference` model -
   dismissed/accepted/snoozed/created_automation, keyed to a pattern id
   so dismissed patterns don't resurface). Same shape as the Ward's
   Never-rule pattern, applied to suggestions instead of live actions -
   a real precedent for "don't keep re-proposing what was already
   rejected."
3. **`guardrails.py` fails closed on exception, worth taking regardless
   of its scoring mechanism.** On any exception during its LLM-based risk
   check - the LLM call failing, JSON parsing failing - the fallback is
   `passed=False, risk_score=75`: block by default, not permit by
   default. This is the opposite of the exact bug already found and
   fixed in `constraint_layer.py` (missing/unparseable data silently
   permitting everything) - independent confirmation of the same
   principle from a different codebase. **Not recommending its actual
   scoring mechanism** - it's an LLM judging risk, which is precisely
   what CAAF's externalized-assertion argument (already the Ward's own
   evidence basis) says not to do for a safety gate; a judgment-based
   check can drift or be reasoned around in a way a deterministic
   assertion cannot. The fail-closed *default*, not the LLM-scoring
   *method*, is what's worth carrying forward.

**From `ai_automation_suggester`:**

4. **Greedy budget-packing with graceful degradation, not a hard cutoff.**
   `_build_prompt()` tries a full entity block first, falls back to a
   compact block if the full one doesn't fit, and only skips the entity
   entirely if neither fits - stopping there rather than skipping ahead,
   with an explicit code comment on why: *"skipping ahead would bias
   low-budget prompts toward entities with shorter names."* Entities are
   randomly sampled up front for the same fairness reason. Every
   truncation/omission produces an explicit warning surfaced to the
   caller, and running out of budget for even one entity is a hard
   failure with a clear message, not a silent empty prompt. This is
   directly relevant to X1 (bounding what Vigil or Steward actually see)
   - the same class of problem as hapve's own 166 vs. 7,006-token gap,
   with a concrete, working algorithm already solving it.
5. **Entity coverage rotation across runs** (`_mark_entities_processed`,
   `_prune_processed_entities`) - avoids the same entities dominating
   every suggestion cycle.
6. **Robust parsing of imperfect LLM output** (`parse_suggestion_response`
   with layered fallback strategies - direct JSON, then loose structured
   extraction, then per-field regex extraction) rather than assuming
   clean JSON every time.
7. **No auto-apply.** Generated suggestions go to a persistent
   notification for human review (`format_suggestion_notification`) - no
   `create_automation`/auto-apply call found anywhere in `suggestions.py`.
   Matches the approve-once model already established elsewhere in this
   project rather than contradicting it.

## Not decided here

Whether Q18 gets built at all, and if so whether it forks
`ai_automation_suggester`, builds fresh using the methods above, or some
combination. This document records what's actually in the source, not a
commitment to use any of it.
