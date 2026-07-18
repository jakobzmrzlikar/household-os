# Fable Mission Brief — Hybrid On-Device/Cloud Model-Routing Runtime (#6 runtime)

> **Audience:** Claude Fable 5, in Claude Code inside this repo (run in a dedicated **git worktree** on its own feature branch).
> **Human owner:** Jakob. **Judgment/taste calls:** the human (with Opus).
> **Status:** **PRE-BUILD, DO NOT MERGE YET.** This is durable runtime IP built ahead of validation. It is merged only after the Nord on-device spike (`feat/on-device-spike`, Stage 3) confirms local inference is viable. Build it clean and tested; gate the merge on the experiment.
> **Relationship to other briefs:** consumes the same OpenAI-compatible local-server seam the fine-tune brief uses (`docs/fable-briefs/workstream-b-finetune.md`); independent of the behavioral-graph brief but **both touch `app/` — see the conflict note in §3**. The recommended on-device config comes from `explore/RECOMMENDATION.md` (Q4_0 + q8_0 KV + flash attention).
> **This brief is the source of truth. Read it fully before acting.**

## 0. How to operate (read first)

1. **Read before building:** this brief; `CLAUDE.md`; ADRs `0003` (pydantic-ai), `0005` (hexagonal — load-bearing), `0006` (attrs/pydantic), `0007` (basedpyright), `0009` (DI container); `.claude/rules/ports.md`, `.claude/rules/adapters.md`, `.claude/rules/code-ordering.md`, `.claude/rules/documentation.md`; the existing chat seam (`app/domain/ports/chat.py`, `app/application/chat.py`, `app/adapter/output/{mock_chat,hardcoded_chat}.py`, `app/infrastructure/container.py`).
2. **Design before code.** Produce the port surface + an **ADR-0011** draft (hybrid routing runtime) mapped to §5 Stage 0, then **STOP for human approval** before implementing. The decomposition below is already agreed — the ADR records it, it does not re-litigate it.
3. **HITL / checkpointed mode.** Stop at every `[HUMAN DECISION]`. The human may steer from a phone — ask **one concise question at a time** with a recommended default.
4. **Self-test every stage** from `backend/`: `uv run pytest -m "not integration"`, `uv run ruff check --fix ./`, `uv run ruff format ./`, `uv run lint-imports`, `uv run basedpyright`.
5. **Escalate judgment, don't guess** on `[HUMAN DECISION]` items (tier model, escalation signal, connectivity semantics, default provider).

## 1. Why this exists

The product's in-trip reliability moat needs a runtime that answers **offline and instantly** on-device for common/simple queries, and **escalates to a frontier cloud model** for hard reasoning — the pattern Apple and Google both ship. This brief builds that **model-routing runtime** as a clean hexagonal layer behind the existing chat/model seam, so the agent calls "a model" and the runtime decides *which* — local or cloud — by connectivity, sensitivity, and complexity, with a confidence-based escalation path.

**The load-bearing architectural discipline (do not violate — this is the whole point of the design review that produced this brief):**
- **The routing policy is pure domain logic over ABSTRACT signals and an ABSTRACT choice.** It maps `RoutingSignals -> ModelTier` (a value object, e.g. `LOCAL`/`CLOUD`). It references **no** concrete model, provider, protocol, or SDK. If the policy ever imports or names `llama-server`, `Anthropic`, `httpx`, or an OpenAI client, that is the coupling defect this brief exists to prevent.
- **Signals come through ports**, never computed in the policy: `ConnectivityProbe`, `SensitivityClassifier`, `ComplexityEstimator`, `ConfidenceEstimator`. Their *values* are produced by adapters (heuristics or model calls = I/O); the policy only consumes them.
- **The model access point is a neutral `Model` port** (or pydantic-ai's provider-agnostic `Model`, which `CLAUDE.md` sanctions inside `domain/agents`). "OpenAI-compatible" is an **implementation detail of the local adapter only** (that is how `llama-server` speaks); it must not appear in the port or the domain.
- **Provider-agnostic by construction.** Adapters wrap any provider (pydantic-ai supports Anthropic, OpenAI, Google, Bedrock, Groq, Mistral; the local adapter wraps `llama-server`). The **composition root** binds the concretes. Default cloud binding = latest Claude per `CLAUDE.md`, but nothing in domain/application knows or assumes that; swapping providers is a one-line container change.
- **Dispatch is an adapter, not domain.** A `RoutingModel` adapter implements the `Model` port and delegates to the bound local/cloud model per the policy's tier. Composing adapters is adapter territory.

## 2. Objective & definition of done

- **ADR-0011** recording the hybrid-routing decomposition (approved at Stage 0).
- **Domain:** `RoutingPolicy` (pure), `RoutingSignals` + `ModelTier` value objects, the escalation *rule* (threshold over an abstract confidence), and the neutral `Model` port — all `attrs`, no framework/I-O imports.
- **Ports:** `ConnectivityProbe`, `SensitivityClassifier`, `ComplexityEstimator`, `ConfidenceEstimator` Protocols (Protocol-first per `ports.md`) with attrs request/response types.
- **Adapters (`app/adapter/output/`):** a **local model** adapter (talks to `llama-server` over its OpenAI-compatible HTTP API — the only place that detail lives), one or more **cloud model** adapters (via pydantic-ai; Claude default), a **`RoutingModel`** composite implementing the `Model` port, and **heuristic + mock** implementations of every signal port.
- **Composition root:** `dependency-injector` providers wiring concretes to ports (ADR-0009), with **all bindings (endpoints, thresholds, default provider) in settings/config** — no hardcoding.
- **Integration:** the routing runtime is reachable through the existing chat/agent path behind the `Model` port; an end-to-end escalation flow works against **mock** adapters (no real model/API needed in tests).
- **Tests:** policy truth-table + escalation-rule tests (pure, exhaustive over signal combinations), adapter mapping/mocks, and a mock-backed end-to-end route+escalate test; pytest naming per `tests.md`; anything touching a real endpoint marked `@pytest.mark.integration`.
- **Done =** ADR-0011 merged onto the branch; domain + ports + adapters + DI + mock-backed integration committed; all five checks green; a `DO-NOT-MERGE` note + a `DECISIONS.md` recording every choice and the exact "flip local endpoint from Mac to phone" step for later.

## 3. Scope guardrails (non-goals)

- **No mobile app, no on-phone deployment, no real connectivity plumbing.** The `ConnectivityProbe` is designed now and given a **stub/config-driven implementation**; its meaningful implementation arrives with the phone runtime (see the connectivity note below). Do not build platform-specific networking.
- **No fine-tuning, no behavioral graph, no new product endpoints** beyond wiring the runtime behind the existing chat seam. Do not touch `explore/`, `bench/`, or `frontend/`.
- **Do not merge to main.** This branch waits on the Nord result. Keep it rebasable and green.
- **Connectivity semantics caveat (state it in the ADR):** in a server-hosted backend, "device is offline" is a *client* concept the server cannot observe. The port + policy are built now so the logic is ready; the real signal is wired when/if this runtime (or its policy) runs on the phone. Treat server-side connectivity as a configurable/injected input for now. `[HUMAN DECISION]` — confirm this framing.
- **Conflict note (both backend briefs):** this brief and `behavioral-graph-schema.md` both add to `app/domain/ports/`, `app/adapter/output/`, and `app/infrastructure/container.py`. To minimize merge pain: keep new files in **dedicated modules** (do not reorganize shared `__init__.py` exports beyond additive lines), and add DI providers as an **appended block**, not a rewrite of `container.py`. Expect a small manual merge on `container.py` at PR time; that is fine.

## 4. Architecture & placement (hexagonal — strict)

- `app/domain/` — `RoutingPolicy` (in `services/` or `agents/` as fits), `RoutingSignals`/`ModelTier` value objects (`models/`), escalation rule, and the neutral `Model` port (`ports/`). No SQLAlchemy, no httpx, no provider SDKs, no `llama-server`/OpenAI/Anthropic names.
- `app/domain/ports/` — the four signal Protocols + the `Model` port; attrs request/response; Protocol-first.
- `app/adapter/output/` — local model client (OpenAI-compatible → `llama-server`), cloud model client(s) (pydantic-ai), `RoutingModel` composite, heuristic signal adapters, and a mock per port.
- `app/application/` — a use case orchestrating "answer a query" through the `Model` port if one is needed beyond the existing `chat.py`; keep orchestration thin.
- `app/infrastructure/` — settings (endpoints, thresholds, default provider), DI providers binding concretes to ports; the router→container `Provide[...]` seam is the only sanctioned outward import. Update the import-linter whitelist only if strictly necessary, narrowly.

## 5. Staged plan (implement in order, pause after each)

**Stage 0 — Port surface + ADR-0011 (light design gate).** Draft ADR-0011 recording the agreed decomposition, the `ModelTier` model, the escalation-signal choice, and the connectivity caveat. List the exact Protocol signatures. **STOP for approval.** `[HUMAN DECISION]` — tier model (binary `LOCAL`/`CLOUD` vs ordered tiers on-device→cloud-small→cloud-frontier), escalation signal (logprob/entropy vs judge-model vs heuristic), default cloud provider (default: latest Claude). *DoD:* ADR draft + signatures; sign-off in `DECISIONS.md`.

**Stage 1 — Domain (pure).** `RoutingSignals`, `ModelTier`, `RoutingPolicy.decide(signals) -> ModelTier`, and the escalation rule `should_escalate(confidence, signals) -> bool`. Exhaustive truth-table tests. No framework imports. *DoD:* domain + tests green under `basedpyright`/`lint-imports`.

**Stage 2 — Signal ports + heuristic/mock adapters.** `ConnectivityProbe`, `SensitivityClassifier`, `ComplexityEstimator`, `ConfidenceEstimator` Protocols; simple heuristic implementations (e.g. complexity from token/keyword features; sensitivity from a PII/location classifier stub) + mocks. *DoD:* ports + adapters + mock-backed tests.

**Stage 3 — Model adapters + `RoutingModel`.** Neutral `Model` port; local adapter (llama-server, OpenAI-compatible — the sole home of that detail, dev endpoint from settings); cloud adapter(s) via pydantic-ai (Claude default, provider from config); `RoutingModel` composite that consults the policy, dispatches to the chosen tier, and applies the escalation rule (call tier, estimate confidence, escalate if needed and connectivity permits). Mocks for both models. *DoD:* composite works end-to-end against mocks; provider swappable via config; tests green.

**Stage 4 — Composition root + integration.** Settings for endpoints/thresholds/default provider; DI providers binding concretes to ports (appended block per §3); reach the runtime through the existing chat/agent path behind the `Model` port. Mock-backed end-to-end route+escalate test. *DoD:* wiring works; import-linter green; no hardcoded provider/endpoint.

**Stage 5 — Docs, gate, handoff.** Finalize ADR-0011; `DECISIONS.md` with every choice; a prominent `DO-NOT-MERGE-UNTIL-NORD-VERIFIED` note in the ADR/branch; document the one-line "point local adapter at the phone instead of the Mac" step and how a future phone-resident runtime reuses the policy. *DoD:* docs committed; branch green and rebasable.

## 6. Conventions

- ADR-0006 (attrs by default; pydantic only at boundaries — DTOs, settings, pydantic-ai structured output; never stdlib dataclasses).
- ADR-0007 basedpyright strict; ADR-0008 pytest naming `test_{unit}_should_{expected}_when_{condition}`, `@pytest.mark.integration` for anything hitting a real endpoint.
- Whole-repo `ruff check`/`ruff format` + `lint-imports` (never scope to changed files); reST/Sphinx docstrings; newspaper-principle ordering.
- Conventional Commits per stage (`feat(backend): add routing policy domain`, `feat(backend): add hybrid RoutingModel adapter`, `docs(adr): add ADR-0011 hybrid routing runtime`).
- No emojis anywhere.

## 7. Key decisions to resolve with the human (`[HUMAN DECISION]`)

1. **Tier model** — binary `LOCAL`/`CLOUD` (simplest) vs ordered tiers (on-device → cloud-small → cloud-frontier). Recommendation: model `ModelTier` as ordered/extensible even if only two are wired now.
2. **Escalation signal** — logprob/entropy from the local model (cheap, needs server support) vs a judge-model score (accurate, costs a call) vs a heuristic. Recommendation: define the `ConfidenceEstimator` port now; wire a heuristic default, leave judge/logprob as swappable adapters.
3. **Connectivity semantics** — confirm the "server can't see device offline; inject/config for now" framing.
4. **Default cloud provider** — default latest Claude per `CLAUDE.md`; confirm the config key so it stays swappable.
