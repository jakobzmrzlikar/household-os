# Fable Mission Brief — Workstream B, Stage 2: Fine-tune & Evaluate a Small Model (#1)

> **Audience:** Claude Fable 5, in Claude Code inside this repo.
> **Human owner:** Jakob. **Judgment/taste calls:** the human (with Opus).
> **Prerequisite:** Workstream B Stage 1 (eval harness) is merged — see `docs/fable-briefs/workstream-b-evals.md` and `backend/evals/`.
> **This brief is the source of truth. Read it fully before acting.**

## 0. How to operate (read first)

1. **Read before building:** this brief; `docs/fable-briefs/workstream-b-evals.md` and the built harness under `backend/evals/` (you will run *that* harness against the fine-tuned model — do not build a second eval system); `CLAUDE.md`; `docs/adr/0003,0005,0006,0007,0008`.
2. **Plan first, then stop.** Propose a staged plan mapped to §5, then **wait for approval**.
3. **HITL / checkpointed mode (this run).** Unlike the overnight eval build, this stage is **decision-heavy and incurs real API cost** — run it with per-stage pauses and stop at every `[HUMAN DECISION]`. The human may be steering from a phone (Claude Code Remote Control), so ask **one concise question at a time** with a recommended default.
4. **Self-test every stage** (from `backend/` for the eval-side code): `uv run pytest -m "not integration"`, `uv run ruff check --fix ./`, `uv run ruff format ./`, `uv run lint-imports`, `uv run basedpyright`. Training-side code (separate env, see §4) has its own lint/tests.
5. **Escalate judgment, don't guess** on `[HUMAN DECISION]` items (base model, compute target, data strategy/volume, tracking tool).

## 1. Why this exists

Stage 1 gave us a model-agnostic eval harness and a baseline (`claude-haiku-4-5`). This stage answers Workstream B's core question: **how close can a small, fine-tunable model get to that baseline on our in-trip tasks?** Distillation from a frontier model provides the *first* training data (we have no users yet), but **distillation is the initial data SOURCE, not the design** — build the pipeline **source-agnostic** so real data slots in later without redesign (see §4 and §5 Stage 1). The output is a decision input ("is on-device viable?"), not a shipping model.

**Design-for-real-data principle (load-bearing):** everything downstream of the data (schema → train → quantize → serve → eval) must be agnostic to where the examples came from. The data *source* is a swappable adapter; the canonical training-example schema is the stable contract. Synthetic distillation is the first adapter; production traces and human-curated/preference data are designed-for now, built later.

## 2. Objective & definition of done

- A **training pipeline** (data gen → LoRA fine-tune → quantize → serve) that runs end-to-end, proven by a **tiny smoke run** (a few steps / a handful of examples). The **full fine-tune is a human-triggered GPU step**, not part of the autonomous session.
- The fine-tuned, quantized model is **served locally behind an OpenAI-compatible endpoint** and reachable by the existing harness as just another model (`OpenAIChatModel(base_url=...)` — no new eval code).
- A **comparison report** (reusing the Stage-1 report generator) of the small model vs `claude-haiku-4-5` on the same scenarios.
- Done = pipeline built + smoke-tested + committed; harness can point at the local model via one config change; `training/README.md` documents the full-run commands; a `FINDINGS.md` stub is ready for the human to fill after the real run.

## 3. Scope guardrails (non-goals)

- **No on-device/mobile runtime (#6)** — local serving on the dev machine only.
- **No eval-set contamination:** the 24 scenarios in `backend/evals/data/` are the **benchmark** — they must **never** appear in training data. Enforce a test that asserts train/eval disjointness.
- Do not modify `frontend/`. Do not break existing endpoints/tests.
- **Model weights & datasets are NOT committed** — gitignore them; keep only configs, scripts, and small metadata in git.
- Keep training dependencies **out of the FastAPI app** (see §4).

## 4. Architecture & placement (important)

Two decoupled environments that communicate via **artifacts + HTTP**, so nothing heavy leaks into the app:

- **`training/` (new top-level package, its OWN uv env + pinned Python).** Holds data-gen, fine-tune, and quantize/serve code. **Pin its Python to whatever the ML stack supports** — torch/Unsloth may not support the backend's 3.14 yet; do **not** force ML deps into the 3.14 backend env. `[HUMAN DECISION]` — confirm the training Python version.
- **Serving = an HTTP boundary.** The quantized model is served via an OpenAI-compatible local server (llama.cpp server, `mlx_lm.server`, or vLLM). The backend/eval side treats it as a **model adapter over HTTP** — `OpenAIChatModel(model=..., base_url="http://localhost:PORT/v1")` — plugged into the raw-`Model` seam from Stage 1. **No cross-env imports:** training produces a model file → server exposes it → the 3.14 backend hits it over HTTP. This also keeps hex clean: the local model is just another adapter behind the existing model port.
- **Eval integration stays in `backend/evals/`** (3.14 env, only needs an HTTP client) — reuse the Stage-1 runner + report generator unchanged; add only a config entry pointing at the local endpoint.
- **Tracking (optional, light):** ClearML (open-source; the human has prior experience) for experiment + dataset tracking, or W&B, or none. `[HUMAN DECISION]`. It is the MLOps spine, not the trainer.

## 5. Staged plan (implement in order, pause after each)

**Stage 1 — Source-agnostic training-data layer (distillation is the first source, not the design).** Build the data layer so real data slots in later without redesign:
- **Canonical `TrainingExample` schema**, rich enough for real data even though synthetic won't fill every field: input (trip context + user message + conversation history), output (assistant reply + tool calls), and metadata — **provenance/source**, timestamp, optional **quality/feedback signal**, optional **human-edited** flag, **consent/PII** flag. **Align this schema with the interaction-capture schema Workstream A (#11 instrumentation / #2 graph) will emit**, so a future production trace converts to a training example with minimal transform.
- **`TrainingDataSource` interface** (ports/adapters). Implement **`SyntheticDistillationSource`** now (prompt `claude-sonnet-5` to produce example pairs across the eval *categories* but **disjoint content**). **Stub** `ProductionTraceSource` and `HumanCuratedSource` behind the same interface — designed-for, not built.
- Everything downstream (train/quantize/serve/eval) consumes the canonical schema, so swapping sources later touches **only the loader**.
- Train/val split; **disjointness test** vs `backend/evals/data/`.
- Leave room for **preference/DPO data** later — do not hard-code an SFT-only schema; include a de-identification hook that real (PII-bearing) data will need.
- **Keep it light:** one schema, one interface, one concrete source now — the rest are stubs.
`[HUMAN DECISION]` — schema fields, dataset size, category weighting, distill-vs-public. *DoD:* canonical schema + source interface + synthetic source built; small dataset generated, validates, provably disjoint from the eval set. *(Costs frontier API tokens — confirm before large generation.)*

**Stage 2 — Fine-tune.** LoRA/QLoRA config + training script (Unsloth if NVIDIA; **MLX if Apple Silicon**), tracked in the chosen tool. Run a **tiny smoke train** (few steps) to prove the loop end-to-end. `[HUMAN DECISION]` — base model (default: a 1–3B instruct model, e.g. Llama-3.2-3B / Gemma-3 / Qwen) and **compute target** (MLX on this Mac vs a rented cloud GPU vs build-only). *DoD:* config + script committed; smoke run completes and logs; full-run command documented (not executed autonomously).

**Stage 3 — Quantize + serve.** Quantize the adapter-merged model (GGUF via llama.cpp, or MLX 4-bit) and stand up the OpenAI-compatible local server. Add a `README` snippet for starting it. *DoD:* server starts and answers a trivial request; documented.

**Stage 4 — Harness integration.** Add one eval config pointing the Stage-1 harness at `OpenAIChatModel(base_url=local)`. Verify the wiring with a **mock/2-scenario smoke** (no full run). The **full comparison run vs `claude-haiku-4-5` (judge `claude-sonnet-5`) is a human step** (real API + local model). *DoD:* one-command comparison documented in `training/README.md`; wiring smoke-tested.

**Stage 5 — Findings scaffold.** Create `training/FINDINGS.md` templated for: baseline vs fine-tuned scores per dimension, latency/size, the gap, and a go/no-go note toward #6 (on-device). *DoD:* template committed; `DECISIONS.md` updated with every choice + the exact full-run commands.

## 6. Conventions

- Backend/eval-side code: all Stage-1 conventions (ADR-0006 attrs/pydantic, ADR-0007 basedpyright, ADR-0008 pytest naming + `@pytest.mark.integration`, whole-repo ruff, `lint-imports`, Conventional Commits per stage).
- `training/` is a separate env: give it its own `pyproject.toml`/`uv` + ruff/basedpyright config; keep its heavy deps (torch/unsloth/mlx) fully out of the backend.
- **gitignore** model weights, datasets, and server caches. Commit configs, scripts, small metadata only.
- Commit per stage; never `--no-verify`.

## 7. Decisions to surface (this run is HITL — ask one at a time)

- Base model (default: a 1–3B instruct model suited to the compute target).
- Compute target: MLX on this Mac (confirm Apple Silicon + RAM) vs rented cloud GPU vs build+smoke only.
- Training Python version / env isolation.
- Dataset size, category weighting, distill vs public.
- Tracking tool: ClearML vs W&B vs none.
- **Cost ack:** this stage spends real API tokens (data generation + the judge during the comparison run) — unlike the mock-only Stage 1.

## 8. If run unattended instead (fallback)

If launched without a human available: pre-answer §7, then **build + smoke-test only** (Stages 1–4 scaffolding on tiny data), do **NOT** run large data generation, the full fine-tune, or the full comparison (all human-triggered), commit per stage, and write `DECISIONS.md` + `FINDINGS.md` stub. Leave the tree green.
