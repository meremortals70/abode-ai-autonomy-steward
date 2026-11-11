# Lemonade NPU/GPU Consolidation — Architecture Plan (Draft)

**Status:** Planning only. Nothing below has been executed. Work paused for the night per Jason — resume with the diagnostic commands in Section 5 before touching any config.

**Date:** 2026-07-24

---

## 1. Decision: Consolidate to a Single Lemonade Instance

**Current state:** Two separate LXCs, each running its own Lemonade server:
- `lemonade-npu` — FastFlowLM backend, serves the NPU
- `lemonade-gpu` — llama.cpp backend, serves the GPU

**Target state:** One Lemonade instance, hosted in the `lemonade-gpu` LXC, using Lemonade's Router to send different models to different backends concurrently — FastFlowLM for NPU-tagged models, llama.cpp for GPU-tagged models — all behind one OpenAI-compatible API/port.

**Why:** Lemonade natively supports running models across NPU, GPU, and CPU simultaneously from one server process, limited only by RAM. There's no need for two separate instances/ports to get both accelerators working at once — that was solving a problem Lemonade already solves internally.

**Mechanics of the change:**
- `lemonade-npu` LXC: shut down, autostart disabled. **Not deleted yet** — kept in place until the new architecture is proven stable.
- RAM freed from `lemonade-npu` reallocated to `lemonade-gpu`.
- NPU device passthrough (`/dev/accel/accel0` or equivalent) added to `lemonade-gpu`'s LXC config — this is a separate device grant from GPU passthrough and does not exist there today.

---

## 2. Workload Split (once consolidated)

### NPU (FastFlowLM backend, inside the single Lemonade instance)

**Task:** Frigate GenAI scene/object description only. Not latency-critical — it's background enrichment on review items, not a live conversation.

**Recommended model:** `gemma3:4b` (FastFlowLM tag; base model `google/gemma-3-4b-it`, Q4_1 quantization) — **not yet pulled or tested.**
- Rationale: published NPU dataflow benchmarks show large measured gains for this model family on this exact hardware class (up to 7.5× faster prefill, 5.9× faster decode vs iGPU) — a genuine architectural fit, not just "free capacity."
- Recommended `--ctx-len`: ~4096. Single-image scene description prompts run well under 1-2K tokens (Gemma3's vision encoder produces ~256 tokens per image); no need for the 64K default.
- Fallback to test if description quality falls short: `Qwen3-VL-4B` / `Qwen3.5-VL-4B` (also has an NPU2 build; Frigate's own docs use `qwen3-vl:4b` as their reference Ollama example).
- Frigate config shape (once a model is loaded):
  ```yaml
  genai:
    provider: openai
    base_url: http://<consolidated-lemonade-ip>:<port>/v1
    model: gemma3:4b
    provider_options:
      context_size: 4096
  ```

**Why NPU only handles this one workload:** FastFlowLM's NPU backend can only hold **one LLM loaded at a time**. Giving it a second concurrent job (e.g. voice) would cause constant eviction/reload thrashing. Keeping NPU single-purpose avoids that entirely.

Object detection stays on the Hailo-8 — separate accelerator, untouched by any of this.

### GPU (llama.cpp backend, inside the single Lemonade instance)

**Task:** Everything else — Tara assistant, HA voice/conversation agent (tool-calling), whole-home autonomous reasoning over sensors/presence, general conversational AI.

**Model:** One single model serves all GPU-side roles — Tara, HA voice/conversation agent, and whole-home reasoning all point at the same loaded model, rather than separate models per role. **Confirmed: Gemma 4 26B-A4B (MoE)** — the model already established for whole-home reasoning. Verified this is well-supported on the GPU/llama.cpp path (official llama.cpp support since April 2026 launch, native function-calling support, and multimodal/vision input via a companion mmproj file if ever needed) — distinct from the NPU/FastFlowLM path, which does not yet support this model. Only 4B parameters active per token despite 26B total, so it runs closer to 4B-class speed while carrying MoE-level quality — a good fit for a single model covering reasoning, tool-calling, and general conversation at once.

**Why voice/reasoning moves off NPU onto GPU:**
- Avoids the NPU single-LLM-slot conflict above.
- Real-world NPU-via-FastFlowLM decode throughput on this hardware class has been measured in the low tens of tokens/sec range for dense conversational models — GPU decode is typically faster for this workload type, so this move plausibly *improves* voice latency rather than costing it.

**Conversation agent architecture:** `mcp-assist` (HACS) is the recommended replacement for the current HA conversation agent (`hass_local_openai_llm`) — **not yet installed or wired.** It replaces full entity dumps (12,000+ tokens/request) with on-demand entity discovery (~400-800 token index), which is the actual fix for the original "every entity sent every request" problem. Still needs real multi-step tool-calling tests on real hardware before being called working — token-cost fix is confirmed, model-capability fix is not.

---

## 3. Dependent Systems Requiring Reconfiguration

- **Tara assistant** — currently points at `lemonade-npu`'s endpoint/port. **Must be repointed** to the new consolidated Lemonade instance (on `lemonade-gpu`) and to whichever model tag actually ends up loaded there. If `lemonade-npu` is shut down before this repoint happens, Tara breaks.
- **Full audit complete:** Tara is the only system pointing at `lemonade-npu`. No other consumers to repoint.

---

## 4. Explicitly Open / Not Yet Decided

- ~~Exact GPU model~~ — **Confirmed: Gemma 4 26B-A4B (MoE)**, serving all three GPU-side roles.
- ~~Full audit of other `lemonade-npu` consumers~~ — **Confirmed: Tara is the only consumer.** No further audit needed.
- `mcp-assist` installation and endpoint config — not started.
- Whether the old NPU voice model (`qwen3-it-4b-FLM`) is retired entirely or repurposed somewhere.
- Real RAM headroom on `lemonade-gpu` once it's carrying NPU passthrough + the Frigate vision model + the existing GPU reasoning model all at once — not calculated.
- Whether the host's `amdxdna` NPU driver is actually healthy under the currently-pinned Proxmox kernel (6.17.13-14-pve) — that kernel pin was chosen for an unrelated nvidia DKMS conflict, and hasn't been checked against NPU driver compatibility.

---

## 5. Diagnostics Needed Before Any Execution

Run these on the Proxmox host before making any config changes:

```bash
# Confirm real container IDs and current device grants
cat /etc/pve/lxc/<lemonade-npu-id>.conf
cat /etc/pve/lxc/<lemonade-gpu-id>.conf

# Confirm NPU device is present and healthy on the host
ls -l /dev/accel/
uname -r
dmesg | grep -i xdna
```

---

## 6. Execution Order (once resumed)

1. Run Section 5 diagnostics.
2. Add NPU device passthrough lines to `lemonade-gpu`'s LXC config, mirroring `lemonade-npu`'s working grant exactly.
3. Increase `lemonade-gpu`'s RAM allocation.
4. Start `lemonade-gpu`, confirm the NPU is visible and functional inside the container (FastFlowLM validation).
5. Pull/load `gemma3:4b` on the NPU side of the consolidated instance; test against Frigate GenAI.
6. Decide and confirm the GPU model for voice/reasoning; wire up `mcp-assist`.
7. Repoint Tara assistant to the new consolidated endpoint + model.
8. Only after full verification of all of the above: stop `lemonade-npu`, disable autostart (`pct set <id> --onboot 0`). Leave the LXC in place, don't delete.
9. Once the new architecture has proven stable over time: decommission/delete `lemonade-npu`.
