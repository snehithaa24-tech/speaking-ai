import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone
from jose import jwt
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.services.gemini_live import gemini_live_service
from app.schemas.schemas import VoiceSessionConfig, LanguageCode
from app.main import app
from app.core.rate_limit import SlidingWindowRateLimiter


# ---------------------------------------------------------
# Fixture: Rate Limiter Reset
# ---------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_rate_limiter_fixture():
    """Ensure rate limiter buckets are completely fresh before and after every security test."""
    if hasattr(app.state, "rate_limiter"):
        app.state.rate_limiter.reset()
    yield
    if hasattr(app.state, "rate_limiter"):
        app.state.rate_limiter.reset()


# ---------------------------------------------------------
# 1. Rate Limiting Tests
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_rate_limit_auth_20_req_per_min(client: AsyncClient):
    """Exceeding 20 req/min on /api/v1/auth/ returns HTTP 429 with Retry-After header."""
    headers = {"X-Forwarded-For": "198.51.100.1"}

    # 20 allowed requests
    for i in range(20):
        resp = await client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401, f"Expected 401 on request {i+1}, got {resp.status_code}"

    # 21st request must trigger 429
    blocked_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert blocked_resp.status_code == 429
    assert "Retry-After" in blocked_resp.headers
    retry_after = int(blocked_resp.headers["Retry-After"])
    assert retry_after > 0
    assert "Rate limit exceeded" in blocked_resp.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limit_sessions_40_req_per_min(client: AsyncClient):
    """Exceeding 40 req/min on /api/v1/sessions returns HTTP 429 with Retry-After header."""
    headers = {"X-Forwarded-For": "198.51.100.2"}

    # 40 allowed requests
    for i in range(40):
        resp = await client.get("/api/v1/sessions/nonexistent-id", headers=headers)
        assert resp.status_code == 404, f"Expected 404 on request {i+1}, got {resp.status_code}"

    # 41st request must trigger 429
    blocked_resp = await client.get("/api/v1/sessions/nonexistent-id", headers=headers)
    assert blocked_resp.status_code == 429
    assert "Retry-After" in blocked_resp.headers
    retry_after = int(blocked_resp.headers["Retry-After"])
    assert retry_after > 0
    assert "Rate limit exceeded" in blocked_resp.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limit_exempt_endpoints_not_blocked(client: AsyncClient):
    """Health check and knowledge endpoints are exempt from rate limiting."""
    headers = {"X-Forwarded-For": "198.51.100.3"}

    # Send 50 requests to /health
    for _ in range(50):
        resp = await client.get("/health", headers=headers)
        assert resp.status_code == 200

    # Knowledge categories also unaffected
    k_resp = await client.get("/api/v1/knowledge/categories", headers=headers)
    assert k_resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_ip_isolation(client: AsyncClient):
    """Exhausting rate limit for one IP does not block a distinct client IP."""
    ip_a_headers = {"X-Forwarded-For": "198.51.100.10"}
    ip_b_headers = {"X-Forwarded-For": "198.51.100.20"}

    # Exhaust IP A (20 requests)
    for _ in range(20):
        await client.get("/api/v1/auth/me", headers=ip_a_headers)
    resp_a = await client.get("/api/v1/auth/me", headers=ip_a_headers)
    assert resp_a.status_code == 429

    # IP B is unaffected
    resp_b = await client.get("/api/v1/auth/me", headers=ip_b_headers)
    assert resp_b.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_options_preflight_exempt(client: AsyncClient):
    """OPTIONS preflight requests are exempt from rate limiting."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "X-Forwarded-For": "198.51.100.5",
    }
    # 50 preflights should all succeed
    for _ in range(50):
        resp = await client.options("/api/v1/sessions", headers=headers)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiter_stale_cleanup():
    """Rate limiter removes inactive keys older than window."""
    limiter = SlidingWindowRateLimiter(cleanup_interval_seconds=1.0)
    now = 1000.0

    # Record requests at t=1000
    limited, _ = await limiter.is_rate_limited("client_old", "auth", 20, window_seconds=60.0, now=now)
    assert not limited
    assert ("client_old", "auth") in limiter._requests

    # Advance time past window (t=1065) and trigger check
    limited, _ = await limiter.is_rate_limited("client_new", "auth", 20, window_seconds=60.0, now=now + 65.0)
    assert not limited

    # Old client key should have been evicted
    assert ("client_old", "auth") not in limiter._requests
    assert ("client_new", "auth") in limiter._requests


# ---------------------------------------------------------
# 2. Cryptographic Voice Session Token Tests
# ---------------------------------------------------------
def test_session_token_valid_claims_and_signature():
    """Validly signed token decodes with claims sub, session_id, config, iat, exp."""
    config = VoiceSessionConfig(
        language=LanguageCode.EN_IN,
        voice_name="Kore",
        system_instruction="Instruction test",
    )
    session_id = "sess-crypto-valid-12345"
    token = gemini_live_service.create_session_token(session_id, config, user_id="user-999")

    decoded = gemini_live_service.verify_session_token(token)
    assert decoded is not None
    assert decoded["session_id"] == session_id
    assert decoded["sub"] == session_id
    assert decoded["user_id"] == "user-999"
    assert decoded["config"]["language"] == "en-IN"
    assert "exp" in decoded
    assert "iat" in decoded
    assert decoded["exp"] > decoded["iat"]


def test_session_token_tampered_payload_rejected():
    """Modifying the session_id or config in the JWT payload invalidates the signature."""
    config = VoiceSessionConfig(language=LanguageCode.EN_IN, voice_name="Kore", system_instruction="I")
    token = gemini_live_service.create_session_token("session-victim", config)

    # Tamper payload
    header, payload_b64, sig = token.split(".")
    import base64
    import json
    # Pad base64 if needed
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    payload["session_id"] = "session-attacker"
    tampered_payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    tampered_token = f"{header}.{tampered_payload_b64}.{sig}"

    assert gemini_live_service.verify_session_token(tampered_token) is None


def test_session_token_forged_signature_rejected():
    """Token signed with an unauthorized secret key is rejected."""
    payload = {
        "sub": "session-forged",
        "session_id": "session-forged",
        "config": {"language": "en-IN"},
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    forged_token = jwt.encode(payload, "unauthorized_forged_secret_key_1234567890", algorithm="HS256")
    assert gemini_live_service.verify_session_token(forged_token) is None


def test_session_token_expired_rejected():
    """Token with an expired exp claim is rejected."""
    payload = {
        "sub": "session-expired",
        "session_id": "session-expired",
        "config": {"language": "en-IN"},
        "exp": int((datetime.now(timezone.utc) - timedelta(seconds=10)).timestamp()),
        "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
    }
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    assert gemini_live_service.verify_session_token(expired_token) is None


def test_session_token_legacy_raw_base64_rejected():
    """Unsigned raw base64 token is rejected."""
    import base64
    import json
    raw_token = base64.urlsafe_b64encode(json.dumps({"session_id": "raw-id"}).encode()).decode()
    assert gemini_live_service.verify_session_token(raw_token) is None


def test_ws_connection_rejects_invalid_token():
    """WebSocket connection with invalid token query param is closed with WS 1008."""
    client = TestClient(app)
    with client.websocket_connect("/ws/live/sess-test-invalid?token=invalid_forged_token") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


def test_ws_connection_rejects_session_mismatch():
    """WebSocket connection where URL session_id does not match token session_id closes with WS 1008."""
    config = VoiceSessionConfig(language=LanguageCode.EN_IN, voice_name="Kore", system_instruction="I")
    token = gemini_live_service.create_session_token("session-A", config)
    client = TestClient(app)
    with client.websocket_connect(f"/ws/live/session-B?token={token}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


# ---------------------------------------------------------
# 3. CORS Hardening Tests
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_cors_allows_localhost_5173(client: AsyncClient):
    resp = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_allows_127_0_0_1_5173(client: AsyncClient):
    resp = await client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_preflight_options(client: AsyncClient):
    resp = await client.options(
        "/api/v1/sessions",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


@pytest.mark.asyncio
async def test_cors_blocks_unauthorized_origin(client: AsyncClient):
    resp = await client.get("/health", headers={"Origin": "http://unauthorized-domain.com"})
    assert resp.headers.get("access-control-allow-origin") != "http://unauthorized-domain.com"


@pytest.mark.asyncio
async def test_cors_headers_present_on_429_response(client: AsyncClient):
    """HTTP 429 rate limit response must carry CORS headers so browsers do not drop the response."""
    headers = {
        "Origin": "http://localhost:5173",
        "X-Forwarded-For": "198.51.100.99",
    }
    # Exhaust auth limit
    for _ in range(20):
        await client.get("/api/v1/auth/me", headers=headers)
    blocked_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert blocked_resp.status_code == 429
    assert blocked_resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ---------------------------------------------------------
# 4. Secret Exposure Audit Tests
# ---------------------------------------------------------
def test_settings_repr_does_not_leak_secrets():
    """Settings string representation must mask SECRET_KEY, GEMINI_API_KEY, and GOOGLE_CLIENT_SECRET."""
    repr_str = repr(settings)
    assert settings.SECRET_KEY not in repr_str
    assert settings.GEMINI_API_KEY not in repr_str
    if settings.GOOGLE_CLIENT_SECRET:
        assert settings.GOOGLE_CLIENT_SECRET not in repr_str
