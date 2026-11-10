# Design rules

One file per design rule, recorded from the decisions made across the project's
Claude sessions (see `hapve-asbuilt-ai-autonomy-steward-2026-07-30.md` and its
handover) and the running code. A number marked "Superseded" is no longer in force.

| Rule | What it says |
| --- | --- |
| [D000](D000.md) | The steward is System 2: continuous, goal-level reasoning over the whole home, not per-entity reaction |
| [D001](D001.md) | The home is four layers: perception, deterministic automations, reasoning, and an independent constraint layer |
| [D002](D002.md) | The steward wakes on events only — never a timer, never polling, never a per-entity watch-list |
| [D003](D003.md) | Every pass pulls the complete current state fresh, not a delta and not an accumulated history |
| [D004](D004.md) | Approval is per action_type, but the steward still re-decides fresh every pass |
| [D005](D005.md) | A new kind of action is proposed, never acted on before approval |
| [D006](D006.md) | The approval response is three-way: Approve, Deny, Never |
| [D007](D007.md) | The steward can propose retiring or replacing an approved action_type |
| [D008](D008.md) | The charter defines the home's purpose and firm boundaries, which hold regardless of any approval |
| [D009](D009.md) | The constraint layer is deterministic and independent of the steward's reasoning |
| [D010](D010.md) | Constraints are append-only; nothing in the running system can edit or remove a rule |
| [D011](D011.md) | The steward refuses to start with zero constraints |
| [D012](D012.md) | min_confidence gates both proposals and actions |
| [D013](D013.md) | The steward ships as two parts, and selectors live in the integration, not the App |
| [D014](D014.md) | The App reads its configuration from the companion sensor at startup and on change |
| [D015](D015.md) | The companion integration exposes LLM tools for config, charter, and triggering a pass |
| [D016](D016.md) | Perception sources are pluggable: Home Assistant now, Frigate and Tara later |
| [D017](D017.md) | A quiet home is correct: when nothing is warranted, the steward does nothing |
| [D018](D018.md) | The steward executes the parameters the model supplied, parsed strictly, and never invents its own |
| [D019](D019.md) | An approval or Never is honoured only with the single-use nonce of a pending proposal |
| [D020](D020.md) | Every action decision and its outcome is appended to an append-only decision log |
| [D021](D021.md) | The charter is a household-extendable data file, seeded and read fresh each pass |
