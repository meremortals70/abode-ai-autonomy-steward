# Decision record — five-layer architecture locked, supersedes "four-layer"

**Supersedes:** the *framing* (not the content) of
`hapve-architecture-four-layer-2026-07-30.md` and every reference since to
"the four-layer architecture." System 0/1/2 and the constraint layer, as
described in that document, stand unchanged. What changes is the count and
the status of Vigil: it was being treated as an addition sitting outside the
architecture ("the new tier," discussed alongside the four layers) rather
than as a fifth layer that belongs in the same enumerated set as the other
four.

---

```
DECISION: The architecture is five layers, locked, not four-plus-an-
          addition
DATE: 2026-08-01
CHOSE BECAUSE: five layers is what actually captures the fast-acting /
               slow-acting split that is the point of the whole
               architecture - Reflex (fast, no reasoning) and Vigil
               (fast-ish, narrow reasoning) sit clearly apart from
               Steward (slow, full reasoning) once Vigil is counted as a
               real layer rather than filed as a late addendum to a
               four-layer document
REJECTED: continuing to refer to "four layers plus Vigil" - correct in
          content, wrong in framing; treats the layer that does the
          actual salience judgment as an afterthought to the set that
          defines the architecture
EVIDENCE CLASS: [A] - architect correction, this session
NOT CHANGED: constraint_layer.py, ai_autonomy_steward, or any other file/
          class - this is architecture framing, not a code change
```

## The five layers, in data-flow order — topology stated precisely

**Senses feeds two independent, parallel consumers - Reflex and Vigil do
not feed each other, and neither is upstream of the other:**

```
                    Senses (System 0)
                   /                 \
             Reflex (System 1)      Vigil (new)
             fast, deterministic    domain-scoped judgment,
             no reasoning, acts     decides what wakes Steward
             directly                       |
                                             v
                                     Steward (System 2)
                                     slow, full reasoning,
                                     proposes actions
                                             |
                                             v
                                  the Ward (constraint layer)
                                  gates every proposal against
                                  the constitution
                                             |
                                             v
                                      HA service calls
```

This is worth stating explicitly because it would be easy to misread the
addition of Vigil as sitting "between Reflex and Steward" in sequence -
it doesn't. Reflex acts on Senses' output directly and immediately,
completely independent of whatever Vigil is doing with the same input.
Vigil's only job is deciding what reaches Steward.

## What this changes in practice

Nothing yet builds differently - Vigil is still unbuilt (Q13). This
document changes how the architecture is talked about and referenced,
so that when Q13 is picked up, it's understood as building the fifth
layer of the locked design, not bolting an extra piece onto a four-layer
document that predates it.

## Supersedes, precisely

`hapve-architecture-four-layer-2026-07-30.md` - keep as the source for
System 0/1/2's original reasoning and the Figure Helix/CAAF evidence
basis (unchanged, still valid). Its title and "four" framing are
superseded by this document; its content is not.
