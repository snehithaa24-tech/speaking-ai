"""Tier 2: Boundary & Corner Cases Test Suite (25 Tests).

Validates security boundaries, protocol edge cases, and numerical/schema limits:
- Token Security Boundaries (6 tests)
- Message Payload Corner Cases (6 tests)
- Parameter & Schema Boundaries (6 tests)
- Database & State Boundaries (7 tests)
"""

import base64
import pytest
import httpx
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.schemas.schemas import LanguageCode


# ---------------------------------------------------------------------------
# Group 1: Token Security Boundaries (6 tests)
# ---------------------------------------------------------------------------

def test_ws_missing_token_rejected_1008(ws_client: TestClient):
    """Connecting without a token query parameter is rejected with policy violation (1008)."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with ws_client.websocket_connect("/ws/live/sess-no-token"):
            pass
    assert exc_info.value.code == 1008


def test_ws_tampered_token_payload_rejected_1008(ws_client: TestClient, session_token_factory):
    """Connecting with a tampered token payload is closed with policy violation (1008)."""
    session_id = "sess-tampered"
    token = session_token_factory(session_id=session_id, tampered=True)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 1008


def test_ws_expired_token_rejected_1008(ws_client: TestClient, session_token_factory):
    """Connecting with an expired token is closed with policy violation (1008)."""
    session_id = "sess-expired"
    token = session_token_factory(session_id=session_id, expired=True)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 1008


def test_ws_mismatched_session_id_rejected_1008(ws_client: TestClient, session_token_factory):
    """Connecting to session B using a token minted for session A is rejected (1008)."""
    token = session_token_factory(session_id="session_A")
    with ws_client.websocket_connect(f"/ws/live/session_B?token={token}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 1008


def test_ws_malformed_base64_token_rejected_1008(ws_client: TestClient, session_token_factory):
    """Connecting with non-base64 garbage token string is rejected (1008)."""
    session_id = "sess-malformed"
    token = session_token_factory(session_id=session_id, malformed=True)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 1008


@pytest.mark.asyncio
async def test_auth_jwt_expired_returns_401(http_client: httpx.AsyncClient, auth_token_factory):
    """GET /api/v1/auth/me with an expired JWT access token returns 401 Unauthorized."""
    expired_token = auth_token_factory(user_id="user_123", expired=True)
    response = await http_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Group 2: Message Payload Corner Cases (6 tests)
# ---------------------------------------------------------------------------

def test_ws_malformed_json_frame_does_not_crash(ws_client: TestClient, session_token_factory):
    """Sending non-JSON raw string does not crash WebSocket server; subsequent messages work."""
    session_id = "sess-malformed-json"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_text("{bad-json-payload-without-closing-brace")
        # Ensure server remains operational
        ws.send_json({"type": "text", "payload": {"text": "Ping"}})
        resp = ws.receive_json()
        assert resp["type"] in ("audio", "text")


def test_ws_unknown_message_type_ignored_gracefully(ws_client: TestClient, session_token_factory):
    """Sending an unrecognized message type is ignored gracefully without server fault."""
    session_id = "sess-unknown-type"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_json({"type": "unsupported_custom_event_xyz", "payload": {"foo": "bar"}})
        ws.send_json({"type": "text", "payload": {"text": "Still active?"}})
        resp = ws.receive_json()
        assert resp["type"] in ("audio", "text")


def test_ws_empty_audio_payload_handled(ws_client: TestClient, session_token_factory):
    """Sending audio type with empty base64 string is handled safely."""
    session_id = "sess-empty-audio"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_json({"type": "audio", "payload": {"data": ""}})
        # Connection remains healthy
        ws.send_json({"type": "text", "payload": {"text": "After empty audio"}})
        resp = ws.receive_json()
        assert resp["type"] in ("audio", "text")


def test_ws_corrupt_base64_audio_handled(ws_client: TestClient, session_token_factory):
    """Sending corrupted base64 audio payload does not crash server."""
    session_id = "sess-corrupt-audio"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_json({"type": "audio", "payload": {"data": "###corrupt!not-base64###"}})
        ws.send_json({"type": "text", "payload": {"text": "After corrupt audio"}})
        resp = ws.receive_json()
        assert resp["type"] in ("audio", "text")


def test_ws_oversized_audio_chunk_buffered_without_overflow(ws_client: TestClient, session_token_factory):
    """Sending oversized 64KB audio chunk is received without memory buffer overflow."""
    session_id = "sess-oversized-audio"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        large_pcm = b"\x00" * (64 * 1024)
        large_b64 = base64.b64encode(large_pcm).decode()
        ws.send_json({
            "type": "audio",
            "payload": {
                "data": large_b64,
                "mime_type": "audio/pcm;rate=16000",
            },
        })
        resp = ws.receive_json()
        assert resp["type"] in ("audio", "text")


def test_ws_rapid_fire_text_messages_queued(ws_client: TestClient, session_token_factory):
    """Sending multiple rapid-fire messages consecutively is handled sequentially."""
    session_id = "sess-rapid-fire"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        for i in range(5):
            ws.send_json({"type": "text", "payload": {"text": f"Rapid message {i}"}})
        # Server produces response without dropping connection
        resp = ws.receive_json()
        assert resp["type"] in ("audio", "text")


# ---------------------------------------------------------------------------
# Group 3: Parameter & Schema Boundaries (6 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_create_temperature_min_boundary_0(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions accepts minimum valid temperature 0.0."""
    payload = {
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Deterministic instruction",
            "temperature": 0.0,
            "maxOutputTokens": 1000,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_session_create_temperature_max_boundary_1(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions accepts maximum valid temperature 1.0."""
    payload = {
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "Creative instruction",
            "temperature": 1.0,
            "maxOutputTokens": 1000,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_session_create_temperature_out_of_bounds_422(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions rejects temperature > 1.0 with 422."""
    payload = {
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Invalid temperature",
            "temperature": 1.5,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_session_create_max_tokens_min_boundary_1(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions accepts minimum valid maxOutputTokens 1."""
    payload = {
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Short response",
            "maxOutputTokens": 1,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_session_create_max_tokens_max_boundary_8192(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions accepts maximum valid maxOutputTokens 8192."""
    payload = {
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "Long response",
            "maxOutputTokens": 8192,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_session_create_max_tokens_out_of_bounds_422(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions rejects maxOutputTokens > 8192 with 422."""
    payload = {
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Excessive tokens",
            "maxOutputTokens": 9999,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Group 4: Database & State Boundaries (7 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feedback_rating_boundary_min_1(http_client: httpx.AsyncClient):
    """POST /api/v1/feedback accepts minimum valid rating 1."""
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {"language": "en-IN", "voiceName": "Kore", "systemInstruction": "Test"}
    })
    session_id = sess_res.json()["sessionId"]

    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": session_id,
        "rating": 1,
    })
    assert fb_res.status_code == 201
    assert fb_res.json()["rating"] == 1


@pytest.mark.asyncio
async def test_feedback_rating_boundary_max_5(http_client: httpx.AsyncClient):
    """POST /api/v1/feedback accepts maximum valid rating 5."""
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {"language": "hi-IN", "voiceName": "Kore", "systemInstruction": "Test"}
    })
    session_id = sess_res.json()["sessionId"]

    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": session_id,
        "rating": 5,
    })
    assert fb_res.status_code == 201
    assert fb_res.json()["rating"] == 5


@pytest.mark.asyncio
async def test_feedback_rating_invalid_zero_422(http_client: httpx.AsyncClient):
    """POST /api/v1/feedback rejects rating 0 with 422."""
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {"language": "en-IN", "voiceName": "Kore", "systemInstruction": "Test"}
    })
    session_id = sess_res.json()["sessionId"]

    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": session_id,
        "rating": 0,
    })
    assert fb_res.status_code == 422


@pytest.mark.asyncio
async def test_feedback_rating_invalid_six_422(http_client: httpx.AsyncClient):
    """POST /api/v1/feedback rejects rating 6 with 422."""
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {"language": "en-IN", "voiceName": "Kore", "systemInstruction": "Test"}
    })
    session_id = sess_res.json()["sessionId"]

    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": session_id,
        "rating": 6,
    })
    assert fb_res.status_code == 422


@pytest.mark.asyncio
async def test_knowledge_search_empty_query_422(http_client: httpx.AsyncClient):
    """POST /api/v1/knowledge/search rejects empty string query with 422."""
    payload = {
        "query": "",
        "language": "en-IN",
    }
    response = await http_client.post("/api/v1/knowledge/search", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_knowledge_search_special_characters_sql_injection_safe(http_client: httpx.AsyncClient):
    """Search queries containing SQL meta-characters are parameterized and injection-safe."""
    malicious_query = "' OR '1'='1; DROP TABLE knowledge_documents; --"
    payload = {
        "query": malicious_query,
        "language": "en-IN",
    }
    response = await http_client.post("/api/v1/knowledge/search", json=payload)
    assert response.status_code == 200
    # Ensure database table was not dropped
    check_res = await http_client.get("/api/v1/knowledge/categories")
    assert check_res.status_code == 200


@pytest.mark.asyncio
async def test_knowledge_search_extreme_length_query(http_client: httpx.AsyncClient):
    """POST /api/v1/knowledge/search: boundary at 500 chars returns 200; 501 chars returns 422."""
    valid_boundary_query = "a" * 500
    res_valid = await http_client.post("/api/v1/knowledge/search", json={
        "query": valid_boundary_query,
        "language": "en-IN",
    })
    assert res_valid.status_code == 200

    over_boundary_query = "a" * 501
    res_invalid = await http_client.post("/api/v1/knowledge/search", json={
        "query": over_boundary_query,
        "language": "en-IN",
    })
    assert res_invalid.status_code == 422
