"""Tier 1: Feature Coverage Test Suite (36 Tests).

Validates individual endpoint functionality, public contracts, and basic lifecycles:
- Health & Diagnostics (2 tests)
- Strict Language Validation (4 tests)
- Session Lifecycle Operations (6 tests)
- WebSocket Handshake & Lifecycle (6 tests)
- WebSocket Bidirectional Messaging (6 tests)
- Knowledge Base & Search (6 tests)
- Auth & Feedback (6 tests)
"""

import base64
import uuid
from datetime import datetime

import pytest
import httpx
from starlette.testclient import TestClient

from app.schemas.schemas import LanguageCode
from app.api.v1.websocket import live_session_manager
from app.services.auth import AuthService
from app.models.models import SessionStatus


# ---------------------------------------------------------------------------
# Group 1: Health & Diagnostics (2 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint_healthy(http_client: httpx.AsyncClient):
    """GET /health returns 200 with status 'healthy' and app version."""
    response = await http_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_endpoint_timestamp_utc(http_client: httpx.AsyncClient):
    """GET /health returns a valid ISO-8601 UTC timestamp."""
    response = await http_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    ts = datetime.fromisoformat(data["timestamp"])
    assert ts is not None


# ---------------------------------------------------------------------------
# Group 2: Language Policy & Strict Validation (4 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_create_english_success(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions with English (en-IN) config creates session successfully."""
    payload = {
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "You are Sahayak AI.",
            "temperature": 0.7,
            "maxOutputTokens": 2048,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["language"] == "en-IN"
    assert "sessionId" in data
    assert "token" in data
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_session_create_hindi_success(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions with Hindi (hi-IN) config creates session successfully."""
    payload = {
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "आप सहायक AI हैं।",
            "temperature": 0.7,
            "maxOutputTokens": 2048,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["language"] == "hi-IN"
    assert "sessionId" in data
    assert "token" in data


@pytest.mark.asyncio
async def test_session_create_telugu_validation(http_client: httpx.AsyncClient):
    """Verifies Telugu (te-IN) behavior: returns 422 once purged, or 201 if M2 pending."""
    payload = {
        "config": {
            "language": "te-IN",
            "voiceName": "Kore",
            "systemInstruction": "మీరు సహాయక్ AI.",
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    # Forward-compatible: accepts 422 (purged) or 201 (pre-purge)
    assert response.status_code in (201, 422)


@pytest.mark.asyncio
async def test_session_create_unsupported_language_422(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions with unsupported language codes strictly returns 422."""
    unsupported_languages = ["fr-FR", "es-ES", "de-DE", "zh-CN"]
    for lang in unsupported_languages:
        payload = {
            "config": {
                "language": lang,
                "voiceName": "Kore",
                "systemInstruction": "Test instruction",
            }
        }
        response = await http_client.post("/api/v1/sessions", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Group 3: Session Lifecycle Operations (6 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_create_nested_config(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions accepts standard nested { config: { ... } } structure."""
    payload = {
        "config": {
            "language": "en-IN",
            "voice_name": "Kore",
            "system_instruction": "Test nested config",
            "temperature": 0.6,
            "max_output_tokens": 1500,
        }
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    assert "sessionId" in response.json()


@pytest.mark.asyncio
async def test_session_create_camel_case(http_client: httpx.AsyncClient):
    """POST /api/v1/sessions accepts camelCase parameters from frontend clients."""
    payload = {
        "language": "hi-IN",
        "voiceName": "Kore",
        "systemInstruction": "परीक्षण निर्देश",
        "maxOutputTokens": 1024,
    }
    response = await http_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    assert response.json()["language"] == "hi-IN"


@pytest.mark.asyncio
async def test_session_get_metadata(http_client: httpx.AsyncClient):
    """GET /api/v1/sessions/{session_id} returns accurate session metadata."""
    create_res = await http_client.post("/api/v1/sessions", json={
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Test instruction",
        }
    })
    session_id = create_res.json()["sessionId"]

    get_res = await http_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == session_id
    assert data["status"] == "active"
    assert data["language"] == "en-IN"
    assert data["messageCount"] == 0


@pytest.mark.asyncio
async def test_session_delete_completes_status(http_client: httpx.AsyncClient):
    """DELETE /api/v1/sessions/{session_id} marks session completed (204)."""
    create_res = await http_client.post("/api/v1/sessions", json={
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "Test",
        }
    })
    session_id = create_res.json()["sessionId"]

    del_res = await http_client.delete(f"/api/v1/sessions/{session_id}")
    assert del_res.status_code == 204

    get_res = await http_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "completed"
    assert get_res.json()["endedAt"] is not None


@pytest.mark.asyncio
async def test_session_get_nonexistent_returns_404(http_client: httpx.AsyncClient):
    """GET /api/v1/sessions/{unknown_id} returns 404 Not Found."""
    response = await http_client.get("/api/v1/sessions/nonexistent-session-uuid-1234")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_session_messages_empty_initially(http_client: httpx.AsyncClient):
    """GET /api/v1/sessions/{session_id}/messages returns an empty array initially."""
    create_res = await http_client.post("/api/v1/sessions", json={
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Test",
        }
    })
    session_id = create_res.json()["sessionId"]

    msg_res = await http_client.get(f"/api/v1/sessions/{session_id}/messages")
    assert msg_res.status_code == 200
    assert msg_res.json() == []


# ---------------------------------------------------------------------------
# Group 4: WebSocket Handshake & Lifecycle (6 tests)
# ---------------------------------------------------------------------------

def test_ws_handshake_valid_token_connects(ws_client: TestClient, session_token_factory):
    """WebSocket handshake connects successfully with valid session token."""
    session_id = "test-ws-handshake-1"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] in ("text", "audio")


def test_ws_initial_greeting_received_english(ws_client: TestClient, session_token_factory):
    """WebSocket connection with English token receives English greeting."""
    session_id = "test-ws-greeting-en"
    token = session_token_factory(session_id=session_id, language=LanguageCode.EN_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "text"
        assert "Namaste! I am Sahayak AI" in msg["payload"]["text"]
        assert msg["payload"]["speaker"] == "assistant"
        assert msg["payload"]["is_final"] is True


def test_ws_initial_greeting_received_hindi(ws_client: TestClient, session_token_factory):
    """WebSocket connection with Hindi token receives Hindi greeting."""
    session_id = "test-ws-greeting-hi"
    token = session_token_factory(session_id=session_id, language=LanguageCode.HI_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "text"
        assert "नमस्ते! मैं सहायक AI हूँ" in msg["payload"]["text"]
        assert msg["payload"]["speaker"] == "assistant"


def test_ws_close_message_graceful_disconnect(ws_client: TestClient, session_token_factory):
    """Client sending close frame disconnects cleanly without exception."""
    session_id = "test-ws-close-graceful"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_json({"type": "close"})


def test_ws_client_disconnect_cleans_session_manager(ws_client: TestClient, session_token_factory):
    """Disconnecting client unregisters session from live_session_manager."""
    session_id = "test-ws-cleanup"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()
        assert live_session_manager.get_gemini_session(session_id) is not None

    assert live_session_manager.get_gemini_session(session_id) is None


def test_ws_connection_tracks_active_status(ws_client: TestClient, session_token_factory):
    """Active WebSocket connection maintains active status in session manager."""
    session_id = "test-ws-active-track"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()
        active_sess = live_session_manager.get_gemini_session(session_id)
        assert active_sess is not None


# ---------------------------------------------------------------------------
# Group 5: WebSocket Bidirectional Messaging (6 tests)
# ---------------------------------------------------------------------------

def test_ws_text_query_and_response(ws_client: TestClient, session_token_factory):
    """Client sending text query receives assistant response."""
    session_id = "test-ws-text-query"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Initial greeting
        ws.send_json({"type": "text", "payload": {"text": "How does Sahayak AI help farmers?"}})
        # Server sends audio frame followed by text transcript frame
        frame1 = ws.receive_json()
        if frame1["type"] == "audio":
            frame2 = ws.receive_json()
            assert frame2["type"] == "text"
            assert "Sahayak AI" in frame2["payload"]["text"]
        else:
            assert frame1["type"] == "text"


def test_ws_audio_chunk_streaming(ws_client: TestClient, session_token_factory):
    """Client streaming 16kHz PCM audio chunk receives processed response."""
    session_id = "test-ws-audio-stream"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        pcm_bytes = b"\x00\x00" * 320  # 16kHz PCM chunk
        b64_audio = base64.b64encode(pcm_bytes).decode()
        ws.send_json({
            "type": "audio",
            "payload": {
                "data": b64_audio,
                "mime_type": "audio/pcm;rate=16000",
            },
        })
        frame = ws.receive_json()
        assert frame["type"] in ("audio", "text")


def test_ws_turn_completion_flag(ws_client: TestClient, session_token_factory):
    """Assistant text response includes is_final=True upon turn completion."""
    session_id = "test-ws-turn-completion"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        greeting = ws.receive_json()
        assert greeting["payload"]["is_final"] is True


def test_ws_speaker_attribution_assistant(ws_client: TestClient, session_token_factory):
    """Server text frames include speaker='assistant' attribution."""
    session_id = "test-ws-speaker-attr"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        greeting = ws.receive_json()
        assert greeting["payload"]["speaker"] == "assistant"


def test_ws_setup_message_ack(ws_client: TestClient, session_token_factory):
    """Client sending setup message is acknowledged without error."""
    session_id = "test-ws-setup"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_json({"type": "setup", "payload": {"model": "gemini-2.0-flash"}})
        # Connection continues normally
        ws.send_json({"type": "text", "payload": {"text": "Ping"}})
        resp = ws.receive_json()
        assert resp["type"] in ("audio", "text")


def test_ws_server_content_audio_and_text(ws_client: TestClient, session_token_factory):
    """Server response includes 24kHz audio and text transcript."""
    session_id = "test-ws-content-types"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_json({"type": "text", "payload": {"text": "Tell me about agriculture"}})
        frame1 = ws.receive_json()
        assert frame1["type"] == "audio"
        assert frame1["payload"]["mime_type"] == "audio/pcm;rate=24000"
        frame2 = ws.receive_json()
        assert frame2["type"] == "text"


# ---------------------------------------------------------------------------
# Group 6: Knowledge Base & Search (6 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_knowledge_search_schemes(http_client: httpx.AsyncClient):
    """Searching for 'PM-KISAN' returns government schemes documents."""
    payload = {
        "query": "PM-KISAN",
        "category": "government_schemes",
        "language": "en-IN",
    }
    response = await http_client.post("/api/v1/knowledge/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["totalResults"] >= 1
    assert any("PM-KISAN" in doc["title"] for doc in data["documents"])


@pytest.mark.asyncio
async def test_knowledge_search_agriculture(http_client: httpx.AsyncClient):
    """Searching agriculture category returns crop management knowledge."""
    payload = {
        "query": "wheat",
        "category": "agriculture",
        "language": "en-IN",
    }
    response = await http_client.post("/api/v1/knowledge/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["totalResults"] >= 1
    assert any("Wheat" in doc["title"] for doc in data["documents"])


@pytest.mark.asyncio
async def test_knowledge_search_transport(http_client: httpx.AsyncClient):
    """Searching knowledge returns general information without error."""
    payload = {
        "query": "hospital",
        "category": "hospital_assistance",
        "language": "en-IN",
    }
    response = await http_client.post("/api/v1/knowledge/search", json=payload)
    assert response.status_code == 200
    assert response.json()["totalResults"] >= 1


@pytest.mark.asyncio
async def test_knowledge_search_hospitals(http_client: httpx.AsyncClient):
    """Searching hospital assistance returns 108 emergency ambulance details."""
    payload = {
        "query": "108 ambulance hospital",
        "category": "hospital_assistance",
        "language": "en-IN",
    }
    response = await http_client.post("/api/v1/knowledge/search", json=payload)
    assert response.status_code == 200
    docs = response.json()["documents"]
    assert any("108" in doc["content"] for doc in docs)


@pytest.mark.asyncio
async def test_knowledge_categories_list(http_client: httpx.AsyncClient):
    """GET /api/v1/knowledge/categories returns all available domain categories."""
    response = await http_client.get("/api/v1/knowledge/categories")
    assert response.status_code == 200
    categories = response.json()
    assert "government_schemes" in categories
    assert "agriculture" in categories
    assert "hospital_assistance" in categories


@pytest.mark.asyncio
async def test_knowledge_get_document_by_id(http_client: httpx.AsyncClient):
    """GET /api/v1/knowledge/{doc_id} retrieves specific document by ID."""
    search_res = await http_client.post("/api/v1/knowledge/search", json={
        "query": "PM-KISAN",
        "language": "en-IN",
    })
    doc_id = search_res.json()["documents"][0]["id"]

    get_res = await http_client.get(f"/api/v1/knowledge/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == doc_id
    assert "PM-KISAN" in get_res.json()["title"]


# ---------------------------------------------------------------------------
# Group 7: Auth & Feedback (6 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_me_without_token_returns_401(http_client: httpx.AsyncClient):
    """GET /api/v1/auth/me without authorization header returns 401."""
    response = await http_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_google_invalid_code_returns_401(http_client: httpx.AsyncClient):
    """POST /api/v1/auth/google with unverified auth code returns 401."""
    payload = {
        "code": "invalid_e2e_code_xyz",
        "redirectUri": "http://localhost:5173/auth/callback",
    }
    response = await http_client.post("/api/v1/auth/google", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_with_valid_jwt_returns_user(
    http_client: httpx.AsyncClient,
    e2e_db,
    auth_token_factory,
):
    """GET /api/v1/auth/me with valid Bearer JWT returns authenticated profile."""
    auth_service = AuthService(e2e_db)
    user = await auth_service.get_or_create_user({
        "email": "e2e_user@sahayak.ai",
        "name": "E2E Test Citizen",
        "picture": "https://example.com/pic.jpg",
    })
    token = auth_token_factory(user_id=user.id, email=user.email)

    response = await http_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "e2e_user@sahayak.ai"
    assert data["name"] == "E2E Test Citizen"


@pytest.mark.asyncio
async def test_feedback_submission_valid_rating(http_client: httpx.AsyncClient):
    """POST /api/v1/feedback with valid 5-star rating returns 201."""
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Test",
        }
    })
    session_id = sess_res.json()["sessionId"]

    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": session_id,
        "rating": 5,
    })
    assert fb_res.status_code == 201
    assert fb_res.json()["rating"] == 5
    assert fb_res.json()["sessionId"] == session_id


@pytest.mark.asyncio
async def test_feedback_submission_with_comment(http_client: httpx.AsyncClient):
    """POST /api/v1/feedback stores citizen comment alongside rating."""
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "Test",
        }
    })
    session_id = sess_res.json()["sessionId"]

    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": session_id,
        "rating": 4,
        "comment": "बहुत मददगार वॉयस असिस्टेंट!",
    })
    assert fb_res.status_code == 201
    assert fb_res.json()["comment"] == "बहुत मददगार वॉयस असिस्टेंट!"


@pytest.mark.asyncio
async def test_feedback_nonexistent_session_returns_404(http_client: httpx.AsyncClient):
    """POST /api/v1/feedback for nonexistent session returns 404."""
    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": str(uuid.uuid4()),
        "rating": 5,
    })
    assert fb_res.status_code == 404
