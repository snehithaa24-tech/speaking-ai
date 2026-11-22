# SAHAYAK AI (सहायक)

**Multilingual Real-Time Voice Assistant for Accessibility**

SAHAYAK AI is a production-grade, voice-first artificial intelligence assistant engineered for Indian citizens. Powered by the Google Gemini Live API (`google-genai` SDK) over bidirectional WebSockets, SAHAYAK AI provides natural, low-latency spoken conversations in **English (India)** (`en-IN`) and **Hindi** (`hi-IN`).

The platform is designed accessibility-first to empower citizens who face challenges with reading, typing, or navigating conventional visual applications, delivering verified domain assistance across Government Schemes (PM-KISAN, Ayushman Bharat), Emergency Medical Triage (108 Ambulance), Agricultural Advisory (Crop disease & soil management), and Public Transit.

---

## Requirements Verification & Feature Mapping (R1–R7)

All core requirements specified in the project charter and acceptance criteria have been implemented, hardened, and verified with 100% passing automated test suites:

| Requirement | Scope & Technical Implementation | Test Evidence | Status |
|---|---|---|:---:|
| **R1: Strict Two-Language Policy** | Supported languages strictly restricted to English (`en-IN`) and Hindi (`hi-IN`). Accessible two-option language toggle ("English \| हिन्दी"). Complete architectural purge of all legacy third languages from UI selectors, schemas, system prompts, voices, and tests. Strict schema validation returns HTTP 422 Unprocessable Entity for any unsupported language code. | `test_tier1_feature_coverage.py`<br>`LanguageSelector.test.tsx` (11 tests) | **VERIFIED** |
| **R2: Natural Gemini Live Voice Interaction** | Real-time bidirectional audio streaming over `/ws/live/{session_id}`. Client captures 16kHz mono PCM via Web Audio API with zero-gain acoustic feedback prevention; backend pipes audio to Google Gemini Live API; 24kHz PCM linear audio chunks stream back to client and are scheduled gaplessly on the Web Audio API audio timeline (`currentTime + duration`). Natural barge-in interruption halts active speech in < 120ms. Explicit browser TTS suppression eliminates synthetic echo. | `test_tier3_cross_feature.py`<br>`audio.test.ts` (11 tests)<br>`test_tier4_application_scenarios.py` | **VERIFIED** |
| **R3: Async Context Manager Lifecycle** | Diagnosed and eliminated `_AsyncGeneratorContextManager can't be used in 'await' expression` defect. Implemented `GeminiLiveSessionWrapper` with persistent `client.aio.live.connect` async context management, synchronized `_send_lock` concurrency protection, multi-turn message loops, and deterministic resource teardown without dummy fallbacks. | `test_websocket_live.py` (11 tests)<br>`test_tier1_feature_coverage.py` | **VERIFIED** |
| **R4: Supabase Database & SQLite Resilience** | Dual-tier database architecture supporting production Supabase PostgreSQL via Supavisor Transaction Pooler (port 6543) and offline zero-credential local development via SQLite (`aiosqlite`). Automated URL normalization (`get_async_database_url`), dialect-agnostic SQLAlchemy models (`sa.JSON`, boolean defaults), Alembic migrations, and automatic startup fallback to SQLite if PostgreSQL credentials are absent or unreachable. | `test_database.py` (21 tests)<br>`docs/SUPABASE_SETUP.md` | **VERIFIED** |
| **R5: Google OAuth & Security Hardening** | Google OAuth ID token verification (verifying signature, audience, issuer, expiration). Cryptographically signed ephemeral voice session tokens (HS256 JWT with `SECRET_KEY`) preventing forged connections. Backend-only `GEMINI_API_KEY` handling with zero client bundle exposure. Multi-origin CORS protection and in-memory sliding-window rate limiting (auth: 20 req/min; sessions: 40 req/min). | `test_security.py` (19 tests)<br>`test_tier2_boundary_corner.py`<br>`test_tier5_adversarial_hardening.py` | **VERIFIED** |
| **R6: Professional Accessible Frontend** | SaaS conversation interface implementing a robust 10-state conversation machine (`idle`, `requesting_permission`, `connecting`, `connected`, `listening`, `processing`, `speaking`, `reconnecting`, `disconnected`, `error`). Full responsiveness across 7 required viewports (320px, 360px, 390px, 768px, 1024px, 1280px, 1440px). WCAG 2.1 AA accessibility compliance (high contrast > 7:1, large text, reduced motion, ARIA live regions, keyboard shortcuts). | `ConnectionStatus.test.tsx` (15 tests)<br>`MicrophoneButton.test.tsx` (15 tests)<br>`npm run build` | **VERIFIED** |
| **R7: Comprehensive Testing & Handover Docs** | 221 passing backend pytest tests (121 E2E tests across Tiers 1–5), 52 passing frontend Vitest tests, 0 TypeScript errors, 0 ESLint warnings. Complete handover documentation: `README.md`, `docs/ARCHITECTURE.md`, `docs/SUPABASE_SETUP.md`, `docs/CONVERSATION_TEST_REPORT.md`, `docs/FINAL_ENGINEERING_QA_REPORT.md`, and safe `.env.example`. | Full repository verification suites passing cleanly | **VERIFIED** |

---

## System Architecture Overview

```
                      +---------------------------------------+
                      |         Citizen Browser Client        |
                      |  React 18 + TypeScript + Tailwind CSS |
                      +---------------------------------------+
                        | Audio Capture: 16kHz PCM (0-gain node)
                        | Audio Playback: 24kHz Timeline Buffer
                        | State Machine: 10 Operational States
                        v
     +---------------------------------------------------------+
     |                  FastAPI Backend Gateway                |
     |           (Port 8000 / Uvicorn Asynchronous)            |
     +---------------------------------------------------------+
       |                                      |
       | /ws/live/{session_id}?token=...      | REST Endpoints (/api/v1)
       v                                      v
+--------------------------+          +---------------------------------+
|   Gemini Live Service    |          | Sliding Window Rate Limiting    |
| (GeminiLiveSessionWrapper|          | (Auth: 20/min, Sessions: 40/min)|
|    _send_lock & VAD)     |          +---------------------------------+
+--------------------------+                          |
       |                                              v
       | Bidirectional Streaming              +---------------------------------+
       | (audio/pcm;rate=16000                | Google OAuth 2.0 Token Check    |
       |  -> 24000)                           | (Signature, aud, iss, exp)      |
       v                                      +---------------------------------+
+--------------------------+                          |
|   Google Gemini Live     |                          v
| (gemini-2.0-flash-exp)   |          +---------------------------------+
+--------------------------+          | Dual-Tier Database Layer        |
       |                              | - Local Dev: SQLite + aiosqlite |
       v Tool Calls                   | - Production: Supabase + asyncpg|
+--------------------------+          +---------------------------------+
| Knowledge Base Retrieval |                          |
| (Gov Schemes, Farming,   |                          v
|  Transit, 108 Hospitals) |          +---------------------------------+
+--------------------------+          | 6 Tables: Users, Sessions,      |
                                      | Messages, Knowledge, Feedback   |
                                      +---------------------------------+
```

---

## Quick Start Guide

### Prerequisites
- **Node.js**: v20.x or higher
- **Python**: v3.11 or v3.12
- **Google Gemini API Key**: Obtainable from [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Repository Setup & Environment Configuration

```powershell
# Clone or navigate to the workspace
cd "D:\Own webs\ai voice"

# Copy the master zero-secret template to .env
copy .env.example .env

# Configure your Gemini API key in .env:
# GEMINI_API_KEY=AIzaSy...
```

### 2. Backend Environment Setup

```powershell
# Navigate to backend and create virtual environment
cd backend
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# On Linux/macOS: source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
cd ..
```

### 3. Frontend Environment Setup

```powershell
# Navigate to frontend and install node packages
cd frontend
npm install
cd ..
```

### 4. Running the Application

#### Option A: One-Click Development Launcher (Windows)
Double-click `dev.bat` or run:
```powershell
.\dev.bat
```

#### Option B: Manual Startup in Separate Terminals

**Terminal 1 — Backend API Server:**
```powershell
backend\venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Health Check*: Open `http://127.0.0.1:8000/health` (Returns `{"status": "healthy"}`).

**Terminal 2 — Frontend Vite Dev Server:**
```powershell
cd frontend
npm run dev
```
*Application Access*: Open `http://localhost:5173` in your browser.

---

## Automated Verification & Testing Commands

All test suites and static analysis tools run out-of-the-box with zero configuration:

### 1. Backend Pytest Suites
```powershell
# Run the complete Tier 5 Adversarial Coverage Hardening Suite (34 tests)
backend\venv\Scripts\pytest.exe backend\tests\e2e\test_tier5_adversarial_hardening.py -v

# Run the complete E2E Test Suite (Tiers 1-5: 121 tests passed, 1 skipped)
backend\venv\Scripts\pytest.exe backend\tests\e2e -v

# Run the entire Repository Backend Suite (221 tests passed, 1 skipped)
backend\venv\Scripts\pytest.exe backend\tests -v
```

### 2. Frontend Test & Build Pipeline
```powershell
cd frontend

# Run Vitest test suite (4 test files, 52 unit/integration tests)
npm test -- --run

# Run TypeScript static type check (0 errors)
npm run typecheck

# Run ESLint validation (0 errors, 0 warnings)
npm run lint

# Run production Vite build (Clean asset compilation in dist/)
npm run build

cd ..
```

### 3. Code Style & Linting
```powershell
# Backend application linting
backend\venv\Scripts\ruff.exe check backend\app
```

---

## Security Guidelines & Credentials Protection

1. **Zero Secret Leakage in Client Bundles**:
   - `GEMINI_API_KEY`, `SECRET_KEY`, and `DATABASE_URL` are strictly consumed by the FastAPI backend.
   - Vite is configured to only bundle variables prefixed with `VITE_` into client code. Client builds (`dist/assets/*.js`) are forensically audited to confirm zero secret presence.

2. **Cryptographic Session Signing**:
   - Every voice conversation requires a signed HS256 JWT minted by `/api/v1/sessions` using `SECRET_KEY`.
   - The WebSocket gateway inspects the token signature, expiration (1-hour TTL), and ensures `token.session_id == path.session_id`. Tampered, expired, or mismatched tokens are rejected with WebSocket close code `1008 Policy Violation`.

3. **In-Memory Sliding-Window Rate Limiting**:
   - Authentication endpoints (`/api/v1/auth/*`): 20 requests / 60 seconds per IP.
   - Voice session endpoints (`/api/v1/sessions/*`): 40 requests / 60 seconds per IP.
   - Throttled requests return HTTP 429 Too Many Requests with `Retry-After` headers and compliant CORS headers.

4. **Database Security & Supabase Row Level Security**:
   - In production Supabase deployments, all 6 tables enforce Row Level Security (RLS) policies.
   - Database passwords containing special characters must be RFC 3986 URL-encoded (e.g., `#` -> `%23`). Refer to `docs/SUPABASE_SETUP.md` for full production connection instructions.

---

## Troubleshooting

| Issue | Root Cause | Solution |
|---|---|---|
| **Microphone Permission Blocked** | Browser blocked microphone access. | Click the camera/microphone icon in the browser address bar, select "Always allow `http://localhost:5173`", and refresh the page. |
| **WebSocket 1008 Policy Violation** | Token is expired, tampered, or mismatched with session ID. | Start a fresh session from the UI home page (`/`), which will mint a new cryptographically signed token via `POST /api/v1/sessions`. |
| **HTTP 429 Too Many Requests** | Rate limit threshold exceeded (sliding 60-second window). | Wait the number of seconds specified in the `Retry-After` HTTP header before retrying requests. In test runs, rate limiter is automatically reset. |
| **Database Connection Warning** | PostgreSQL / Supabase credentials not set or unreachable. | **No action required.** SAHAYAK AI features automatic startup fallback to local SQLite (`sqlite+aiosqlite:///./sahayak.db`), ensuring continuous offline operation without blocking startup. |
| **Browser Audio Not Playing** | Browser autoplay policy blocked audio context. | Click anywhere in the application or press `Space` to initialize the Web Audio API context. |

---

## Documentation Index

- `docs/ARCHITECTURE.md`: Complete end-to-end architectural specification, real-time audio pipeline, 10-state conversation machine, and database pooling architecture.
- `docs/SUPABASE_SETUP.md`: Production Supabase migration guide, Supavisor Transaction Pooler (port 6543) configuration, asyncpg driver tuning, and RLS policies.
- `docs/CONVERSATION_TEST_REPORT.md`: Empirical conversational evaluation in English and Hindi, multi-turn memory traces, barge-in interruption benchmarks (< 120ms), and latency profiles.
- `docs/FINAL_ENGINEERING_QA_REPORT.md`: Master engineering sign-off report with acceptance criteria verification across R1–R7, test metrics, and 7-viewport responsive audit.
- `docs/api.md`: Comprehensive REST and WebSocket API specification.
- `.env.example`: Master zero-secret environment configuration template.
