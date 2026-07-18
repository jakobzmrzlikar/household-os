# Fable Mission Brief — On-Device Runtime Feasibility: Spike Harness + Quant Explorer (#6)

> **Audience:** Claude Fable 5, in Claude Code inside this repo.
> **Human owner:** Jakob. **Judgment/taste calls:** the human (with Opus).
> **Relationship to other briefs:** this is the **#6 on-device** work that `docs/fable-briefs/workstream-b-finetune.md` Stage 5 points toward ("go/no-go note toward #6"). That brief explicitly scoped out mobile runtime; this brief owns it. No fine-tuned model is required to start (see §1 stock-proxy principle).
> **This brief is the source of truth. Read it fully before acting.**

## 0. How to operate (read first)

1. **Read before building:** this brief; `CLAUDE.md`; `docs/adr/0004` (tooling), `0005` (hex — relevant for where code may NOT go), `0008` (pytest); and skim `docs/fable-briefs/workstream-b-finetune.md` so you reuse its GGUF/quantize artifacts rather than duplicating them.
2. **Plan first, then stop.** Propose a staged plan mapped to §5, then **wait for approval**.
3. **HITL / checkpointed mode.** Run with per-stage pauses. Stop at every `[HUMAN DECISION]` and at every `[HUMAN — DEVICE]` step (the human physically operates the phone). The human may be steering from a phone — ask **one concise question at a time** with a recommended default.
4. **Self-test** any Python that lands in the repo, from its own env (see §4): `ruff check --fix ./`, `ruff format ./`, and `pytest` for harness parsing/logic. Bench tooling is a separate env — keep its deps out of `backend/`.
5. **Escalate judgment, don't guess** on `[HUMAN DECISION]` items (stack/transport, target devices, model set).

## 1. Why this exists

Desk research (product vault, summarized here so this brief is self-contained) green-lit on-device 1–3B inference on paper for everything **except three device-specific unknowns** that only physical hardware can answer. This brief converts those three unknowns into measured numbers, and picks the best on-device inference config.

**The three open gaps to close (the whole point):**
1. **Sustained decode tok/s** for a 3B Q4 model on the pessimistic floor device (weak, CPU-bound older SoC) — no public benchmark exists for that chip class.
2. **Thermal throttling curve** under a sustained multi-turn agentic session on a small thermal envelope.
3. **Battery drain** per realistic in-trip session on that device.

**Stock-proxy principle (load-bearing — why we are NOT blocked by fine-tuning):** LoRA fine-tuning and quantization do not change parameter count, architecture, or inference compute, so a **stock** 3B Q4 model is a **near-exact proxy** for the physical gates. Judge results on **speed / thermal / battery only**; treat answer *quality* as directional. If the fine-tune brief has already produced a merged+quantized GGUF, prefer it — but it is **not a prerequisite**.

**Design rule that falls out of the data:** target **bursty, short inferences** (system prompt + tool context in, short answer out), not long on-device reasoning chains. Benchmark that shape.

## 2. Objective & definition of done

- **`explore/`** — a device-independent quantization/config explorer that ranks quant formats + KV-cache strategies + context-length costs and recommends **one** on-device config. Runs entirely on the dev machine; **no phone needed** (do this first).
- **`bench/`** — a reproducible on-device harness (+ prepared device scripts) that measures the three gaps, plus tooling to parse logs into a results schema and plots.
- **Done =** both built, committed, reproducible from a `README`; explorer emits a single recommended config; harness produces (for at least the floor device) steady-state 3B decode tok/s, throttle knee, peak temp, sustained watts, and %/min battery; a `FINDINGS.md` converts the three gaps to measured values (or clearly documents the blocker). No production runtime built (§3).

## 3. Scope guardrails (non-goals)

- **No production router, no on-device/cloud handoff, no MLOps lifecycle, no app/UI.** This is the feasibility/technical-depth layer only.
- **No fine-tuning** — that is the other brief. Use a stock (or the already-produced) model.
- Do **not** modify `frontend/` or the `backend/` app. Bench/explore tooling is a **separate top-level env** (§4) — do not leak its deps into the 3.14 backend, and do not route it through the hexagonal app layers.
- **Model weights & GGUF files are NOT committed** — gitignore them; keep only scripts, configs, small metadata, and results.

## 4. Architecture & placement

Two decoupled tool directories, each self-contained; nothing heavy touches the FastAPI app.

- **`explore/` and `bench/` as new top-level tool dirs**, mirroring how `training/` is kept separate. Give the Python its **own `uv` env + ruff/basedpyright config**; pin Python to whatever the tooling supports (llama.cpp Python bindings / plotting are undemanding, but do not force the backend's 3.14 if a dep objects). `[HUMAN DECISION]` — confirm dir names and that a separate env is preferred over folding into `training/`.
- **Runtime = `llama.cpp`** (broadest compat, GGUF, ARM KleidiAI CPU kernels — best fit for a CPU-bound floor device). It ships `llama-bench`, `llama-cli`, `llama-perplexity` — use them; don't reinvent measurement.
- **On-device transport = `adb`** over USB (or Termux on-device). `[HUMAN DECISION]`. Harness prepares exact commands; a human runs the on-device steps.
- **Reuse, don't duplicate:** if `training/` already produces quantized GGUFs, consume them; otherwise download stock GGUFs. Document fetch commands; gitignore the files.

## 5. Staged plan (implement in order, pause after each)

**Stage 0 — Confirm & scaffold.** Propose repo layout; confirm stack/transport, target devices (floor + ceiling, or floor-only for now), HF token, and model set. `[HUMAN DECISION]`. *DoD:* dirs + envs scaffolded, `README` skeleton, lint/test green.

**Stage 1 — Quant/config explorer (`explore/`, no phone — do first).** For the 3B model:
- **Quant sweep:** build/fetch `Q3_K_M, Q4_0, Q4_K_M, Q5_K_M, Q8_0` (+ IQ4_XS if easy); measure file size, **perplexity** (`llama-perplexity` on a wikitext slice), and dev-machine tok/s. Rank by size↔quality↔speed.
- **KV-cache:** fp16 vs q8_0 vs q4 at ctx {2048, 4096} — memory vs perplexity delta.
- **Context-length curve:** prefill tok/s + memory vs ctx {128, 512, 1024, 2048, 4096}.
- **(Stretch) speculative decoding:** 1B draft + 3B target speedup on dev machine.
`[HUMAN DECISION]` — model set + which quants to include. *DoD:* `explore/results.csv` + `explore/RECOMMENDATION.md` naming the on-device config (hypothesis: Q4_K_M) with reasoning. Feeds Stage 2.

**Stage 2 — On-device harness (`bench/`) scaffolding.** Build, using the Stage-1 recommended config:
- **Speed:** `llama-bench` capturing **prefill (pp)** and **decode (tg)** tok/s separately across ctx {128, 512, 1024, 2048} × out {64, 256}; median + p90 over ≥5 runs after a discarded warmup.
- **Sustained/thermal:** continuous generation ≥10 min (or back-to-back agentic-length sessions), logging tok/s in ~10s windows; concurrently sample `/sys/class/thermal/thermal_zone*/temp` and CPU freq via adb at ~2s. Output a throttle curve (tok/s vs time) + temp overlay; report **steady-state (post-throttle)** decode tok/s.
- **Battery/power:** instantaneous W from `current_now`×`voltage_now`; cross-check `dumpsys batterystats`; report watts, **%/min**, and inferences-per-charge for a bursty session.
- **Prompt corpus:** 8–12 realistic in-trip prompts, realistic system prompt + simulated tool-call context (512–2048 input tokens, 64–256 output). `[HUMAN DECISION]` — human supplies real prompts if available; else synthesize and flag for review.
*DoD:* harness + samplers + **prepared adb run scripts** committed; parser emits `results.json` (schema below); self-tested on parsing with a fixture log.

**Stage 3 — Device runs `[HUMAN — DEVICE]`.** Human physically connects the phone(s) and runs the prepared scripts; Fable ingests the logs. Do **not** block earlier stages on this. *DoD:* raw logs + parsed `results.json` under `bench/results/<device>/`.

**Stage 4 — Findings.** Fill `bench/FINDINGS.md`: the three gaps as measured values, throttle/battery plots, steady-state tok/s, and a feasibility go/no-go toward a future runtime. *DoD:* findings committed; `DECISIONS.md` updated with every choice.

**Stage 5 (stretch) — NPU pass.** ExecuTorch + Qualcomm QNN on the ceiling device to exercise the NPU. Report only.

```json
// bench/results/<device>/results.json
{
  "device": "oneplus-nord", "soc": "sd765g", "runtime": "llama.cpp",
  "model": "Llama-3.2-3B-Instruct-Q4_K_M",
  "prefill_toks_s": {"ctx_512": 0, "ctx_2048": 0},
  "decode_toks_s": {"warm": 0, "steady_state": 0},
  "throttle_knee_s": 0, "peak_temp_c": 0,
  "power_w_sustained": 0, "battery_pct_per_min": 0,
  "inferences_per_charge_est": 0, "notes": ""
}
```

## 6. Conventions

- Any Python that lands in the repo follows repo tooling: whole-dir `ruff check`/`ruff format`, type hints required, `pytest` for parsing/logic (name `test_{unit}_should_{expected}_when_{condition}` per ADR-0008), Conventional Commits per stage (`feat(bench): ...`, `feat(explore): ...`).
- `explore/` and `bench/` are **separate envs** with their own `pyproject.toml`/`uv` + lint config; heavy/tooling deps stay out of `backend/`.
- **gitignore** model weights, GGUFs, perplexity corpora, and server/bench caches. Commit scripts, configs, small metadata, results JSON/CSV, and plots only.
- No emojis in code/comments/output.

## 7. Device envelope (target)

- **Floor (pessimistic):** original OnePlus Nord — 8 GB RAM, Snapdragon 765G, Adreno 620, Android. Expect **CPU-bound**; this is the number that matters.
- **Ceiling (optimistic):** OnePlus 15 — 12 GB RAM, current flagship.
