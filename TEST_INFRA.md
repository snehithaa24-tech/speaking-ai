# E2E Test Infra: SAHAYAK AI

## Test Philosophy
- **Opaque-Box & Requirement-Driven**: Tests interact strictly through external and public contracts: HTTP endpoints (`/health`, `/api/v1/sessions`, `/api/v1/auth/google`, `/api/v1/knowledge/search`, `/api/v1/feedback`) and WebSocket channels (`/ws/live/{session_id}`). Tests validate observable behavior, status codes, payload structures, and protocol sequences without depending on internal private helper functions.
- **Methodology**: Systematic 4-tier testing adhering to Category-Partitioning, Boundary Value Analysis (BVA), Pairwise Combinatorial Testing, and Real-World Citizen Workload Testing.
- **Deterministic & Offline-Capable**: Includes a high-fidelity in-memory ASGI test harness emulating Gemini Live protocol exchanges (audio streaming, turn-taking, tool calls, and barge-in interruptions) so tests run reliably in sub-second time without external quota exhaustion or network flakiness, while providing an opt-in `--real-gemini` flag for live Google API integration verification when quota is available.

---

## Feature Inventory
| # | Feature | Source (Requirement) | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Workload) |
|---|---------|----------------------|:-----------------:|:-----------------:|:-----------------:|:-----------------:|
| F1 | Strict Two-Language Policy (`en-IN`, `hi-IN`, purge `te-IN`) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F2 | Real-Time Audio & Bidirectional WebSocket Streaming | ORIGINAL_REQUEST §R2 | 6 | 5 | ✓ | ✓ |
| F3 | Multi-Turn Memory & Barge-In User Interruption | ORIGINAL_REQUEST §R2, §R3 | 5 | 5 | ✓ | ✓ |
| F4 | Async DB Lifecycle & SQLite Local Dev Resilience | ORIGINAL_REQUEST §R4 | 5 | 4 | ✓ | ✓ |
| F5 | Google OAuth & Cryptographic Session Security | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| F6 | 10-State Conversation Machine & Frontend A11y Contracts | ORIGINAL_REQUEST §R6 | 5 | 3 | ✓ | ✓ |
| F7 | Knowledge Retrieval & Citizen Domain Services | ORIGINAL_REQUEST §R7, PROJECT §Architecture | 5 | 3 | ✓ | ✓ |

**Total Test Count Goal**:
- Tier 1: 36 tests (≥5 per feature across 7 features)
- Tier 2: 25 tests (≥5 boundary/corner cases for features with limits/parameters)
- Tier 3: 16 tests (Pairwise interactions: barge-in + memory, auth + sessions, language switch + streaming)
- Tier 4: 10 tests (Real-world citizen multi-turn scenarios: agriculture, health, emergency, transit, accessibility)
- **Overall Suite Size**: 87 test cases (exceeding minimum requirement of $11 \times 7 + \max(5, 3) = 82$).

---

## Test Architecture
- **Runner**: Pytest 9.2+ with `pytest-asyncio` running in `backend\venv` Python 3.12 environment.
- **Test Invocations**:
  - Full E2E suite (instant in-process ASGI execution):
    ```powershell
    backend\venv\Scripts\pytest.exe backend\tests\e2e -v
    ```
  - Opt-in Live Network Integration test:
    ```powershell
    backend\venv\Scripts\pytest.exe backend\tests\e2e -v -m real_gemini
    ```
- **In-Memory Opaque Test Client Architecture**:
  - Asynchronous HTTP Client: `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")`
  - Synchronous / Async WebSocket Client: `starlette.testclient.TestClient(app)` connecting to `/ws/live/{session_id}?token={token}`
  - Isolated In-Memory Database: `sqlite+aiosqlite:///:memory:` with clean table provisioning and knowledge seeding per session.
  - Mock Gemini Live Harness: Intercepts `GeminiLiveService.create_live_session` to return deterministic bidirectional mock streams simulating Gemini Live audio, text transcripts, and interruption behavior.

### Directory Layout
```
backend/tests/e2e/
├── conftest.py                       # Fixtures: ASGI test client, WebSocket client, DB lifecycle, Mock/Real Gemini harness
├── test_tier1_feature_coverage.py     # Tier 1: 36 tests covering API endpoints, languages, sessions, and WebSocket lifecycle
├── test_tier2_boundary_corner.py      # Tier 2: 25 tests covering invalid tokens, bad schemas, malformed frames, parameter limits
├── test_tier3_cross_feature.py        # Tier 3: 16 tests covering interruption, multi-turn memory, auth+sessions, tool loops
└── test_tier4_application_scenarios.py# Tier 4: 10 tests covering citizen journeys (PM-KISAN, Ayushman Bharat, 108 ambulance, etc.)
```

---

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity | Description |
|---|----------|--------------------|------------|-------------|
| S1 | PM-KISAN Scheme Inquiry (Hindi) | F1, F2, F3, F7 | High | Farmer asks about next 2000 INR installment in Hindi; assistant accesses knowledge base and details DBT timeline. |
| S2 | Ayushman Bharat Hospital Search (English) | F1, F2, F7 | Medium | Citizen searches for PMJAY empanelled private/government hospitals nearby for surgery. |
| S3 | Medical Emergency & 108 Ambulance Dispatch | F1, F2, F3, F7 | High | User urgently reports chest pain; assistant immediately provides 108 emergency protocol and nearest cardiac care. |
| S4 | Paddy Crop Pest Yellow Leaf Advisory (Hindi) | F1, F2, F7 | Medium | Farmer describes yellowing paddy leaves; assistant returns ICAR-recommended dosage of pesticide. |
| S5 | Rural Bus Transit Timings (English) | F1, F2, F7 | Medium | Commuter checks evening state transport bus schedules between rural hub and district center. |
| S6 | Accessibility Repeat & Slow-Pace Request | F1, F2, F3, F6 | Medium | Elderly user asks assistant to repeat the previous advice louder and clearly. |
| S7 | Rapid User Barge-in Interruption Mid-Explanation | F2, F3 | High | Assistant is midway through explaining 5 steps of a government scheme when user interrupts to ask for toll-free number. |
| S8 | Bilingual Hinglish Conversational Query | F1, F2, F3 | Medium | Citizen uses colloquial Hinglish phrasing; assistant comprehends context and replies naturally in Hindi. |
| S9 | Full Authentication, Session & Star Feedback Journey | F4, F5, F6 | High | User logs in via OAuth, opens voice session, converses, disconnects, and leaves 5-star feedback. |
| S10 | Gemini Live Upstream Fallback Resilience | F2, F3, F4 | Medium | Simulated upstream API degradation triggers polite user notification without 500 error or crash. |

---

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 isolated tests per feature (total ≥36 tests).
- **Tier 2 (Boundary & Corner Cases)**: ≥5 tests for token security, payload validation, numerical parameters, and state extremes (total ≥25 tests).
- **Tier 3 (Cross-Feature Combinations)**: ≥15 pairwise tests linking streaming, barge-in, auth, database, and language switching (total ≥16 tests).
- **Tier 4 (Real-World Application Scenarios)**: ≥10 multi-turn end-user citizen workloads in Hindi and English.
- **Verification Rule**: 100% test pass rate with exit code 0 under `backend\venv\Scripts\pytest.exe backend\tests\e2e`.
