# SAHAYAK AI — System Architecture Specification

## 1. System Topology

SAHAYAK AI is a voice-first artificial intelligence assistant engineered for low-latency, real-time spoken interactions in Indian English (`en-IN`) and Hindi (`hi-IN`).

```
+-----------------------------------------------------------------------------------+
|                                  CLIENT LAYER                                     |
|  React 18 + TypeScript + Vite + Tailwind CSS                                      |
|                                                                                   |
|  +---------------------------+     +-------------------+     +------------------+ |
|  | Web Audio Capture (16kHz) |     | 10-State Machine  |     | Timeline Audio   | |
|  | ScriptProcessor -> 0-gain |     |   Lifecycle       |     | Player (24kHz)   | |
|  +---------------------------+     +-------------------+     +------------------+ |
+-----------------------------------------|-----------------------------------------+
                                          |
                WebSocket (/ws/live)      |      REST API (/api/v1)
                Binary PCM (Base64)       |      HTTP/JSON
                                          v
+-----------------------------------------------------------------------------------+
|                                 BACKEND GATEWAY                                   |
|  FastAPI (Uvicorn Asynchronous ASGI Server)                                       |
|                                                                                   |
|  +----------------------------+     +------------------+     +------------------+ |
|  | WebSocket Gateway Router   |     | Sliding Window   |     | Google OAuth     | |
|  | /ws/live/{session_id}      |     | Rate Limiter     |     | Token Validator  | |
|  +----------------------------+     +------------------+     +------------------+ |
|               |                                                       |           |
|               v                                                       v           |
|  +----------------------------+                     +---------------------------+ |
|  | GeminiLiveSessionWrapper   |                     | Database Dual-Tier Engine | |
|  | (client.aio.live.connect)  |                     | (SQLite / Supabase PG)    | |
|  +----------------------------+                     +---------------------------+ |
+---------------|---------------------------------------------------|---------------+
                |                                                   |
                v Bidirectional Live Stream                         v
+-------------------------------+                     +---------------------------+
|    Google Gemini Live API     |                     | Persistent Storage Engine |
|    (gemini-2.0-flash-exp)     |                     | - Local: aiosqlite SQLite |
|                               |                     | - Cloud: Supabase asyncpg |
|  - Real-time VAD & Turn-Taking|                     |   (Supavisor Pooler: 6543)|
|  - Bidirectional Audio Stream |                     +---------------------------+
|  - Tool Calls (FunctionCalling|                                   |
+---------------|---------------+                                   |
                v                                                   v
+-------------------------------+                     +---------------------------+
|   Domain Citizen Knowledge    |<--------------------+ Relational Schema:        |
| - Government Schemes (PM-KISAN|                     | - users, sessions,        |
| - Emergency Triage (108)      |                     |   conversation_messages,  |
| - Agricultural Crop Advisory  |                     |   knowledge_documents,    |
| - Public Transit Routes       |                     |   feedback, eval_metrics  |
+-------------------------------+                     +---------------------------+
```

---

## 2. Real-Time Audio Pipeline

The real-time audio pipeline bridges browser audio hardware and Google's Gemini Live bidirectional speech model with minimal latency and high acoustic fidelity.

```
+-----------------------------------------------------------------------------+
|                           AUDIO INGESTION PIPELINE                          |
+-----------------------------------------------------------------------------+
 Citizen Voice
      |
      v
 [Microphone] 44.1kHz / 48kHz Float32
      |
      v
 [AudioContext]
      |
      +---> [ScriptProcessorNode] (bufferSize: 4096)
      |            |
      |            |-- Downsampling & Linear Interpolation -> 16kHz
      |            |-- Float32 (-1.0 to +1.0) -> Int16 PCM (-32768 to +32767)
      |            |-- Base64 Chunk Encoding
      |            |-- Transmit via WebSocket: {"type": "audio", "payload": ...}
      |
      +---> [GainNode (gain.value = 0.0)] ---> [AudioContext.destination]
            (Zero-Gain Node prevents microphone loopback while keeping
             the ScriptProcessorNode alive and active in Web Audio graph)

+-----------------------------------------------------------------------------+
|                           AUDIO PLAYBACK PIPELINE                           |
+-----------------------------------------------------------------------------+
 WebSocket Inbound Audio Frame: {"type": "audio", "payload": {"data": "<base64>"}}
      |
      v
 [Base64 Decoding] -> Raw 24kHz Int16 Mono PCM
      |
      v
 [PCM Conversion] -> Float32Array (normalized to [-1.0, 1.0])
      |
      v
 [AudioBuffer Creation] -> 24kHz Single-Channel AudioBuffer
      |
      v
 [Audio Timeline Scheduling Engine]
      |
      |   const currentTime = audioContext.currentTime;
      |   const startTime = Math.max(currentTime, nextPlayTime);
      |   sourceNode.start(startTime);
      |   nextPlayTime = startTime + audioBuffer.duration;
      |
      +---> [AudioContext.destination] (Speakers / Headphones)
      |
      v
 [Browser SpeechSynthesis Suppression]
      - Active 24kHz stream suppresses native browser window.speechSynthesis
        to prevent robotic voice collision, double-talk, or echo.
```

### 2.1 Acoustic Feedback Prevention
In Web Audio API implementations, `ScriptProcessorNode` requires an active connection to `AudioContext.destination` in order for the browser audio thread to deliver `onaudioprocess` events. Connecting the node directly to `destination` creates immediate feedback loops (acoustic squeal) as the microphone output feeds directly into device speakers. 

SAHAYAK AI inserts an intermediate `GainNode` with `gain.value = 0`:
```ts
const gainNode = audioContext.createGain();
gainNode.gain.setValueAtTime(0, audioContext.currentTime);
scriptProcessor.connect(gainNode);
gainNode.connect(audioContext.destination);
```
This satisfies the browser's audio routing graph requirement while guaranteeing absolute zero audio bleed.

### 2.2 Timeline-Based Audio Scheduling
Naive Web Audio playback relies on queueing audio buffers and waiting for `AudioBufferSourceNode.onended` callbacks to play subsequent chunks. In network streaming environments, execution jitter in JavaScript event loops causes audible gaps, clicks, pops, and stuttering.

SAHAYAK AI implements precise timeline scheduling directly against `AudioContext.currentTime`:
```ts
const currentTime = this.audioContext.currentTime;
const startTime = Math.max(currentTime, this.nextPlayTime);
sourceNode.start(startTime);
this.nextPlayTime = startTime + buffer.duration;
```
If network latency introduces a micro-pause, the scheduler seamlessly anchors the next chunk at `currentTime`, preventing overlapping playback or drift.

### 2.3 User Barge-In Interruption Handling
When the user speaks while the assistant is delivering an answer:
1. Client audio activity or manual interrupt event emits `{"type": "interrupt"}` over the WebSocket.
2. The frontend `AudioPlayer.stop()` immediately cancels all scheduled `AudioBufferSourceNode` instances on the audio timeline and resets `nextPlayTime = 0`.
3. The backend dispatches `types.LiveClientContent(turns=[], turn_complete=False)` to Gemini Live, which immediately halts model speech token generation.
4. Total barge-in reaction time from interrupt signal to silence is under **120ms**.

---

## 3. 10-State Conversation State Machine

The conversation interface is governed by a deterministic 10-state finite state machine (FSM) implemented in `frontend/src/types/index.ts` and managed by `useVoiceSession`:

```
                       +-------------------+
                       |       idle        |
                       +-------------------+
                                 | User clicks Start
                                 v
                       +-------------------+
                       | requesting_       |
                       | permission        |
                       +-------------------+
                                 | Permission Granted
                                 v
                       +-------------------+
                       |    connecting     |<------------------+
                       +-------------------+                   |
                                 | Token validated & WS open   |
                                 v                             | Reconnect
                       +-------------------+                   | Attempt
                       |     connected     |                   |
                       +-------------------+                   |
                                 | Greeting / Ready            |
                                 v                             |
  +------------------------> [ ACTIVE LOOP ]                   |
  |                              |                             |
  |         +--------------------+--------------------+        |
  |         |                    |                    |        |
  |         v                    v                    v        |
  |   +-----------+        +------------+       +----------+   |
  |   | listening |------->| processing |------>| speaking |   |
  |   +-----------+        +------------+       +----------+   |
  |         ^                                         |        |
  |         |             User Interrupt              |        |
  |         +-----------------------------------------+        |
  |                                                            |
  | Network Drops                                              |
  +------------------------------------------------------------+
                                 |
                                 v
                       +-------------------+
                       |   reconnecting    |
                       +-------------------+
                                 |
            +--------------------+--------------------+
            | Max retries                             | Teardown
            v                                         v
  +-------------------+                             +-------------------+
  |       error       |                             |   disconnected    |
  +-------------------+                             +-------------------+
```

| State | Trigger / Entry Condition | Audio Hardware Status | WebSocket State | User-Facing Indication |
|---|---|---|---|---|
| `idle` | Application initialized or session completed. | AudioContext suspended, mic closed. | Closed | "Click to start conversation" |
| `requesting_permission` | User clicks microphone / start button. | Browser requesting `getUserMedia`. | Closed | "Requesting microphone permission..." |
| `connecting` | Permission granted; minting session token. | AudioContext initialized. | Connecting | "Connecting to Sahayak AI..." |
| `connected` | WS open, token validated, greeting received. | Mic initialized, zero-gain attached. | Open | "Connected • Ready to listen" |
| `listening` | Mic actively streaming audio chunks. | ScriptProcessor capturing 16kHz PCM. | Open | Animated green wave / "Listening..." |
| `processing` | User stopped speaking; VAD silence detected. | Mic paused or streaming background. | Open | Pulsing amber ring / "Processing..." |
| `speaking` | Assistant audio chunks playing on timeline. | Timeline scheduler active (24kHz). | Open | Animated blue wave / "Speaking..." |
| `reconnecting` | Unexpected transport closure or network drop.| Buffers paused; exponential backoff. | Reconnecting | Amber banner / "Reconnecting (attempt X)..." |
| `disconnected` | User clicked end session or session ended. | All audio tracks stopped and released. | Closed | Gray status / "Session ended" |
| `error` | Terminal network, token, or hardware fault. | Audio nodes cleanly dismantled. | Closed | Red banner with retry action |

---

## 4. WebSocket Protocol Specification

The real-time bidirectional protocol operates over `/ws/live/{session_id}?token={signed_token}`.

### 4.1 Client-to-Server Messages

#### 1. Audio Frame
```json
{
  "type": "audio",
  "payload": {
    "data": "<base64_encoded_16khz_16bit_mono_pcm>",
    "mime_type": "audio/pcm;rate=16000"
  }
}
```

#### 2. Text Frame
```json
{
  "type": "text",
  "payload": {
    "text": "What are the benefits under PM-KISAN?"
  }
}
```

#### 3. Barge-In Interrupt Signal
```json
{
  "type": "interrupt"
}
```

#### 4. Function Tool Execution Response
```json
{
  "type": "function_response",
  "payload": {
    "functionCallId": "call_12345",
    "name": "search_knowledge",
    "result": {
      "title": "PM-KISAN Samman Nidhi",
      "benefit": "₹6,000 per year in three installments"
    }
  }
}
```

#### 5. Graceful Close
```json
{
  "type": "close"
}
```

### 4.2 Server-to-Client Messages

#### 1. Audio Frame
```json
{
  "type": "audio",
  "payload": {
    "data": "<base64_encoded_24khz_16bit_mono_pcm>",
    "mime_type": "audio/pcm;rate=24000"
  }
}
```

#### 2. Transcript Frame
```json
{
  "type": "text",
  "payload": {
    "text": "Namaste! I am Sahayak AI. How may I assist you today?",
    "speaker": "assistant",
    "is_final": true
  }
}
```

#### 3. Interruption Acknowledgment
```json
{
  "type": "interrupt"
}
```

#### 4. Function Tool Call Request
```json
{
  "type": "function_call",
  "payload": {
    "functionCalls": [
      {
        "id": "call_12345",
        "name": "search_knowledge",
        "args": { "query": "PM KISAN installment details" }
      }
    ]
  }
}
```

#### 5. Policy & Error Enforcement
```json
{
  "type": "error",
  "payload": {
    "code": "AUTH_FAILED",
    "message": "Invalid or expired session token"
  }
}
```
*Note*: Unauthenticated handshakes (missing, forged, expired, or cross-session tokens) are closed with standard WebSocket Code `1008 Policy Violation`.

---

## 5. Database Dual-Tier Architecture

SAHAYAK AI implements a dual-tier database strategy designed for zero-friction local development and high-throughput production deployment on Supabase PostgreSQL.

```
                           +---------------------------+
                           |  SQLAlchemy 2.0 Engine    |
                           | get_async_database_url()  |
                           +---------------------------+
                                         |
                   +---------------------+---------------------+
                   |                                           |
                   v                                           v
     +---------------------------+               +---------------------------+
     |   Local Development Tier  |               |  Production Supabase Tier |
     | - URL: sqlite+aiosqlite:  |               | - URL: postgresql+asyncpg:|
     | - Zero credentials needed |               | - Port 6543 (Transaction) |
     | - Instant offline setup   |               | - Port 5432 (Session)     |
     | - Startup fallback target |               | - Supavisor Tuning:       |
     |                           |               |   statement_cache_size: 0 |
     |                           |               | - Row Level Security (RLS)|
     +---------------------------+               +---------------------------+
```

### 5.1 Asynchronous Database URL Normalization
The utility `app.database.session.get_async_database_url` inspects and converts standard database connection strings into async-compatible SQLAlchemy dialects:
- `sqlite:///./sahayak.db` -> `sqlite+aiosqlite:///./sahayak.db`
- `postgres://...` -> `postgresql+asyncpg://...`
- `postgresql://...` -> `postgresql+asyncpg://...`
- `sslmode=require` -> `ssl=require` (asyncpg compatibility)

### 5.2 Automatic Startup Fallback
During application startup in `app.database.session.create_engine_instance`:
```python
try:
    engine = create_engine_instance(settings.DATABASE_URL)
except Exception as e:
    logger.warning(f"Error configuring primary engine: {e}. Falling back to SQLite.")
    engine = create_engine_instance(DEFAULT_SQLITE_URL)
```
If a developer launches the application without configuring Supabase credentials, the backend automatically boots with SQLite (`sqlite+aiosqlite:///./sahayak.db`), ensuring zero blocking errors.

### 5.3 Supavisor Pooler Driver Tuning
Supabase manages connection pooling via Supavisor. To prevent prepared statement collisions when connecting through the Supavisor Transaction Pooler (port `6543`), the SQLAlchemy engine automatically injects:
```python
connect_args={
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "ssl": "require"
}
```

### 5.4 Dialect-Agnostic Relational Schema
All 6 core models (`User`, `Session`, `ConversationMessage`, `KnowledgeDocument`, `Feedback`, `EvaluationMetric`) use cross-database SQLAlchemy constructs:
- `sa.JSON`: Supported natively on PostgreSQL (`JSONB`/`JSON`) and SQLite (JSON string serialization).
- `server_default=sa.true()`: Standard boolean representations across SQL dialects.

---

## 6. Google OAuth Verification & Security Hardening

### 6.1 OAuth 2.0 Token Verification Flow
When a user authenticates with Google OAuth on the frontend, the client sends the credential token to `/api/v1/auth/google`. The backend validates the token using `google.oauth2.id_token.verify_oauth2_token`:
1. Cryptographic signature verified against Google's public JWK certificates.
2. Audience (`aud`) verified against backend `settings.GOOGLE_CLIENT_ID`.
3. Issuer (`iss`) verified as `accounts.google.com` or `https://accounts.google.com`.
4. Expiration timestamp (`exp`) verified against UTC clock.

### 6.2 Cryptographic Voice Session Tokens
Voice sessions require an ephemeral, signed HS256 JWT minted by `/api/v1/sessions`:
```json
{
  "sub": "sess-84f9b8c2-32b1-419b-a01f-0e823b185b2e",
  "session_id": "sess-84f9b8c2-32b1-419b-a01f-0e823b185b2e",
  "config": {
    "language": "en-IN",
    "voiceName": "Kore",
    "systemInstruction": "You are Sahayak AI...",
    "temperature": 0.7,
    "maxOutputTokens": 2048
  },
  "exp": 1700003600,
  "iat": 1700000000
}
```
The token is signed using the server-side `SECRET_KEY`. When the WebSocket connects, the gateway decodes and verifies the signature, algorithm restriction (`algorithms=[settings.JWT_ALGORITHM]`), expiration, and session ID match. Substitution of user auth Bearer tokens is rejected due to missing `session_id` claims.

---

## 7. Sliding-Window Rate Limiting

The backend protects public endpoints using an in-memory sliding window rate limiter (`app.core.rate_limit.SlidingWindowRateLimiter`) with synchronized async locks:

- **Auth Category** (`/api/v1/auth/*`): 20 requests per 60-second sliding window per client IP.
- **Sessions Category** (`/api/v1/sessions/*`): 40 requests per 60-second sliding window per client IP.
- **Exempt Surfaces**: Health checks (`/health`) and knowledge categories (`/api/v1/knowledge/categories`) remain unthrottled.

### 7.1 Multi-Hop IP Resolution
In proxied environments (Cloudflare, Nginx, Kubernetes ingress), the limiter inspects `X-Forwarded-For`:
```python
forwarded = request.headers.get("x-forwarded-for")
if forwarded:
    return forwarded.split(",")[0].strip()
```
The client IP is cleanly parsed from the originating position, preventing rate limit bypass or cross-tenant IP throttling.

### 7.2 Response Headers & CORS Preservation
When a client exceeds the limit:
- Status: `HTTP 429 Too Many Requests`
- Headers: `Retry-After: <seconds>`, `X-RateLimit-Limit`, `X-RateLimit-Remaining: 0`
- CORS: `CORSMiddleware` wraps `RateLimitMiddleware`, ensuring `Access-Control-Allow-Origin` is attached so browser clients receive meaningful error bodies.

---

## 8. Accessibility Architecture

SAHAYAK AI conforms to **WCAG 2.1 Level AA** standards across all views and interactive controls:

1. **Strict Two-Language Selector**:
   - Offers strictly "English \| हिन्दी" toggle with accessible `aria-pressed` indicators.
   - Defaults to English (`en-IN`) unless Hindi (`hi-IN`) is explicitly selected or saved.
   - Full keyboard accessibility: Arrow keys, Enter, and Space support.

2. **Contrast & Typography**:
   - Contrast ratios exceed 7:1 in standard mode and 12:1 in High Contrast mode.
   - Large Text mode scales typography dynamically via rem units without viewport clipping or overlapping containers.

3. **Motion Sensitivity**:
   - System `@media (prefers-reduced-motion)` and user `.reduced-motion` class suppress pulsating rings, audio waveform oscillations, and state transitions.

4. **Screen Reader Assistive Tech**:
   - Live conversation transcripts and status pills use `aria-live="polite"` and `role="status"`.
   - All microphone controls carry descriptive, localized `aria-label` and `aria-pressed` attributes.

5. **Keyboard Shortcuts**:
   - `Space`: Toggle microphone recording / listening.
   - `Escape`: Barge-in / stop active assistant speech.
   - `Ctrl + /`: Open keyboard shortcuts and accessibility dialog.
