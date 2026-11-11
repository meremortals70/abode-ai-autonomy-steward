# Migration Plan: Ollama → llama.cpp (llama-server) on `intranet`

Version 1.1 — 2026-10-08 — status: **APPROVED by Jason; Phase 0 next.** Nothing has been changed yet.

**Decisions (Jason, 2026-10-08):** D1 Option C · D2 floating tag, build recorded · D3 official Qwen GGUF if it ships mmproj, same quant as today · D4 keep separate task model · D5 drop qwen3-vl:8b if T8 passes · **D6 drop the `ollama.meremortals.au` FQDN entirely (no replacement name): remove the Caddy site, the Pulse monitor and the DNS record** · D7 bind 127.0.0.1, no Caddy publishing · D8 top_k = 20 · D9 14-day rollback window · **D3 revised:** no official Qwen GGUF exists → **bartowski/Qwen_Qwen3.5-9B-GGUF** `Qwen_Qwen3.5-9B-Q4_K_M.gguf` (6.17 GB) + `mmproj-Qwen_Qwen3.5-9B-f16.gguf` (918 MB) · **D10:** remove **n8n** (backup DB + quadlet first) in Phase 4 · **D11:** **disable LiteLLM** (stop, keep quadlet/config/DB, not started on boot) in Phase 4 — do not delete.

## Phase 0 findings (2026-10-08, confirmed from output)
- GPU RTX 4060 Ti 16,380 MiB; driver **550.163.01 / CUDA 12.4** (Debian stock, pinned). Image built with CUDA 12.8.1 → relies on NVIDIA minor-version compatibility (driver ≥ 525; no PTX JIT) → **Phase 1 test 1 decides**; fallback = local build `CUDA_VERSION=12.4.x`, `CUDA_DOCKER_ARCH=89`.
- Ollama models: qwen3.5:9b Q4_K_M (vision, 9.3 GB @98304), llama3.2:3b Q4_K_M (4.1 GB @16384), nomic-embed-text F16 (768-dim, ctx 2048, 323 MB), qwen3-vl:8b Q4_K_M (not loaded).
- Consumers: Open WebUI (`ollama.base_urls`, `rag.embedding_engine=ollama` / `nomic-embed-text`, `task.model.default=llama3.2:3b-instruct-q4_K_M`, `mm-assistant` base `qwen3.5:9b`, quadlet `After=`/`Wants=ollama.service`); Paperless (quadlet lines 11–18); Mealie (quadlet lines 34–37: `OPENAI_BASE_URL`, key, `OPENAI_MODEL=qwen3-vl:8b`, image services on); Caddy (`caddy.json` line 188, `ollama.meremortals.au`); `ollama-preload.service`; LiteLLM `config.yaml` (being disabled). Not consumers: n8n (no Ollama/OpenAI creds or workflows), Nextcloud (no appconfig refs).
- Network: `infra.pod` = `Network=pasta:-t,80,-t,443` → only 80/443 reach the LAN; 11434 was never directly exposed. Pulse's "192.168.89.222" in the Ollama log is the X-Forwarded-For from Caddy (Pulse → https://ollama.meremortals.au). No other client IPs in the log window (since 2026-10-07 06:07). Caddy has no access log; its 7 lines for the FQDN are ACME renewal-info only.
- Free ports in the pod: **8090 chat, 8091 task, 8092 embed** (bind 127.0.0.1).
- Disk: 3.1 TB free on /mnt/data.

## Phase 1 progress
- **Image:** `ghcr.io/ggml-org/llama.cpp:server-cuda` pulled — llama.cpp **build 11459 (commit f498f864f)**, 0.6.0-dev.
- **CUDA error 804 found and resolved:** the image ships CUDA forward-compat `libcuda 570.124.06` in `/usr/local/cuda-12.8/compat`, registered first in the loader cache (`/etc/ld.so.conf.d/00-compat-*.conf`, sorts before CDI's `00-nvcr-*.conf`). Forward compat is data-centre-GPU only → "forward compatibility was attempted on non supported HW". **Fix (no image change): `Environment=LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/nvidia/current:/usr/local/cuda/lib64`** in every llama-* quadlet → libcuda = host 550.163.01; `--list-devices` shows `CUDA0: NVIDIA GeForce RTX 4060 Ti (16076 MiB)`. GPU passed as in ollama quadlet: `AddDevice=nvidia.com/gpu=all`, `SecurityLabelDisable=true`. Remaining check in Phase 2: model load + compute on GPU (no PTX JIT errors); fallback = local build with CUDA 12.4 / arch 89.
- **Model files (to download):** bartowski `Qwen_Qwen3.5-9B-Q4_K_M.gguf` (6.17 GB) + `mmproj-Qwen_Qwen3.5-9B-f16.gguf` (918 MB); bartowski `Llama-3.2-3B-Instruct-Q4_K_M.gguf` (2.02 GB); nomic-ai `nomic-embed-text-v1.5.f16.gguf` (274 MB). Verified against Hugging Face sha256.

---

## 1. Why (evidence from 2026-10-08)

| # | Problem | Evidence | Fixed by migration? |
|---|---|---|---|
| 1 | Full prompt re-processed every round (25–27k tokens, 10–13 s per round) | Ollama 0.34.0 log: "forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent memory)" | **Partly.** Same llama.cpp engine underneath, but llama-server exposes the checkpoint/cache controls Ollama hides (`--checkpoint-min-step`, `--ctx-checkpoints`, `--cache-reuse`, `--cache-ram`) and `LLAMA_SERVER_SLOTS_DEBUG=1` to see exactly which tokens changed. |
| 2 | Open WebUI drops the system prompt on every tool-call follow-up | tcpdump capture; Open WebUI #30161 / fix PR #30375 (merged to `dev`, unreleased). The fix only touches the `owned_by == 'ollama'` path. | **Unknown — must be proven in the pilot (Phase 2, test T2).** The OpenAI-compatible path is different code; not yet verified. |
| 3 | Paperless AI: `think=False` turned into `None` by llama-index-llms-ollama 0.11.0 → qwen3.5 thinks → 2–3+ min per suggestion | Bug report Jason filed | **Yes, if confirmed in T6.** Paperless switches to its `openai-like` backend; thinking is disabled server-side per model. |
| 4 | Ollama-specific workarounds that silently break | `num_ctx` lost on `ollama pull` (re-`ollama create` needed); `PAPERLESS_AI_LLM_CONTEXT_SIZE` must equal num_ctx or Ollama reloads; ollama-preload unit; context default overrides | **Yes.** Each llama-server instance has a fixed, explicit config in its quadlet. |
| 5 | Hidden model swapping / VRAM surprises (qwen3-vl evicts the chat model) | Handover 10-07 | **Yes**, with fixed per-model instances (design below). |

Not caused by Ollama (stays on the list regardless): 69 tools / 45 KB tool JSON per request (HA tool exposing internal helpers), `KeyError: 'model'` title bug (#30339), top_k = 420.

---

## 2. Target architecture (recommended: **Option C — one llama-server container per model**)

All containers in `infra.pod` (shared localhost), GPU via CDI exactly like the current ollama quadlet, rootless, quadlets in `~/.config/containers/systemd/`, models in `/mnt/data/volumes/llama/models/`.

| Instance (quadlet) | Model | Role | Key settings (to finalise in Phase 1) | Est. VRAM |
|---|---|---|---|---|
| `llama-chat` | Qwen3.5-9B GGUF (+ mmproj for vision) | Open WebUI chat, Paperless AI, Mealie (incl. image) | `--alias qwen3.5-9b`, `-c 98304`, `-ngl all`, `-np 1`, thinking off, `--jinja`, `--checkpoint-min-step` lowered, `--metrics` | ~9.3 GB + mmproj (~1 GB, verify) |
| `llama-task` | Llama-3.2-3B-Instruct Q4_K_M | Open WebUI task model (titles, tags, follow-ups) | `--alias llama3.2-3b`, `-c 16384` | ~4 GB |
| `llama-embed` | nomic-embed-text v1.5 GGUF | Open WebUI RAG + Paperless LLM index | `--embeddings`, `-c 2048`, batch ≥ chunk size | ~0.3 GB |
| *(dropped)* | qwen3-vl:8b | was Mealie vision | replaced by Qwen3.5-9B's own vision (Qwen3.5 is multimodal — verify mmproj file exists for the chosen GGUF) | 0 |

Total ≈ 14.5–15.5 GB of 16.4 GB — same envelope as today, but **fixed**: no eviction, no reload when a client sends a different context size.

Endpoints (ports to be confirmed free in Phase 0): `http://localhost:<chat>/v1`, `http://localhost:<task>/v1`, `http://localhost:<embed>/v1`. Health: `GET /health` (200 when ready, 503 while loading).

### Alternatives considered

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. llama-server router mode** (`--models-preset`, one endpoint, LRU) | Single upstream project, one URL | Router "counts models, not gigabytes"; LRU eviction on a 16 GB card; concurrent requests can exceed `--models-max` (llama.cpp #20137); newer feature | Not recommended for a 3-model always-on set |
| **B. llama-swap** (Go proxy in front of llama-server) | One URL, TTL, preload hooks, `matrix` for concurrency | Third-party component to maintain; another layer to debug | Fallback if one URL becomes important |
| **C. One container per model** (recommended) | Deterministic VRAM; each piece testable alone (matches "one component at a time"); plain quadlets like the rest of the stack; restart one model without touching the others | Three URLs instead of one; three units | **Recommended** |

---

## 3. Decisions needed from Jason (before Phase 1)

| # | Decision | Recommendation |
|---|---|---|
| D1 | Architecture A / B / C | C |
| D2 | Image tag: floating `ghcr.io/ggml-org/llama.cpp:server-cuda` (house rule: floating tags) vs pinned build tag | Floating, record the build number (`llama-server --version`) in the as-built; note llama.cpp docs say GPU images are "not currently tested by CI beyond being built" |
| D3 | GGUF source for Qwen3.5-9B: official Qwen repo vs Unsloth; quantisation (match today's Ollama quant) | Official Qwen GGUF if it ships an mmproj; same quant as today so quality comparison is fair |
| D4 | Keep a separate task model (llama3.2-3B) or use the chat model for tasks | Keep separate — keeps the chat slot's cache clean |
| D5 | Drop qwen3-vl:8b; Mealie image recognition via Qwen3.5-9B vision | Drop, if test T8 passes |
| D6 | `ollama.meremortals.au` in Caddy/Pulse: rename (e.g. `llm.meremortals.au`) or remove | Decide; Pulse monitor must follow |
| D7 | API key on llama-server instances (they bind inside the pod; LAN exposure only via Caddy) | Bind to 127.0.0.1; key only if published through Caddy |
| D8 | `top_k` 420 vs 20 (set once in the new model config) | 20 (Qwen's non-thinking recommendation) — Jason to confirm |
| D9 | Rollback window before deleting Ollama + its models | 14 days |

---

## 4. Phases

Each phase ends with Jason confirming from pasted output. One component at a time. Backups stated before they are made. `systemctl --user stop` → verify → `start` (never `restart`).

### Phase 0 — Inventory and pre-checks (read-only)
- Every consumer of Ollama: quadlets, Open WebUI (`ollama.*` config keys, model `base_model_id`s, task model, RAG embedding engine), Paperless, Mealie (group AI provider in Mealie DB/UI), n8n (credentials/workflows using Ollama), Caddy (`ollama.meremortals.au`), Pulse, ollama-preload, anything else on 11434.
- Free ports in the infra pod netns.
- NVIDIA driver version vs the image's CUDA 12.8 runtime (Debian Trixie stock driver is pinned by decision — must confirm compatibility before anything else).
- Current Ollama model quantisations and sizes (for D3) and `ollama ps` VRAM baseline.
- Disk space under `/mnt/data/volumes/` for GGUFs.
- Diagnostics: §6.

### Phase 1 — Prepare (no service impact)
1. Pull image (with Jason's OK). Record `llama-server --version`.
2. Download GGUFs (+ mmproj) into `/mnt/data/volumes/llama/models/` and checksum them.
3. Write the three quadlets (`llama-chat`, `llama-task`, `llama-embed`), **not started**. Each flag verified against the README of the pulled build.
4. Backups: `~/quadlet-backups/ollama.container.<date>`, `ollama-preload.service`, Open WebUI `config` + `model` tables (pg_dump), Paperless quadlet, Mealie AI provider settings.

### Phase 2 — Pilot (short maintenance window; Ollama stopped, rollback = stop llama-*, start ollama)
VRAM cannot hold both stacks, so the pilot runs in a window:
1. Stop `ollama-preload`, stop `ollama`, verify stopped, confirm VRAM free (`nvidia-smi`).
2. Start `llama-chat`, then `llama-task`, then `llama-embed` — one at a time, logs grepped for errors/warnings after each, `/health` = 200, VRAM recorded.
3. In Open WebUI add an **OpenAI connection** `http://localhost:<chat>/v1`, Auth None, Provider `llama.cpp` (Admin Panel → Settings → Connections → OpenAI → Add Connection → Advanced → Provider). Create a *test* Workspace model on it (copy of mm-assistant with the new base model id) — the production model is untouched.
4. Run acceptance tests (§5). Any FAIL → stop llama-*, start ollama, analyse.

### Phase 3 — Cutover (one consumer at a time, each confirmed before the next)
1. **Open WebUI chat:** re-point `mm-assistant` to the new base model (JSON export/import as before), set default, remove Ollama connection afterwards.
2. **Open WebUI task model** → llama-task.
3. **Open WebUI RAG embeddings** → OpenAI engine `http://localhost:<embed>/v1` (Admin Panel → Settings → Documents). Knowledge base for the as-builts is created **after** this, so no re-index is needed.
4. **Paperless:** `PAPERLESS_AI_LLM_BACKEND=openai-like`, `PAPERLESS_AI_LLM_ENDPOINT=http://localhost:<chat>/v1`, model = alias, `PAPERLESS_AI_LLM_EMBEDDING_BACKEND=openai-like`, `PAPERLESS_AI_LLM_EMBEDDING_ENDPOINT=http://localhost:<embed>/v1`, `PAPERLESS_AI_LLM_EMBEDDING_MODEL=<alias>`, API key placeholder (backend "typically requires" one), context size, chunk size ≤ embed ctx. Then `document_llmindex rebuild` (embeddings change source → full rebuild). Timeout back toward default once T6 passes.
5. **Mealie:** group AI provider base_url → `http://localhost:<chat>/v1`, any non-empty key, model alias; image provider same.
6. **n8n / others** found in Phase 0.
7. **Drop `ollama.meremortals.au` (D6):** remove the site from Caddyfile + caddy.json (single-file bind mount, edit in place; stop/verify/start caddy, no reload); delete the Pulse monitor; Jason removes the DNS record. Done only after Ollama has no consumers left.

### Phase 4 — Decommission
- Ollama: stop, `systemctl --user disable` equivalent for quadlet (move quadlet to `~/quadlet-backups/…removed-<date>`), daemon-reload. Remove `ollama-preload.service`.
- Keep Ollama image + models for the rollback window (D9), then remove.
- **n8n (D10):** pg_dump `n8n` DB to `~/db-backups/`, quadlet to `~/quadlet-backups/…removed-<date>`, stop, remove unit; Caddy site (if any) removed per house rules.
- **LiteLLM (D11):** stop, verify stopped, move quadlet out of the systemd dir to `~/quadlet-backups/litellm.container.disabled-<date>` (keeps config + DB; re-enable = move back + daemon-reload).
- Close obsolete open items: OLLAMA_DEBUG cleanup, ollama-preload GPU-after-reboot check, Paperless `think` bug workaround, num_ctx Modelfile notes.

### Phase 5 — Documentation
- As-built for the LLM layer (instances, flags, ports, model files + checksums, build number, consumers), handover update. Then the as-built knowledge base (open item) is built on the new embeddings.

---

## 5. Acceptance tests (pilot, Phase 2)

| ID | Test | Pass criterion |
|---|---|---|
| T1 | Each instance starts cleanly | `/health` 200; no unexplained ERR/WARN in logs; VRAM total ≤ ~15.5 GB with all three loaded |
| T2 | **System prompt on tool follow-ups** — same tcpdump capture + `ollama_prompt_diff.py` (port changed to the chat port) | System message present in every request; leading messages identical between consecutive requests |
| T3 | **Cache reuse** with `LLAMA_SERVER_SLOTS_DEBUG=1` | Follow-up rounds restore a checkpoint / process only new tokens (prompt tokens per follow-up ≪ total) |
| T4 | Tool calling: UniFi, Paperless, Homebox, HA in one chat | All four answer correctly; no HTTP 500 "Failed to parse input" (known Qwen3.5 tool-call parser reports, llama.cpp #20761) |
| T5 | Thinking off | No reasoning block; `reasoning_tokens` 0 (known report that `--chat-template-kwargs` was ignored, llama.cpp #20409 — use the switch verified for the pulled build) |
| T6 | Paperless "Suggest" on one document | Result in well under today's ~2 m 40 s; correct fields |
| T7 | Embeddings | Open WebUI test doc retrieval works; Paperless index rebuild completes without errors |
| T8 | Mealie recipe from a photo | Works with Qwen3.5-9B vision (else keep a vision instance → revisit VRAM) |
| T9 | Latency | Your 10-second requirement on the same UniFi + Paperless test as today (baseline: ~19 s and ~40 s total) |
| T10 | Reboot test (after cutover) | All three instances start on boot, on GPU, before consumers need them |

---

## 6. Phase 0 diagnostics (read-only — next step)

```bash
# 1. GPU driver / CUDA
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv
nvidia-smi | head -5

# 2. Current Ollama models: quantisation and size
podman exec ollama ollama list
for m in qwen3.5:9b llama3.2:3b-instruct-q4_K_M nomic-embed-text qwen3-vl:8b; do echo "== $m"; podman exec ollama ollama show "$m" | grep -iE 'architecture|parameters|quantization|context length|embedding length|vision|projector'; done
podman exec ollama ollama ps

# 3. Who references Ollama (quadlets, names only + URL lines; secrets filtered)
grep -nE '11434|ollama' ~/.config/containers/systemd/*.container ~/.config/containers/systemd/*.pod 2>/dev/null | grep -viE 'key|token|pass|secret'
ls ~/.config/systemd/user/ | grep -i ollama
grep -n '11434' /mnt/data/volumes/caddy/caddy.json | head

# 4. Open WebUI: Ollama-related config keys and models on Ollama
podman exec -i postgres psql -U admin -d webui -At -c "select key, left(value::text,200) from config where key ilike 'ollama%' or key ilike 'rag.embedding%' or key ilike 'task%' order by key;"
podman exec -i postgres psql -U admin -d webui -At -c "select id, base_model_id from model order by id;"

# 5. Databases present (to find n8n / mealie)
podman exec -i postgres psql -U admin -At -c "select datname from pg_database where not datistemplate;"

# 6. Ports already listening inside the infra pod
P=$(podman inspect -f '{{.State.Pid}}' ollama)
podman unshare nsenter -t "$P" -n ss -ltn | sort -k4

# 7. Disk space for models
df -h /mnt/data
```

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Open WebUI drops the system prompt on the OpenAI path too | T2 decides before cutover. If it does, cutover still gives cache controls, and the Open WebUI release (PR #30375 or equivalent) is still awaited. |
| Qwen3.5 tool-call parsing / thinking-switch bugs in llama.cpp (#20761, #20837, #20409) | T4/T5 in the pilot on the exact build pulled; floating tag means re-test after updates |
| CUDA runtime in image newer than the pinned Debian driver supports | Phase 0 check #1 before pulling anything |
| Embedding vectors differ from Ollama's nomic → existing Paperless index invalid | Full `document_llmindex rebuild` (453 docs ≈ 45 s today); Open WebUI KB built after cutover |
| VRAM over-commit | Fixed instances; T1 measures; ctx sizes explicit |
| Downtime of Paperless AI / Mealie AI / Open WebUI during pilot | Short window, tested rollback (stop llama-*, start ollama) |

---

## 8. Sources
- llama-server README (flags, endpoints, env vars): https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- llama.cpp Docker images: https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md
- llama.cpp model management / router mode: https://huggingface.co/blog/ggml-org/model-management-in-llamacpp
- llama.cpp #20225 (Qwen3.5 full re-processing), #20153, #20761 (tool parse 500), #20837, #20409 (thinking switch)
- llama-swap: https://github.com/mostlygeek/llama-swap
- Open WebUI — connect llama.cpp: https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-llama-cpp
- Open WebUI #30161 / PR #30375: https://github.com/open-webui/open-webui/issues/30161
- Paperless-ngx AI configuration (`openai-like` backend): https://github.com/paperless-ngx/paperless-ngx/blob/dev/docs/configuration.md
- Mealie AI providers: https://mealie.io/documentation/getting-started/installation/ai-providers/
