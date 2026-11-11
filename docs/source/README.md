# Source architecture documents

These are the original architecture theses and as-builts from the Claude
sessions (July–August 2026). They are retained as the **historical record** —
the reasoning and history behind the architecture, not its current form.

The current, authoritative version is [docs/architecture.md](../architecture.md).
Key corrections made since these documents were written:

- **Vigil is a series of domain microservices, each with a learned model,
  doing deterministic routing — no LLM.** The theses described a "cheap,
  model-driven salience tier" that calls the AI Engine; that was superseded.
- **There is exactly one LLM — the AI service, sitting above the Steward.**
  Nothing below the Steward (Senses, Reflex, Vigil) uses it.
- **Models are seeded by the LLM (or the setup agent), then learn from HA's
  recorder, then operate deterministically** — the *seed → learn → operate*
  lifecycle.
- A **catch-all** microservice escalates events no domain claimed (or two or
  more claimed) to the Steward.

Read `docs/architecture.md` for the current architecture; treat these files as
the history behind it.
