# Policy — OHF AI policy, and the review gate it requires

**Supersedes:** nothing. This **amends** `hapve-handover-collaborative-cycle-2026-07-30.md`
by inserting one new step into the cycle in its §3, and adds a classification
rule that did not previously exist. Everything else in that document stands
unchanged.

**Source:** Open Home Foundation AI Policy,
`https://developers.home-assistant.io/docs/ai_policy`, last updated
20 July 2026, read in full 31 July 2026. Evidence class **[V]** — direct read
of the primary source, not a summary of it.

---

## 1. Scope — what this policy does and does not govern

The policy governs contributions **to** Open Home Foundation projects: pull
requests, issues, and code-review communication on their repositories. It
does not govern what is built in private repositories for private use.

This distinction matters, and getting it wrong in either direction is a
failure:

- Treating it as binding on everything would impose an upstream review
  burden on private homelab work that nobody is asking for.
- Treating it as irrelevant would mean discovering the bar only at the point
  a contribution is closed without review.

Therefore every artefact this project produces is classified at creation, and
the gate applies to one class only.

## 2. Classification — assigned when the artefact is created, not later

| Class | Definition | Gate applies |
|---|---|---|
| **Private** | Lives in Jason's own repositories and on hapve/intranet. Never submitted to an OHF project. | No |
| **Upstream-bound** | Any PR or issue to `home-assistant/core`, `home-assistant/brands`, the developer docs, HACS default-repository submissions, or any other OHF-governed repo. | **Yes** |

Ambiguous cases are classified upstream-bound. The cost of the gate is one
extra step; the cost of misclassifying is a closed contribution and, per the
policy's enforcement section, a repeat pattern risks being blocked from
contributing at all.

Note that a repository being public does not by itself make its contents
upstream-bound. `abode-ai-tools` is public and remains private-class under
this rule. It becomes upstream-bound the moment a HACS default-repository
submission is contemplated.

## 3. The new gate — step 4a, between Review and Act

Inserted into the cycle in `hapve-handover-collaborative-cycle-2026-07-30.md`
§3, after step 4 (Review) and before step 5 (Act):

> **4a. Explain — upstream-bound artefacts only.**
> Before submission, Claude walks Jason through every change, in Jason's
> terms, until Jason can defend each one unaided. Jason pushes back until
> that is true. Claude does not draft the PR description, the issue text, or
> any reply to a maintainer.

The policy's own words set this bar, not this document's interpretation of
it. Three requirements, quoted:

- Contributions must be reviewed and understood by the contributor before
  submission, and the contributor should be able to explain every change in
  a pull request they submit. Anything appearing to be unreviewed AI output
  will be closed without review.
- AI must not be used to generate answers to questions from maintainers.
  Improving grammar or clarity of text Jason has written himself is
  explicitly fine; the substance must be his.
- Context from an AI interaction included in a comment must sit in a quote
  block, be disclosed as such, carry Jason's own commentary on its relevance,
  and must not be a long snippet.

## 4. The honest gap this closes

Stated plainly because the policy's substance is a standard worth meeting
regardless of whether it is binding.

Current practice is that Claude writes code, verifies it parses, and confirms
that primary sources say what Claude claims they say — then hands it over.
Jason has not read every line of, for example, `paperless.py`. For private
work that is Jason's call to make and this document does not change it.

But the `abode-ai-tools` README states that implementation and code were
"written in collaboration with Claude (Anthropic)." That statement is
accurate and should stay. It should not, however, be allowed to imply a
line-by-line human review that has not occurred. Step 4a is what makes the
claim true for anything that leaves Jason's own repositories.

## 5. Autonomous agents — a live constraint, not a hypothetical

The policy states that autonomous agents are not allowed to contribute, and
that PRs or issues believed to be autonomously created will be closed and
automated comments may be marked as spam.

Nothing in the current working method is autonomous: Jason directs every
step and runs every command. But `ai_autonomy_steward` is, by design, a
continuously reasoning service. If it ever gains the ability to file an
issue, open a PR, or post a comment to any OHF repository, that capability
is in breach of this policy on the day it is built — regardless of intent.

**Standing constraint:** System 2 gains no outbound write capability to any
OHF-governed repository. This is recorded here so it gates the design rather
than being discovered afterwards.

## 6. Decision record

```
DECISION: OHF AI policy adopted as a binding gate on upstream-bound
          artefacts, and as a voluntary standard elsewhere
DATE: 2026-07-31
CHOSE BECAUSE: the policy's review bar is the correct standard for any code
               leaving this project regardless of enforcement, and the
               classification rule prevents both over- and under-applying it
REJECTED: applying the gate to all private homelab work - imposes an
          upstream review burden with no corresponding benefit
REJECTED: treating the policy as irrelevant because current work is private
          - the bar would then first be encountered at the point a
          contribution is closed
EVIDENCE CLASS: [V], direct read of the policy, 31 Jul 2026
FALSIFIED IF: an OHF project rejects a contribution from this project that
              passed step 4a, showing the gate does not actually meet the
              bar - not yet tested, no contribution has been submitted
```

## 7. Open questions

**Q1.** Is HACS itself OHF-governed? A HACS default-repository submission is
classified upstream-bound in §2 on a precautionary basis; this has not been
verified against HACS's own governance.

**Q2.** Whether the policy has changed since 20 July 2026 — it is newer than
Claude's training cutoff and is known only from the 31 July read. Re-read
before any submission rather than relying on this document's summary.

## 8. What this does not change

Nothing in `hapve-handover-collaborative-cycle-2026-07-30.md` other than the
insertion of step 4a. The Document Standard, the source-of-truth table, the
evidence classes, and the standing behavioural rules are untouched.
