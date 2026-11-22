# SAHAYAK AI — Complete Gemini API & Google OAuth Configuration Report

**Document:** `docs/SAHAYAK_AI_CREDENTIAL_CONFIGURATION_REPORT.md`  
**Date:** 2026-11-16  
**Lead Engineer:** Senior Full-Stack & Security Engineer  
**Workspace:** `D:\Own webs\ai voice`  
**Client ID Configured:** `398446910998-9s4te3s57ok4pjapitjpbvg2u4qtuo00.apps.googleusercontent.com`  

---

## 1. Files Inspected

1. `backend/app/core/config.py` — Settings schema, Pydantic settings parsing, and environment resolution.
2. `backend/app/api/v1/auth.py` — OAuth endpoint `/api/v1/auth/google` and user profile `/api/v1/auth/me`.
3. `backend/app/services/auth.py` — Token exchange, ID token validation, and JWT session issuing.
4. `backend/app/services/gemini_live.py` — Gemini Live client initialization, model configuration, and session bridge.
5. `backend/app/api/v1/websocket.py` — WebSocket gateway `/ws/live/{session_id}` and error handling.
6. `backend/.env` — Backend environment variables.
7. `frontend/src/contexts/AuthContext.tsx` — Client-side Google OAuth initiation and user state management.
8. `frontend/src/services/api.ts` — Frontend REST API service and authorization header injection.
9. `frontend/src/App.tsx` — React Router route definitions.
10. `frontend/src/vite-env.d.ts` — TypeScript environment variable declarations.
11. `.gitignore` — Repository ignore definitions.

---

## 2. Files Modified

1. **`frontend/.env` (Created):**
   - Configured `VITE_GOOGLE_CLIENT_ID=398446910998-9s4te3s57ok4pjapitjpbvg2u4qtuo00.apps.googleusercontent.com`.
   - Configured `VITE_API_URL` and `VITE_WS_URL`.
2. **`frontend/.env.example` (Created):**
   - Clean template with placeholders for frontend environment setup.
3. **`backend/.env` (Updated):**
   - Enabled OAuth: `ENABLE_OAUTH=true`.
   - Added `GOOGLE_CLIENT_ID=398446910998-9s4te3s57ok4pjapitjpbvg2u4qtuo00.apps.googleusercontent.com`.
   - Added `GOOGLE_CLIENT_SECRET=` placeholder.
4. **`backend/.env.example` (Created):**
   - Clean template with placeholders for backend deployment.
5. **`.env.example` (Updated):**
   - Unified master environment template.
6. **`frontend/src/vite-env.d.ts` (Modified):**
   - Removed unsafe declaration `readonly VITE_GEMINI_API_KEY: string;` to ensure no frontend component attempts or expects client-side Gemini keys.
7. **`backend/app/services/auth.py` (Modified):**
   - Implemented cryptographic Google token verification using `google.oauth2.id_token.verify_oauth2_token`.
   - Added audience verification (`aud == GOOGLE_CLIENT_ID`), issuer validation, and signature verification against Google's public certs.
   - Migrated to `datetime.now(timezone.utc)`.
8. **`backend/app/api/v1/auth.py` (Modified):**
   - Removed unused database imports (`AsyncSession`, `get_db`).
9. **`frontend/src/pages/AuthCallback.tsx` (Created):**
   - Complete OAuth callback route handler processing `code` and `error` search parameters from Google, exchanging tokens via `apiService.googleAuth`, and redirecting to `/conversation`.
10. **`frontend/src/App.tsx` (Modified):**
    - Mounted `/auth/callback` route.
11. **`frontend/src/services/api.ts` (Modified):**
    - Added `googleAuth(code, redirectUri)` and `getCurrentUser(token)`.
    - Automatically injects `Authorization: Bearer <token>` when a user token exists in `localStorage`.
12. **`frontend/src/contexts/AuthContext.tsx` (Modified):**
    - Cleans up `sahayak-token` on logout.
13. **`frontend/src/types/index.ts` (Modified):**
    - Exported `User` interface.
14. **`backend/tests/test_auth.py` (Created):**
    - 5 automated tests for `/auth/me`, `/auth/google`, and token generation.

---

## 3. Environment Variables Required

### Backend (`backend/.env`)
| Variable | Type | Description | Current Value / Setting |
|---|---|---|---|
| `GEMINI_API_KEY` | Secret (Backend only) | Google AI Studio Gemini API Key | Set in `backend/.env` (Placeholder currently active) |
| `GEMINI_LIVE_MODEL` | String | Live audio model | `gemini-2.0-flash-exp` |
| `GOOGLE_CLIENT_ID` | Public String | Google Cloud OAuth Client ID | `398446910998-9s4te3s57ok4pjapitjpbvg2u4qtuo00.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET`| Secret (Optional) | Client Secret for web server code exchange | Optional for ID token verification; recommended for Web App flow |
| `ENABLE_OAUTH` | Boolean | Activates OAuth endpoints | `true` |
| `SECRET_KEY` | Secret | JWT signing key | 32+ character random string |
| `DATABASE_URL` | String | SQLite development URL | `sqlite:///./sahayak.db` |
| `FRONTEND_URL` | String | Allowed CORS origin | `http://localhost:5173` |

### Frontend (`frontend/.env`)
| Variable | Type | Description | Current Value |
|---|---|---|---|
| `VITE_GOOGLE_CLIENT_ID` | Public String | Public OAuth client identifier | `398446910998-9s4te3s57ok4pjapitjpbvg2u4qtuo00.apps.googleusercontent.com` |
| `VITE_API_URL` | URL | Backend REST API path | `http://localhost:8000/api/v1` |
| `VITE_WS_URL` | URL | Backend WebSocket URL | `ws://localhost:8000` |

> [!CAUTION]
> Under no circumstances should `GEMINI_API_KEY`, `SECRET_KEY`, or `GOOGLE_CLIENT_SECRET` ever be placed in `frontend/.env` or prefixed with `VITE_`.

---

## 4. Exact Local Setup Instructions

### Step A: Configure Your Gemini API Key
1. Generate an API key from [Google AI Studio](https://aistudio.google.com/apikey).
2. Open `backend/.env` in your text editor.
3. Replace the placeholder on Line 4:
   ```env
   GEMINI_API_KEY=AIzaSyYourActualKeyHere
   ```
4. Save the file. The backend will automatically use this key on the next connection without restarting.

### Step B: Configure Google Cloud Console (Required for Real Login)
In the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) under your project for Client ID `398446910998-9s4te3s57ok4pjapitjpbvg2u4qtuo00.apps.googleusercontent.com`:

1. **Authorized JavaScript origins**:
   ```
   http://localhost:5173
   http://127.0.0.1:5173
   ```
2. **Authorized redirect URIs**:
   ```
   http://localhost:5173/auth/callback
   http://127.0.0.1:5173/auth/callback
   ```
3. If you have generated a Client Secret for this Web Application in Google Cloud Console, add it to `backend/.env`:
   ```env
   GOOGLE_CLIENT_SECRET=GOCSPX-YourClientSecretHere
   ```

---

## 5. Security Audit Results

| Check | Target | Result | Evidence |
|---|---|:---:|---|
| **No Gemini Key in Frontend** | `frontend/dist/` assets | **PASS** | Scanned all JS and CSS bundles. Zero occurrences of `AIzaSy` or `GEMINI_API_KEY`. |
| **No Secrets in Vite Env** | `frontend/src/vite-env.d.ts` | **PASS** | Removed dead `VITE_GEMINI_API_KEY` declaration. |
| **CORS Restriction** | `backend/app/main.py` | **PASS** | Restricts origins to `http://localhost:5173`. Arbitrary origins receive no CORS header. |
| **Stack Trace Suppression** | Exception handlers | **PASS** | Error responses output sanitized JSON errors without Python tracebacks. |
| **Token Audience Validation** | `backend/app/services/auth.py` | **PASS** | `id_token.verify_oauth2_token` validates `aud == GOOGLE_CLIENT_ID`. |
| **Git Credential Tracking** | `.gitignore` | **PASS** | `.env`, `frontend/.env`, `backend/.env`, and `*.db` are completely ignored. |

---

## 6. Test Results Matrix

### Backend Tests (Pytest) — 20 / 20 PASSED
- `test_auth_me_unauthorized` — **PASSED** (HTTP 401 on missing token)
- `test_auth_me_invalid_token` — **PASSED** (HTTP 401 on tampered token)
- `test_auth_google_invalid_code` — **PASSED** (HTTP 401 on unverified Google code)
- `test_auth_google_invalid_payload` — **PASSED** (HTTP 422 on bad body)
- `test_token_creation_and_auth_me_lifecycle` — **PASSED** (User creation & JWT validation roundtrip)
- `test_config_debug_property` — **PASSED**
- `test_config_defaults` — **PASSED**
- `test_get_categories` — **PASSED**
- `test_create_and_search_document` — **PASSED**
- `test_health_check` — **PASSED**
- `test_create_session_nested_config` — **PASSED**
- `test_create_session_camel_case` — **PASSED**
- `test_get_session_lifecycle` — **PASSED**
- `test_get_nonexistent_session` — **PASSED**
- `test_submit_feedback` — **PASSED**
- `test_submit_feedback_nonexistent_session` — **PASSED**
- `test_token_creation_and_verification` — **PASSED**
- `test_invalid_token_verification` — **PASSED**
- `test_live_tools_declarations` — **PASSED**
- `test_multilingual_system_instructions` — **PASSED**

### Backend Linter (Ruff)
- `ruff check backend` — **0 errors, 0 warnings** (18 unused imports cleaned).

### Frontend Verification
- `npm run typecheck` (`tsc --noEmit`) — **0 errors** (PASSED)
- `npm run lint` (`eslint . --max-warnings 0`) — **0 errors, 0 warnings** (PASSED)
- `npm test` (`vitest --run`) — **4/4 passed** in 2.07s (PASSED)
- `npm run build` (`vite build`) — **Built in 6.11s** cleanly into `dist/` (PASSED)

---

## 7. Exact Commands to Run Application

To launch both backend and frontend concurrently:
```bat
dev.bat
```

Or run in separate terminals:

**Terminal 1 (Backend):**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm run dev
```

---

## 8. Final Status Summary

| Component | Status | Details |
|---|:---:|---|
| **Gemini API Configuration** | **CONFIGURED** | Backend-only loader in place; graceful fallback alerts; model pinned to `gemini-2.0-flash-exp`. |
| **Gemini Live Real Connection** | **BLOCKED** | Requires user to supply a valid API key in `backend/.env` Line 4. |
| **Google OAuth Configuration** | **CONFIGURED** | Client ID `398446910998-...` configured in both `backend/.env` and `frontend/.env`; `/auth/callback` page and backend ID token verification implemented. |
| **Google OAuth Real Login** | **READY FOR USER AUTH** | Google Cloud Console authorized redirect URIs must include `http://localhost:5173/auth/callback`. |
| **Backend Health** | **EXCELLENT** | 20/20 Pytest passed; sub-10ms response latencies; 0 Ruff errors. |
| **Frontend Health** | **EXCELLENT** | Strict TypeScript check passed; 0 ESLint errors; production build succeeded. |
| **Security** | **VERIFIED** | Zero credentials in frontend bundles; token audience validated; CORS restricted. |
| **Production Readiness** | **HIGH** | Complete pending live API key and Google Cloud Console URI registration. |

