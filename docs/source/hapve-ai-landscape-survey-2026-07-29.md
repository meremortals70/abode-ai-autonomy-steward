# hapve / Abode — AI Landscape Survey: what already exists vs. what's being built

**29 July 2026.** Requested by the architect, twice — the first pass
(retracted, see §0) wrongly scoped this to Paperless retrieval alone. This
version covers the whole Abode project: retrieval, voice pipeline, model
choice, proactive automation, camera/vision, and Homebox.

Every finding below is evidence-tagged per the Document Standard. Most of
this document is **[V]** — vendor documentation, project READMEs, and
search-engine summaries of primary sources, gathered from the open web this
session. Where a primary source (repository source code) was actually read
rather than summarized, it says so explicitly and is tagged **[source]**.
**Nothing here is [M]** — nothing was tested against this hardware or this
deployment. That is the entire point of this document: it exists to be
checked against Jason's actual systems before anything in it changes a
single line of code.

---

## 0. Correction

The first version of this survey covered only Paperless-ngx retrieval,
after being asked to survey the whole project. That was wrong and is not
repeated here.

---

## Decision — Autonomy Model (resolves a standing open question, settled 30 Jul)

**DECISION:** "Autonomous home" means the system acts on its own initiative
after seeking approval the first time an action type occurs; once approved,
it executes that action type without asking again. This is settled by the
architect directly, is not to be re-asked in any form, and supersedes any
reading of this project's earlier "voice-first response only" framing.

**CHOSE BECAUSE:** stated directly by the architect. Not inferred.

**REJECTED:** voice-first-response-only (the system only ever answers when
asked) - explicitly rejected as an interpretation.

**EVIDENCE CLASS:** [A] - architect decision, highest authority in this
project's evidence scheme.

**FALSIFIED IF:** never - this is a standing architectural fact, not a
hypothesis. Do not re-test it, re-ask it, or reintroduce it as a caveat.

### What this means concretely, checked against what's already installed

`home_generative_agent`'s **Sentinel** component (§9.1) already implements
this exact pattern, not an analog of it [V, official docs, direct read of
`docs/sentinel.md`, 30 Jul 2026]:

- **Discovery → Proposal → approval, once:** Sentinel's LLM discovery
  proposes new rules from observed patterns; a human approves or rejects
  each proposal exactly once (`approve_rule_proposal` service); an approved
  proposal becomes a permanently registered dynamic rule.
- **Autonomous execution thereafter:** at autonomy level 2/3
  (`sentinel_auto_execution_enabled`), an approved rule fires and executes
  its allowed action automatically on every subsequent detection - no
  further approval per occurrence. Level 1 (default) still notifies only;
  moving to 2/3 is itself a one-time configuration step, optionally PIN-
  gated (`sentinel_require_pin_for_level_increase`).
- **Safety gates already built, not hypothetical:** `min_confidence`,
  `max_actions_per_hour`, an explicit `allowed_services` allowlist, an
  idempotency window, and a canary dry-run mode - this is more rigorous
  than anything sketched for the unbuilt `abode_autonomy` component to
  date.

**Practical consequence: do not build a bespoke approve-once-then-autonomous
gate for `abode_autonomy`.** That mechanism already exists, is more
thoroughly safety-gated than anything designed so far this project, and is
sitting installed and unconfigured. Building a parallel one would be the
same mistake as `paperless.py` re-implementing what Paperless-ngx's own
chat feature already does (§1).

**The real, specific gap - not hand-waved, checked against the actual rule
template list in `docs/sentinel.md`:** every one of Sentinel's built-in and
generated rule templates triggers on live entity/sensor/camera state
(locks, entries, batteries, appliance power, baselines). **None trigger on
a fact extracted from a document** (a registration due date, an insurance
renewal date). That pipeline does not exist anywhere yet, installed or
custom. The remaining real work, precisely scoped:

1. Build the extraction step: document arrives in Paperless → structured
   fact (a date, an amount, a policy number) written into HA as an entity
   or helper. Nothing installed does this today - it's the one piece of
   `paperless.py`'s intent that has no existing-tool answer.
2. Confirm whether that entity, once it exists, can be picked up by one of
   Sentinel's **already-generic** templates (`sensor_threshold_condition`
   for "days until due < N", or `entity_staleness`) without writing a new
   Sentinel rule type - or whether it needs a custom dynamic rule via
   Sentinel's own Discovery/`approve_rule_proposal` API. This is
   unconfirmed and is the next concrete question, not "worth checking" -
   it is what determines whether any Sentinel code needs to change at all.

### Correction (second one, 30 Jul) — two separate functions were conflated, not just RAG's definition

The previous version of this subsection was itself wrong, on its own
terms - not in its technical findings, but in its framing. It treated
document-search RAG (Paperless-ngx's native chat, open-webui) as a
demoted, lesser answer competing with "the real RAG" for autonomy. That
forced two unrelated functions into one slot. Restated exactly as the
architect described them, and kept permanently separate from here on -
this is not a re-definition of RAG, it is a recognition that **this
project has two distinct functions that must never be merged into one
narrative again:**

**Function 1 — the autonomous home.** The system reasons over device and
sensor state and acts on its own initiative, per the Autonomy Model
decision above: approve once, then autonomous, forever after. This is
Sentinel's domain entirely. It has nothing to do with documents. If it
needs durable memory at all, that memory is operational - a learned
preference, an approved rule's outcome, something that changes how an
automation behaves - never a document fact.

**Function 2 — voice, beyond device control.** The household asks
business-as-usual questions - *when did we buy the brushcutter, how much
did we pay for X* - and gets an answer pulled from the household's own
records (Paperless), and, when those records don't have the answer,
potentially from a live web search. **This is a separate, first-class
capability. It is not a fallback for Function 1 and it is not secondary
to it.** Paperless-ngx's native chat (§1) and open-webui's RAG (§11.2)
belong here, undemoted - they were never the wrong answer, they were
answering the wrong question by being placed against Function 1 at all.

**Web search, as an extension of Function 2, is new scope introduced
this correction and has a first-pass finding below in §12** - it had not
been researched before this point in the session.

The `upsert_memory`/Postgres+pgvector material below is Function 1's
operational memory only, and was never wrong on its own terms - only
wrongly framed as if it competed with document search. Restated with
that scoping explicit:

**What matches Function 1, checked against source, not the feature list:**
`home_generative_agent` has an `upsert_memory` LangChain tool backed by
Postgres+pgvector - a separate running service from the agent process, so
it survives an AI-engine restart as long as the Postgres container itself
persists. This is distinct from HGA's differently-named "Tool Retrieval
(RAG)" feature, which only indexes HGA's own tools for context management
and has nothing to do with household facts - the two should not be
conflated.

**The gap, resolved as far as source allowed:**

- `services.yaml` [source, direct read, 30 Jul] - no standalone HA service
  exists for memory writes. Every other HGA subsystem (Sentinel, face
  enrollment, camera snapshot) has its own service; memory does not.
  Confirmed, not assumed: a document-extraction pipeline or an approved
  Sentinel decision cannot write to long-term memory via a normal HA
  service call today.
- `const.py` [source, direct read, 30 Jul] - Postgres serves as both the
  vector store and the LangGraph checkpointer, meaning the memory table
  lives inside LangGraph's own internal persistence layer, not a bespoke
  HGA table with a published schema.
- **Not resolved:** the actual memory-writing module's source. GitHub's
  API returned nothing on both the directory-listing and full-tree
  requests this session, and guessing the filename directly did not
  locate it. This is a tool limitation hit this session, stated plainly
  rather than papered over with a guess.

**Decision, not left open:** until that module is read and a direct write
is confirmed safe, route extracted facts and approved Sentinel decisions
into memory via `conversation.process` against the HGA agent, using its
own `upsert_memory` tool rather than writing to an internal LangGraph
table whose schema hasn't been verified. Revisit only if the source read
changes this.

---

## 1. Retrieval / Paperless-ngx — Function 2 (voice BAU queries), carried from the first pass

Full detail in this document's superseded first version (same filename,
overwritten) is condensed here; nothing in §1 changes on a second look.

**Headline: Paperless-ngx now ships its own native RAG document chat,
merged into core.** Confirmed from source: the `dev` branch registers
`POST /api/documents/chat/` → `ChatStreamingView`
(`paperless/urls.py`) [source, 29 Jul 2026]. A maintainer confirmed in the
implementing PR's own discussion thread that it runs RAG across **all**
documents and can answer exactly the kind of question this project has
been building toward — quoted directly: *"So we could ask something like:
'What is the total amount of the invoices I received in the first quarter
of 2025?'"* → *"Yes."* [source, PR #10319 thread]. Mechanism: LlamaIndex +
FAISS vector index, embedding backend configurable (HuggingFace local by
default, Ollama or OpenAI optional).

**Corrected a wrong lead:** paperless-gpt, already running in the infra
pod, does NOT do chat/RAG — its own README says so in its second sentence.
It does LLM-enhanced OCR and auto-tagging/titling only.

**Not yet known:** whether the running paperless-ngx instance is new
enough, whether `PAPERLESS_AI_ENABLED` is set, and whether its backend can
be pointed at 252's Lemonade endpoint. One diagnostic, unresolved:

```bash
podman exec paperless-ngx env | grep -i PAPERLESS_AI
curl -s http://localhost:8010/api/status/ -H "Authorization: Token <token>" | head -c 2000
```

**If live:** most of today's custom `find_document`/`read_document`/
`PaperlessSearchAPI` retrieval code is likely redundant with a
better-built, upstream-maintained feature. A thin bounded proxy to
`/api/documents/chat/`, plus a `sum_values`-style deterministic step for
exact arithmetic, is probably the right remaining shape - RAG retrieval
being native doesn't remove the risk of an LLM adding up many numbers
itself, which is a separate problem native chat doesn't solve.

qdrant, litellm, and open-webui are all already running in the infra pod
and were checked — none of them change this recommendation. They would
matter as a fallback if the native chat turns out unusable, not as a first
choice; qdrant in particular is not what paperless-ngx's own feature uses
internally (that's FAISS), so building a separate qdrant-backed index would
be duplicating, not complementing, what the software already does.

---

## 2. Model choice (Q3) — the project's own highest-priority open question

The 28 Jul evening as-built named this explicitly: *"Q3 (model choice) is
now the highest-value open question... Gemma-4-26B-A4B was chosen on a
blog citation [V], never a comparison here."* This survey adds current
information, still [V], still not a replacement for measuring it.

**Three credible on-device tool-calling bases are named consistently
across 2026 sources** [V, multiple aggregator/benchmark sites, 29 Jul
2026]:

| Model | Size | Reported strength | Reported weakness |
|---|---|---|---|
| Qwen3-4B-Instruct-2507 | 4B | BFCL v4 single-turn lead "out of the box" | **Already falsified in this project's own Document Standard**: multi-turn BFCL 35.25% (arXiv 2511.22138) - the project's own worked example of a vendor claim that didn't hold |
| Gemma 4 E4B | 4B active (MoE) | Currently in use on this build | Chosen on a blog citation, never benchmarked against alternatives on this hardware |
| Phi-4-Mini-Instruct | 3.8B | Reported better multi-turn reasoning-chain quality; 15-20% faster than Qwen3-4B, 5-10% faster than Gemma 4 E4B in third-party comparisons | Smallest context / least agentic-data-heavy training mix per the same sources |

**Why this matters more than it did in July:** the project's own 28 Jul
finding was that decode and round-trip count, not prefill, are now the
binding cost, and that a compound request cost six model round trips in
one measured case. If Phi-4-Mini's reported multi-turn advantage is real
on this hardware, a turn like that could cost meaningfully less wall-clock
time on a smaller, faster model — but every number in this table is [V],
gathered from aggregator sites repeating each other's benchmark claims, not
from BFCL's own leaderboard or a run against this hardware. The project's
own Document Standard example (Qwen3-4B's "established tool-calling
strength" turning out to be 35.25% multi-turn) is a direct warning against
trusting this table as-is.

**Recommendation, not a decision:** this is worth an actual side-by-side
test now that `abode_tools`' tool surface is more complex than it was in
July (real multi-turn tool sequences exist to test against, e.g.
`ask_archive`'s nested search-then-read pattern) - run the same real
requests against Gemma 4 E4B (current) and Phi-4-Mini-Instruct, measure
round-trip count and wall-clock time, not benchmark citations.

---

## 3. Voice pipeline — one concrete, actionable finding

**Kokoro's streaming capability may already exist on 252 and simply not be
reachable through the current HA integration.** A third-party source
citing Lemonade's own changelog states streaming support for Kokoro TTS
via the OpenAI-compatible `/api/v1/audio/speech` endpoint shipped in
Lemonade **v9.4.1** [V, GitHub issue tracker citation, 29 Jul 2026]. 252 is
running Lemonade **11.5.0** (`hapve-asbuilt-voice-2026-07-28-evening.md`
§2) - a later version than 9.4.1.

This directly bears on Q24 (`hapve-asbuilt-voice-2026-07-28-evening.md`
§12.5): the 28 Jul session found "no streaming option appears in the
config flow" for the `sfortis/openai_tts` HA integration and concluded
this build has no streaming path. **This survey suggests that conclusion
may have been about the wrong layer** - if Lemonade's endpoint has
supported streaming since well before the version currently running,
the gap may be in the HA-side integration not exposing/using it, not in
the underlying server. Worth checking directly against Lemonade's own API
docs for the installed version, not inferred from a config-flow UI
absence. **Not verified this session; the two claims (Lemonade version
supports streaming vs. sfortis/openai_tts doesn't expose it) have not been
reconciled against each other.**

Everything else checked (Wyoming protocol architecture, faster-whisper,
Piper) matches what's already built and documented; no better-fit
alternative surfaced for this project's specific constraints (local-only,
NPU-hosted, single household).

---

## 4. Proactive automation / semantic sensors (§3.4-3.6) — confirms, doesn't change, the existing direction

Nothing found changes the guide's or the 28 Jul session's conclusions.
2026 industry commentary on mmWave presence sensing and "sensor fusion"
[V, various smart-home blogs] describes exactly the FP2/mmWave-vs-PIR
distinction already identified as the prerequisite for §3.4, and the
"reactive to proactive" framing matches HA's own 2026.4 release (live
tool-call visibility in Assist, proactive conversation starts - already
noted in the first survey pass, §4). No new tool or integration surfaced
that would change the `ai_task`-instead-of-`abode_autonomy` direction
already recorded as a design question in the 28 Jul evening as-built §12.2.

---

## 5. Camera / vision (Frigate, LXC 249) — two findings worth carrying forward

1. **Frigate 0.18 (currently beta, GA still pending per release tracking)
   is building the same native-chat pattern found for Paperless-ngx.** Its
   settings UI adds semantic search (GenAI-provider embeddings) and a
   tool-calling chat agent with camera-specific tools: search tracked
   objects, semantic similarity search, live camera context, camera
   feature toggling, VLM monitoring, and an activity-recap tool [V,
   release notes/discussion, 29 Jul 2026]. This is structurally the same
   thing §1 found in Paperless-ngx - a maintained, native RAG/chat layer
   that may make custom tool-building redundant once it's deployed. Worth
   checking again when Frigate 249 actually gets built, not before -
   0.18's GA status is unconfirmed and the project's own gating (0.18 GA +
   Phase 2 MQTT relocation + Phase 2 config backup) is unmet regardless.
2. **Frigate also has its own community MCP server, reported at 45 tools
   across 9 categories** [V, mcpmarket.com/dedsxc's mcp-frigate, 29 Jul
   2026] - the same over-exposure problem `paperless-mcp` had (44 tools, no
   read-only flag) is very likely to recur here. The lesson already
   recorded for Paperless - proxy a small bounded set, or use the
   `ai_task`+`llm_api` nested-call pattern, never attach the raw MCP server
   to the voice-path conversation agent - should be treated as a standing
   rule for any future MCP server this project touches, not something to
   re-derive per integration.

---

## 6. Homebox retrieval — a possible simpler path than the one already approved

The approved design (28 Jul, `hapve-asbuilt-voice-2026-07-28-evening.md`
§11) is a `find_item` proxy tool against the already-running `homebox-mcp`
(port 8031), following the same pattern as Paperless. That MCP server's
actual tool surface was never read - it remains genuinely unstarted.

**This survey found a second, more direct option not previously
considered:** `marcboivin/homebox-ha` - a dedicated Home Assistant
integration for Homebox, rather than an MCP proxy [V, GitHub, 29 Jul
2026]. If it exposes Homebox items as HA entities or services directly,
that may be simpler than standing up an MCP-proxy tool from scratch
(no bespoke `_rpc`/JSON-RPC layer to write and verify, as was needed for
`paperless.py`) - but nothing about what it actually exposes, its
maintenance state, or its compatibility with this Homebox deployment was
read this session. **Not a recommendation, a alternative worth reading
before starting the originally-approved MCP-proxy build.**

---

## 7. Standing pattern across every finding in this document

The same shape shows up in retrieval, camera, and (soon, if the pattern
holds) inventory: the underlying open-source project has been building a
native AI/chat/RAG layer faster than this project has been building
bespoke proxies for it. Paperless-ngx confirmed live in source. Frigate
confirmed in beta. Homebox not checked for the same pattern this session -
worth doing before the `find_item` tool is built, not after.

**Standing recommendation for anything touched from here on:** before
writing a proxy tool against any self-hosted project's API or its
community MCP server, check that project's own recent releases and open
PRs for a native chat/RAG/tool-calling feature first. This session found
one by reading a single merged PR's discussion thread - it did not require
deep investigation, only asking the question before writing code instead
of after.

---

## 9. Already-installed custom_components — not proposals, already on the system

Everything in §1-§7 above was "what exists on the open web that this
project could adopt." This section is different in kind: these are
`custom_components` **already present** in `/config/custom_components/`
on Jason's HA instance right now, confirmed from his own `ls` output
[M, 29 Jul 2026, directory listing]. Identification of what each folder
*is* (which upstream repo it maps to, what it does) is still [V] -
folder names were matched to project READMEs by name and description,
not by reading the installed code. Whether any of them are configured,
enabled, or doing anything is unconfirmed and untested - "installed" is
not "active."

### 9.1 The two findings that matter

**`home_generative_agent` → `goruck/home-generative-agent`.** This is the
single largest finding of this session, larger than the Paperless-ngx
native-chat finding in §1. It is a LangGraph-based HA integration that
already does, in one maintained package: conversational device control,
automation authoring, camera-image analysis, anomaly detection
("Sentinel"), face recognition, and long-term semantic memory over
Postgres+pgvector, with streaming responses [V, full README read, 29 Jul
2026]. Postgres is already running in the infra pod. Read against
today's work directly: this is not adjacent to `abode_tools` and the
unbuilt `abode_autonomy` component, it is substantially the same
capability, already built, already installed, unconfigured.

**`llmvision` → `valentinfrlch/ha-llmvision`.** Mature, actively
maintained camera/vision analysis integration, native Frigate event
support, multi-provider backend (including Ollama and any
OpenAI-compatible endpoint - Lemonade on 252 qualifies), event timeline,
notification blueprint [V, full README read, 29 Jul 2026]. This
substantially covers the camera/vision ground §5 flagged as a future
build against Frigate 0.18.

**Standing recommendation, same shape as §7:** before writing one more
line of `abode_tools`/`abode_autonomy` code, read what `home_generative_agent`
and `llmvision` actually do when configured against this stack - not
their READMEs, their source and their HA config flow. If they cover the
ground, the remaining Abode-specific work shrinks to wiring and
household-specific policy, not building an agent framework from scratch.
**Not yet done. This is the next diagnostic, not a decision - the
question is whether they can be pointed at Lemonade/252 and Postgres as
they stand, and what if anything they're missing for this project's
specific requirements (Paperless retrieval, Homebox, the household-only
latency profile in the project's opening principle).**

### 9.2 Secondary conversation/automation agents - overlapping, lower priority

Four more installed components sit in the same "AI conversation agent or
automation-suggestion tool" category as `home_generative_agent`, but none
read as a superset the way it does:

- **`ai_automation_suggester`** → very likely
  `ITSpecialist111/ai_automation_suggester` (750+ stars, v1.5.7 as of
  June 2026) - scans entities/devices and suggests automation YAML via a
  configurable AI provider including Ollama [V, 29 Jul 2026]. A narrower
  tool than `home_generative_agent`'s automation authoring; would only
  matter if `home_generative_agent`'s own authoring capability turns out
  weaker in practice.
- **`ha_text_ai`** → very likely `smkrv/ha-text-ai` - multi-provider
  (OpenAI/Anthropic/DeepSeek/Gemini) conversational/automation
  integration [V, 29 Jul 2026]. Cloud-provider-first in its own
  documentation; runs against this project's local-only principle unless
  it also supports an OpenAI-compatible local endpoint - unconfirmed.
- **`llama_conversation`** → not pinned to a specific upstream repo this
  session. Several candidates share the concept (local llama.cpp-backed
  conversation agent for HA Assist: `acon96/home-llm`,
  `M4TH1EU/llama-assist`, `skye-harris/hass_local_openai_llm`) but none
  was confirmed to match the exact installed folder name [V, unresolved,
  29 Jul 2026]. Lower priority regardless - Lemonade already provides an
  OpenAI-compatible endpoint, which is the same integration point
  `local_openai` (already installed and presumably in the active
  conversation-agent role) uses; a llama.cpp-direct agent would be a
  parallel path to the same model host, not a new capability.
- **`ai_agent_ha`** → `sbenodiz/ai_agent_ha`, already on Jason's own
  curated link list from before this session. Natural-language →
  automation-authoring agent, same category as
  `ai_automation_suggester`.

None of these four block or gate anything - they're worth a five-minute
look each only after the §9.1 question (does `home_generative_agent`
cover the ground) is answered, not before.

### 9.3 MCP-related installed components - a different architecture question

**`mcp_assist`, `mcp_server_http_transport`, `ha_mcp_tools`** - none of
the three folder names matched an exact upstream repo by name in search
[V, 29 Jul 2026 - searched, not confirmed]. The category is clear even
though the exact repos aren't: these all expose **Home Assistant itself**
as an MCP server, so that an external AI client (Claude Desktop, Claude
Code, or similar) can control HA over MCP. Candidates in this space
include `homeassistant-ai/ha-mcp`, `achetronic/hass-mcp`,
`ganhammar/hass-mcp-server`, `jango-blockchained/advanced-homeassistant-mcp`
(50+ tools, 3 transports), and `robbrad/homeassistant-mcp` (40 tools,
BM25 search to keep context lean - notably the only one of these that
appears to have already solved the tool-overexposure problem §5 and §1
flagged for `paperless-mcp` and Frigate's MCP server).

**This is the inverse direction from everything else in this document.**
Sections 1 and 5 are about Abode's own LLM reaching *out* to other
services' MCP servers (Paperless, Frigate) as a tool-calling client. An
installed HA-as-MCP-server component is about an *external* AI client
reaching *into* HA. Both can coexist, but they answer different
questions - the first is "how does Abode's agent get data," the second is
"can Jason drive HA from Claude Desktop directly." Worth confirming which
one (or both) Jason installed these for before assuming either is part
of the Abode voice-path architecture.

### 9.4 UI/satellite layer - not an AI-capability finding

**`view_assist`** (`dinki/View-Assist`) and **`voice_satellite`**
(companion to `jxlarrea/voice-satellite-card-integration` /
`kiosk-satellite`) are visual-feedback and satellite-network tooling for
Assist - screen/tablet UI, wake-word satellite management - not
retrieval, reasoning, or automation-authoring capability [V, 29 Jul
2026]. They don't change anything in §1-§7 or §9.1-9.3. Noted for
completeness only, since they were on the installed list.

---

## 11. Second sweep — the wider ecosystem, and what's already running unsurveyed

Prompted by a direct correction: §1-§9 were still reactive, built from lists
Jason supplied rather than an independent sweep. This section covers what
that sweep found, in four tiers ordered by how directly each changes the
architecture rather than by discovery order.

### 11.1 Tier 1 — HA core itself, not a custom_component, not HACS

**Home Assistant core now ships two native MCP integrations, both official,
neither requiring HACS or a custom_component:**

- **`mcp_server`** — HA acting as an MCP server, available since **2026.7.4**
  [V, home-assistant.io/integrations/mcp_server/, 30 Jul 2026]. Exposes HA's
  own Assist API (devices, entities, scripts) to external MCP clients like
  Claude Desktop. This is the "external AI controls HA" direction §9.3 flagged
  as unconfirmed - it turns out the canonical way to do it is now core, not
  any of the three installed custom_components with unclear provenance.
  Access is scoped through the same exposed-entities settings Assist already
  uses.
- **`mcp`** — HA acting as an MCP **client**, i.e. HA's own conversation
  agent/`llm_api` reaching out to external MCP servers, available since
  **2026.6.0** for the in-process variant [V, same source]. This is directly
  relevant to §1 and §5's Paperless/Frigate MCP findings: the mechanism to
  attach `paperless-mcp` or a Frigate MCP server to an HA-side agent is core
  HA, not a bespoke JSON-RPC client (which is what `paperless.py`'s
  `_PaperlessTool` classes hand-roll today). It does not solve the
  tool-overexposure problem (44/45-tool servers still expose everything) -
  that finding stands - but it removes the need to hand-write the transport
  layer at all. **This is a direct architecture question for `paperless.py`:
  today's code implements its own HTTP/JSON-RPC calls to paperless-mcp
  end-to-end; core HA's `mcp` client integration may make that layer
  redundant, leaving only the tool-scoping problem to solve.**

Confirms and updates §9.3: the three installed custom_components in that
category (`mcp_assist`, `mcp_server_http_transport`, `ha_mcp_tools`) most
likely predate or duplicate what's now built into core. Worth checking HA
version against 2026.6.0/2026.7.4 as the very first diagnostic before doing
anything else with any of them.

### 11.2 Tier 2 — already running in the infra pod, native capability never surveyed (open-webui/n8n items are Function 2 - voice BAU queries; litellm is plumbing for both functions)

Three services in the infra pod (postgres, redis, nats aside) were treated
in every design so far as plumbing only. None had their own native
AI/agent/RAG capability checked. All three do more than assumed:

- **open-webui** - ships a native RAG engine (upload documents, vector search
  or full-content injection), **Pipes/Functions/Tools** (Python tools that
  run inside chat, MCP and OpenAPI server connections, message-routing
  pipelines), and - most relevant to the Paperless retrieval problem this
  whole project keeps circling - a documented "shell-style interface over
  knowledge bases (`ls`, `tree`, `grep`, `cat`, `head`/`tail`)" that models
  chain more reliably than bespoke search tools [V, docs.openwebui.com,
  Mayhem Code guide, 30 Jul 2026]. open-webui is already running and already
  has an endpoint. **This is a real alternative to hand-building
  `find_document`/`ask_archive` in Python**: point it at the household's
  documents (Paperless export or direct DB access) and let its own RAG
  engine and shell-style tool do what `paperless.py` v1-v4 have been trying
  to build from scratch all session, including v4's `_build_structure_schema`
  workaround for a private HA function - none of which is needed if
  open-webui's own tool surface does the job.
- **n8n** - ships a native **AI Agent node** using LangChain's Tools Agent
  pattern: visual orchestration of multi-tool, multi-step agent workflows,
  with memory nodes and tool nodes as first-class citizens, wired to any of
  n8n's 400+ existing integration nodes [V, docs.n8n.io, 30 Jul 2026]. This
  is a direct alternative to the hand-written Python orchestration in
  `paperless.py` (`_ask` → `_ai_task_generate` → nested `llm_api` tool loop)
  - the same multi-step "search, then read, then sum" pattern is exactly
    what n8n's Tools Agent is designed to visually build and maintain,
  without writing or debugging Python against HA's private, unexported
  schema-conversion functions.
- **litellm** - confirmed as a unified OpenAI-compatible gateway/router
  (virtual keys, spend tracking, provider fallback), not an agent or RAG
  capability [V, litellm.ai, docs.litellm.ai, 30 Jul 2026]. This resolves
  what litellm is *for* in this stack - plumbing to let every other
  component (open-webui, n8n, HA) speak one API dialect to Lemonade, useful
  if more than one of them needs to reach 252, but it doesn't change any
  capability finding above.

**Standing observation, same shape as §7:** the project has been building
bespoke Python against HA's private internals while two general-purpose,
already-running, actively-maintained AI platforms (open-webui, n8n) sit in
the same infra pod with native tool-calling and RAG built in. This wasn't
found earlier because the sweep so far checked HA-side integrations and
open-source projects the custom code talks *to* (Paperless, Frigate), not
the AI tooling already running *alongside* it.

### 11.3 Tier 3 — alternatives to already-planned or already-found work

- **Face recognition alternatives to `llmvision`'s face-recognition angle:**
  `jakowenko/double-take` (unified UI over multiple detectors - DeepStack,
  CompreFace, Facebox), `CompreFace` (single-detector, offline, lower setup
  burden per a March 2026 comparison), `CodeProject.AI` (free, self-hosted,
  has its own Frigate detector config path) [V, various, 30 Jul 2026]. None
  of these do what `llmvision`/`home_generative_agent` do beyond face
  recognition specifically - relevant only if face-recognition accuracy
  from `home_generative_agent`'s built-in face-rec (§9.1) proves
  insufficient once tested. Not an action item now.
- **Long-term memory alternatives to `home_generative_agent`'s built-in
  Postgres+pgvector memory:** `mem0` (lightweight memory layer, bolt onto
  any agent framework, 48K+ GitHub stars) and `letta`/formerly MemGPT (full
  stateful-agent framework, tiered core/recall/archival memory, 23K+ stars)
  [V, vectorize.io comparison, atlan.com, 30 Jul 2026]. Same status as
  above - only relevant if `home_generative_agent`'s own memory layer is
  tested and found wanting. Not an action item now.

### 11.4 Tier 4 — confirms existing direction, changes nothing

Community 2026 consensus names **Ollama** as "the standard local host" for
HA local-AI builds [V, botmonster.com, 30 Jul 2026] - this is the generic
default other guides assume, and it is not what this project uses.
Confirms, doesn't challenge, the project's own documented reason to diverge
(NPU-hosted Lemonade on dedicated hardware vs. Ollama's CPU/generic-GPU
default) - worth recording so a future reader doesn't mistake Ollama's
popularity for a reason to reconsider Lemonade. Wyoming/faster-whisper/Piper
again confirmed as the same stack already built; nothing new surfaced here
this pass either.

---

## 10. What still needs Jason, not more searching

- **Added this pass, now the actual first diagnostic - everything else in
  this list is downstream of it:** HA core version against 2026.6.0/
  2026.7.4 (§11.1 - gates whether `mcp`/`mcp_server` are even available),
  and whether open-webui or n8n (§11.2) can be pointed at Paperless and
  Lemonade to do what `paperless.py` has been hand-building all session.
  If either can, the right next step is configuring them, not writing more
  Python against HA's private internals. This should be checked before
  §9's `home_generative_agent`/`llmvision` diagnostic below, not after -
  it's a cheaper, faster test (does open-webui already read a test
  document correctly) and it bears on whether custom code is the right
  shape at all, which the §9 diagnostic assumes.
- §1's diagnostic (paperless-ngx version + `PAPERLESS_AI_*` env vars) -
  gates whether any of today's `paperless.py` work should continue as
  built or be replaced.
- Confirming which Lemonade version actually shipped Kokoro streaming
  support, and whether `sfortis/openai_tts` or an alternative HA
  integration can reach it (§3) - gates the single largest documented
  latency opportunity in the voice pipeline that hasn't been tested.
- A real side-by-side test of Phi-4-Mini-Instruct against Gemma 4 E4B on
  this hardware, using real multi-turn tool sequences (§2) - the project's
  own Document Standard already warns against trusting the benchmark
  citations in that table as-is.
- **Highest priority of the three, added this pass:** whether
  `home_generative_agent` and `llmvision` (§9.1), already installed and
  unconfigured, can be pointed at Lemonade/252 and the infra pod's
  Postgres as they stand. This gates whether continued build-out of
  `abode_tools`/`abode_autonomy` is still the right shape at all, or
  whether it should become configuration and gap-filling against two
  already-installed components instead. Diagnostic: read
  `home_generative_agent`'s and `llmvision`'s actual config flow and
  source (not README) against this stack's specific requirements -
  Paperless retrieval, Homebox, the single-household latency principle -
  and report what's missing, not what's claimed.

---

## 12. Web search for Function 2 (voice BAU queries) — new scope, first pass

Introduced this session only after the architect's correction that
Function 2 (voice, beyond device control) includes web search, not just
household-record lookup. Not previously researched anywhere in this
document. First pass only - not a recommendation yet:

- **`skye-harris/llm_intents`** - a HACS custom_component that explicitly
  "exposes internet search tools for use by LLM-backed Assist in Home
  Assistant" [V, GitHub, 30 Jul 2026]. The most directly on-point find -
  purpose-built for exactly this gap. Not read past the one-line
  description; needs an actual look at what search backend it uses and
  whether it's still maintained.
- **Brave Search API** - community pattern for wiring a conversation
  agent to Brave's API directly (summarized, snippet-rich results; $5/mo
  free tier ≈ 1000 searches) [V, community forum, 30 Jul 2026]. A paid
  cloud dependency, which cuts against this build's local-only principle
  unless usage is small enough that occasional-BAU-question volume stays
  inside a household's real usage pattern.
- **Google Gemini Conversation's built-in Google Search tool** - HA's own
  `google_generative_ai_conversation` integration can enable Google Search
  as a tool [V, home-assistant.io, 30 Jul 2026], but **the same source
  notes an API limitation: Google's Search tool cannot be used together
  with other tools in the same call.** That's a real constraint, not a
  footnote - a Function 2 conversation turn that needs both Paperless
  lookup and web search in the same exchange would not work through this
  path.
- **Not yet checked:** whether `home_generative_agent`'s own tool
  architecture (§9.1, §11.1) could take a web-search tool as just another
  LangChain tool alongside `upsert_memory` and the rest - this would avoid
  the single-tool-only constraint above and keep Function 2 inside the
  same conversational agent already being evaluated for document
  retrieval. This is the natural next question, not yet answered.
