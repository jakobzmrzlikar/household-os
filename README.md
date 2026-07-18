# Household OS

**Shared life, zero bookkeeping.** Flatmates and couples run on invisible admin — who paid, what's in the fridge, whose turn to buy olive oil. Every shared-household app dies the same death: manual data entry. Household OS removes the entry cost entirely: point your camera at a receipt, or say "we're out of olive oil" while cooking. The AI drafts the bookkeeping; your household approves it with one tap.

**There is no chat box in this app.**

## How it works

```
capture (camera / voice)  →  extraction (vision / STT + LLM)  →  pending commands  →  one-tap approval  →  shared household state
```

- **Capture**: photograph a receipt or hold-to-record a voice note. That's the entire input surface.
- **Extraction**: a vision model reads the receipt (merchant, total, line items — Slovenian diacritics included); voice notes are transcribed and parsed into pantry intents.
- **Staged, never executed**: agents can only *propose*. Every AI output lands as an inert pending command — a typed verb with a payload, carrying provenance (which agent, which model, from which capture).
- **Approval**: another household member sees the draft on their phone — "€3.67 at Lidl, split equally" — and approves or rejects. Only approval executes, and it revalidates against current state first. Approving twice fails closed.
- **Shared state**: pantry and expenses update for everyone, instantly.

Every write goes through a typed command (`log_receipt`, `adjust_pantry_item`, `record_expense`, `approve_command`, …) with invariants enforced in code: splits must sum to the total, quantities can't go negative, nothing crosses household boundaries. The model is never trusted with a raw write — and is swappable in one line (we switched extraction providers mid-hackathon).

## Stack

- **Mobile**: Expo / React Native (two-phone live demo: capture on one, approve on the other)
- **Backend**: FastAPI + Pydantic AI, hexagonal architecture (ports & adapters, enforced by import-linter), SQLAlchemy
- **Models**: `gpt-5-mini` (receipt vision + voice-intent parsing), ElevenLabs Scribe (speech-to-text) — both behind ports with mock adapters
- **Analytics**: PostHog (approval rates per command type — the signal for earning per-verb auto-approval)

## Run it

```bash
# backend
cd backend
uv sync --all-groups
cp .env.example .env   # add API keys
uv run uvicorn app.main:app --reload --host 0.0.0.0

# mobile
cd frontend/mobile
npm install
# set EXPO_PUBLIC_API_URL in .env to your machine's address
npx expo start
```

Open in Expo Go, pick a member, photograph a receipt.

Built in a day at a mobile-app hackathon in Ljubljana.
