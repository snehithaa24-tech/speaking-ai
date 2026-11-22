# Project: SAHAYAK AI

## Architecture
SAHAYAK AI is a real-time conversational voice assistant tailored for India, supporting English (India) (`en-IN`) and Hindi (`hi-IN`).

### System Topology
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS. Captures 16kHz PCM audio via Web Audio API, streams binary chunks over WebSocket, schedules incoming 24kHz PCM audio on the audio timeline, manages 10-state conversation lifecycle, and provides an accessible, responsive UI across all viewports (320px to 1440px).
- **Backend API**: FastAPI asynchronous server (`backend/app`).
  - `/ws/live/{session_id}`: Bidirectional WebSocket handling real-time audio streams, user interruption, and tool execution with Google Gemini Live API.
  - `/api/v1/auth/google`: Google OAuth token verification (verifying signature, audience, issuer, expiration) and session creation.
  - `/api/v1/sessions`: Voice session configuration, signed HMAC/JWT token issuance, and metadata persistence.
  - Rate limiting middleware: Sliding window rate limiting protecting auth and session endpoints.
- **Database & Storage**: SQLAlchemy 2.0 with async engine (`aiosqlite` for local dev; `asyncpg` for PostgreSQL / Supabase). Alembic handles schema migrations with dialect-agnostic JSON and booleans.
- **AI Integration**: Google GenAI SDK (`google-genai`) async client with Gemini Live bidirectional streaming (`client.aio.live.connect`).

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Gemini Live Async Context Manager Fix | Resolve `_AsyncGeneratorContextManager` await error using proper async session lifecycle without fake fallback | M1 | Survey 1, R3 |
| 2 | Multi-Turn WebSocket Stream Lifecycle | Wrap `AsyncSession.receive()` in persistent loop so session persists beyond turn 1 without early termination | M1 | Survey 1, R2, R3 |
| 3 | Real-Time Bidirectional Audio Streaming | Stream 16kHz PCM mic input to Gemini Live and stream 24kHz PCM output back to client | M1 | Survey 1, R2 |
| 4 | User Interruption Handling | Detect and handle server & client barge-in, cancelling active assistant playback immediately | M1 | Survey 1, R2 |
| 5 | Clean Session Teardown & Resource Management | Gracefully close Gemini Live connection, WebSocket, and unregister session on disconnect | M1 | Survey 1, R3 |
| 6 | WebSocket Automated Pytest Suite | Pytest suite for WebSocket endpoint, audio transmission, and interruption handling | M1 | Survey 1, R7 |
| 7 | Backend Telugu Purge | Remove `LanguageCode.TE_IN`, Telugu greetings, system prompts, tool schemas, seed data, and tests | M2 | Survey 2, R1 |
| 8 | Frontend Telugu Purge | Remove `te-IN` from types, `LanguageContext`, font links, CSS classes, and Tailwind config | M2 | Survey 3, R1 |
| 9 | Strict Two-Option Language Selector | Render accessible "English \| हिन्दी" toggle defaulting to English unless Hindi selected | M2 | Survey 3, R1 |
| 10 | Multilingual Validation & 422 Enforcement | Strict schema validation accepting only `en-IN` and `hi-IN`, returning 422 for unsupported languages | M2 | Survey 2, R1 |
| 11 | Async Database URL Normalization | Provide helper converting `postgres://` or `postgresql://` to `postgresql+asyncpg://` and `sqlite://` to `sqlite+aiosqlite://` | M3 | Survey 2, R4 |
| 12 | Dialect-Agnostic SQLAlchemy Models | Replace `sqlite.JSON` with standard `sa.JSON` across all models | M3 | Survey 2, R4 |
| 13 | Alembic Migration & Metadata Registration | Import models into `migrations/env.py` and fix boolean server defaults for PostgreSQL | M3 | Survey 2, R4 |
| 14 | Local SQLite Resilience | Fall back gracefully to local SQLite without failing startup if Supabase/PostgreSQL is unconfigured | M3 | Survey 2, R4 |
| 15 | Supabase Documentation | Author `docs/SUPABASE_SETUP.md` with complete pooling URL, migration, and setup instructions | M3 | Survey 2, R4, R7 |
| 16 | Google OAuth Verification | Verify ID token signature, audience, issuer, and expiration via Google public keys | M4 | Survey 2, R5 |
| 17 | Cryptographically Signed Session Tokens | Sign voice session tokens using HMAC-SHA256 or JWT with `SECRET_KEY`, eliminating forged tokens | M4 | Survey 2, R5 |
| 18 | Rate Limiting Middleware | In-memory sliding window rate limiter protecting auth (20 req/min) and sessions (40 req/min) | M4 | Survey 2, R5 |
| 19 | CORS & Environment Security | Multi-origin CORS support including 127.0.0.1, robust .env resolution, zero secret leaks | M4 | Survey 2, R5 |
| 20 | Frontend Audio Timeline Scheduling | Replace sequential `onended` queue processing with Web Audio API timeline scheduling (`currentTime + duration`) | M5 | Survey 3, R2 |
| 21 | Acoustic Feedback Prevention | Connect `ScriptProcessorNode` to destination via zero-gain node to prevent speaker feedback | M5 | Survey 3, R2 |
| 22 | Elimination of Browser TTS Collision | Suppress `speechSynthesis` when native audio stream is received to prevent robotic echo | M5 | Survey 1, 3, R2 |
| 23 | 10-State Conversation State Machine | Implement `idle`, `requesting_permission`, `connecting`, `connected`, `listening`, `processing`, `speaking`, `reconnecting`, `disconnected`, `error` | M5 | Survey 3, R6 |
| 24 | Frontend Layout Bug Fixes | Eliminate duplicate header and duplicate `id="main-content"` on `/conversation` | M5 | Survey 3, R6 |
| 25 | Mobile Audio Controls & Responsiveness | Fix dead mute button in `MicrophoneButton.tsx`, ensure clean responsive layout from 320px to 1440px | M5 | Survey 3, R6 |
| 26 | Frontend WCAG AA Accessibility | Visible focus rings, high contrast mode support, screen-reader live regions, reduced motion | M5 | Survey 3, R6 |
| 27 | E2E Requirement-Driven Test Suite | Opaque-box test suite covering Tiers 1-4 with minimum 11xN + max(5, N/2) test cases | E2E / M6 | R7 |
| 28 | Adversarial Coverage Hardening | Tier 5 white-box stress testing and edge-case verification | M6 | R7 |
| 29 | Comprehensive Handover Documentation | Deliver `README.md`, `docs/ARCHITECTURE.md`, `docs/CONVERSATION_TEST_REPORT.md`, `docs/FINAL_ENGINEERING_QA_REPORT.md`, `.env.example` | M6 | R7 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Gemini Live WebSocket Pipeline & Async Lifecycle | Features 1-6 (R2, R3) | None | DONE |
| M2 | Telugu Purge & Strict Two-Language Support | Features 7-10 (R1) | None | DONE |
| M3 | Supabase Database Architecture & SQLite Operation | Features 11-15 (R4) | None | DONE |
| M4 | Google OAuth Verification & Security Hardening | Features 16-19 (R5) | None | DONE |
| M5 | Frontend Audio Engine, State Machine, UI & A11y | Features 20-26 (R2, R6) | M1, M2 | DONE |
| M6 | Final Verification, E2E Pass, Hardening & Docs | Features 27-29 (R7) | M1, M2, M3, M4, M5, E2E Track | DONE |

---

## Interface Contracts

### 1. WebSocket Protocol (`/ws/live/{session_id}?token={signed_token}`)
- **Client -> Server Messages**:
  - Audio chunk: `{"type": "audio", "payload": {"data": "<base64_pcm16_16khz>", "mime_type": "audio/pcm;rate=16000"}}`
  - Text prompt: `{"type": "text", "payload": {"text": "<query>"}}`
  - User interrupt: `{"type": "interrupt"}`
  - Close session: `{"type": "close"}`
- **Server -> Client Messages**:
  - Audio chunk: `{"type": "audio", "payload": {"data": "<base64_pcm16_24khz>", "mime_type": "audio/pcm;rate=24000"}}`
  - Text transcript: `{"type": "text", "payload": {"text": "<transcript>", "speaker": "assistant"|"user", "is_final": boolean}}`
  - Status change: `{"type": "status", "payload": {"status": "<ConnectionStatus>"}}`
  - Interrupt signal: `{"type": "interrupt"}`
  - Error: `{"type": "error", "payload": {"code": "<CODE>", "message": "<str>"}}`

### 2. Supported Languages & Enums
- `LanguageCode`: Strictly `"en-IN"` (English India) and `"hi-IN"` (Hindi).
- Requests containing any other language code MUST return HTTP 422 Unprocessable Entity.

### 3. Voice Session Token Contract
- Token must be a cryptographically signed JWT or HMAC signed payload containing:
  `{"sub": "<session_id>", "session_id": "<session_id>", "config": {...}, "exp": <unix_ts>}`
- Backend validates signature with `settings.SECRET_KEY` before accepting WebSocket connections.

### 4. Database Connection Contract
- `get_async_database_url(url: str) -> str`: Normalizes any PostgreSQL or SQLite URL into an async SQLAlchemy dialect (`postgresql+asyncpg://` or `sqlite+aiosqlite://`).
- Models use standard `sa.JSON` and boolean defaults compatible with PostgreSQL.

---

## Code Layout
```
backend/
├── app/
│   ├── api/v1/          # FastAPI routers (auth, sessions, knowledge, websocket)
│   ├── core/            # Config, security, logging
│   ├── database/        # Session, engine, URL normalization
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic schemas (LanguageCode strict en-IN, hi-IN)
│   └── services/        # Gemini Live service, Auth service, Knowledge service
├── migrations/          # Alembic environment and versions
└── tests/               # Pytest test suites (unit, websocket, db, security, language)

frontend/
├── src/
│   ├── components/      # React UI components (voice, navigation, accessibility, feedback)
│   ├── contexts/        # LanguageContext, AccessibilityContext, AuthContext
│   ├── hooks/           # useVoiceSession, useAudioRecording, etc.
│   ├── services/        # websocket.ts, api.ts
│   ├── types/           # index.ts (LanguageCode strict 'en-IN' | 'hi-IN', 10 states)
│   └── utils/           # audio.ts (timeline scheduling, PCM converters)
└── tests/               # Vitest component & audio tests

docs/
├── ARCHITECTURE.md
├── SUPABASE_SETUP.md
├── CONVERSATION_TEST_REPORT.md
└── FINAL_ENGINEERING_QA_REPORT.md
```
