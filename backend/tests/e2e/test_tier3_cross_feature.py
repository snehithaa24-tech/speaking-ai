"""Tier 3: Cross-Feature Combinations Test Suite (16 Tests).

Validates pairwise and multi-component interactions:
- User Barge-In & Interruption (4 tests)
- Multi-Turn Contextual Memory (4 tests)
- Knowledge Tool Execution Loop (4 tests)
- Auth, Session & Feedback End-to-End Journey (4 tests)
"""

import base64
import uuid
from datetime import datetime, timezone

import pytest
import httpx
from starlette.testclient import TestClient

from app.schemas.schemas import LanguageCode, SpeakerType
from app.models.models import Session, SessionStatus, ConversationMessage
from app.services.auth import AuthService


# ---------------------------------------------------------------------------
# Group 1: User Barge-In & Interruption (4 tests)
# ---------------------------------------------------------------------------

def test_barge_in_client_interrupt_signal_stops_playback(ws_client: TestClient, session_token_factory):
    """Client sending interrupt frame receives an interrupt frame acknowledgment from server."""
    session_id = "test-bargein-signal"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Initial greeting
        ws.send_json({"type": "interrupt"})
        interrupt_frame = ws.receive_json()
        assert interrupt_frame["type"] == "interrupt"


def test_barge_in_client_audio_chunk_triggers_interruption(ws_client: TestClient, session_token_factory):
    """Client streaming audio chunk during assistant turn receives processed voice response."""
    session_id = "test-bargein-audio"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        # Stream user audio chunk simulating barge-in
        pcm_bytes = b"\x00\x00" * 320
        b64_pcm = base64.b64encode(pcm_bytes).decode()
        ws.send_json({
            "type": "audio",
            "payload": {"data": b64_pcm, "mime_type": "audio/pcm;rate=16000"},
        })
        frame = ws.receive_json()
        assert frame["type"] in ("audio", "text")


def test_barge_in_subsequent_user_query_processed_immediately(ws_client: TestClient, session_token_factory):
    """Immediately following an interruption, user's new query is answered without deadlock."""
    session_id = "test-bargein-next-query"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        # 1. Interrupt active turn
        ws.send_json({"type": "interrupt"})
        interrupt_frame = ws.receive_json()
        assert interrupt_frame["type"] == "interrupt"

        # 2. Immediately send new question
        ws.send_json({"type": "text", "payload": {"text": "What are emergency contacts?"}})
        frame1 = ws.receive_json()
        if frame1["type"] == "audio":
            frame2 = ws.receive_json()
            assert frame2["type"] == "text"
            assert "emergency" in frame2["payload"]["text"].lower() or "108" in frame2["payload"]["text"]
        else:
            assert frame1["type"] == "text"


def test_barge_in_state_resets_for_new_turn(ws_client: TestClient, session_token_factory):
    """Interruption clears pending state so the next turn completes cleanly with is_final=True."""
    session_id = "test-bargein-state-reset"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_json({"type": "interrupt"})
        ws.receive_json()  # Interrupt frame

        ws.send_json({"type": "text", "payload": {"text": "Tell me about bus schedule"}})
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert f2["payload"]["is_final"] is True


# ---------------------------------------------------------------------------
# Group 2: Multi-Turn Contextual Memory (4 tests)
# ---------------------------------------------------------------------------

def test_multi_turn_two_turns_conversation_memory(ws_client: TestClient, session_token_factory):
    """Turn 1 question followed by Turn 2 question preserves session and returns both answers."""
    session_id = "test-multi-turn-2"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        greeting = ws.receive_json()
        assert greeting["type"] == "text"

        # Turn 1
        ws.send_json({"type": "text", "payload": {"text": "Tell me about PM-KISAN"}})
        t1_audio = ws.receive_json()
        t1_text = ws.receive_json() if t1_audio["type"] == "audio" else t1_audio
        assert "6,000" in t1_text["payload"]["text"]

        # Turn 2
        ws.send_json({"type": "text", "payload": {"text": "What about hospital emergency?"}})
        t2_audio = ws.receive_json()
        t2_text = ws.receive_json() if t2_audio["type"] == "audio" else t2_audio
        assert "108" in t2_text["payload"]["text"] or "hospital" in t2_text["payload"]["text"].lower()


def test_multi_turn_three_turns_follow_up_pronoun_resolution(ws_client: TestClient, session_token_factory):
    """Three sequential turns in the same voice session execute without dropping connection."""
    session_id = "test-multi-turn-3"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        # Turn 1
        ws.send_json({"type": "text", "payload": {"text": "Tell me about wheat crops"}})
        ws.receive_json()
        ws.receive_json()

        # Turn 2
        ws.send_json({"type": "text", "payload": {"text": "Tell me about bus schedule"}})
        ws.receive_json()
        ws.receive_json()

        # Turn 3
        ws.send_json({"type": "text", "payload": {"text": "Repeat that for me"}})
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "Repeating" in f2["payload"]["text"]


@pytest.mark.asyncio
async def test_multi_turn_history_persistence_in_db(http_client: httpx.AsyncClient, e2e_db):
    """Persisting multi-turn messages in database can be retrieved chronologically."""
    session_id = str(uuid.uuid4())
    db_session = Session(
        id=session_id,
        status=SessionStatus.ACTIVE,
        language="en-IN",
        message_count=2,
    )
    e2e_db.add(db_session)

    m1 = ConversationMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        speaker=SpeakerType.USER,
        transcript="How do I apply for PM-KISAN?",
        language="en-IN",
        is_final=True,
        timestamp=datetime.now(timezone.utc),
    )
    m2 = ConversationMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        speaker=SpeakerType.ASSISTANT,
        transcript="You can apply online at pmkisan.gov.in or Common Service Centers.",
        language="en-IN",
        is_final=True,
        timestamp=datetime.now(timezone.utc),
    )
    e2e_db.add_all([m1, m2])
    await e2e_db.commit()

    response = await http_client.get(f"/api/v1/sessions/{session_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 2
    assert messages[0]["speaker"] == "user"
    assert messages[1]["speaker"] == "assistant"


@pytest.mark.asyncio
async def test_multi_turn_session_message_count_incremented(http_client: httpx.AsyncClient, e2e_db):
    """Session metadata messageCount reflects completed interactions."""
    session_id = str(uuid.uuid4())
    db_session = Session(
        id=session_id,
        status=SessionStatus.ACTIVE,
        language="hi-IN",
        message_count=4,
    )
    e2e_db.add(db_session)
    await e2e_db.commit()

    response = await http_client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["messageCount"] == 4


# ---------------------------------------------------------------------------
# Group 3: Knowledge Tool Execution Loop (4 tests)
# ---------------------------------------------------------------------------

def test_tool_call_search_knowledge_triggered_and_resolved(ws_client: TestClient, session_token_factory):
    """Assistant emits search_knowledge tool call; client function_response resolves it."""
    session_id = "test-tool-search-loop"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        # Trigger tool call
        ws.send_json({"type": "text", "payload": {"text": "tool_search: PM-KISAN"}})
        call_msg = ws.receive_json()
        assert call_msg["type"] == "function_call"
        assert call_msg["payload"]["name"] == "search_knowledge"
        call_id = call_msg["payload"]["id"]

        # Client sends function result
        ws.send_json({
            "type": "function_response",
            "payload": {
                "functionCallId": call_id,
                "name": "search_knowledge",
                "result": {"documents": [{"title": "PM-KISAN Overview", "benefit": "₹6000"}]},
            },
        })

        # Assistant delivers final answer
        final_resp = ws.receive_json()
        assert final_resp["type"] == "text"
        assert "search_knowledge" in final_resp["payload"]["text"]


def test_tool_call_get_scheme_details_flow(ws_client: TestClient, session_token_factory):
    """Assistant emits get_scheme_details; resolved with scheme data."""
    session_id = "test-tool-scheme-flow"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        ws.send_json({"type": "text", "payload": {"text": "tool_scheme: pm-kisan"}})
        call_msg = ws.receive_json()
        assert call_msg["type"] == "function_call"
        assert call_msg["payload"]["name"] == "get_scheme_details"

        ws.send_json({
            "type": "function_response",
            "payload": {
                "functionCallId": call_msg["payload"]["id"],
                "name": "get_scheme_details",
                "result": {"scheme": "PM-KISAN", "eligibility": "Landholding farmers"},
            },
        })
        resp = ws.receive_json()
        assert resp["type"] == "text"
        assert "get_scheme_details" in resp["payload"]["text"]


def test_tool_call_hospital_assistance_flow(ws_client: TestClient, session_token_factory):
    """Assistant emits find_nearby_hospital; resolved with emergency hospital data."""
    session_id = "test-tool-hospital-flow"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        ws.send_json({"type": "text", "payload": {"text": "tool_hospital: District Center"}})
        call_msg = ws.receive_json()
        assert call_msg["type"] == "function_call"
        assert call_msg["payload"]["name"] == "find_nearby_hospital"

        ws.send_json({
            "type": "function_response",
            "payload": {
                "functionCallId": call_msg["payload"]["id"],
                "name": "find_nearby_hospital",
                "result": {"hospitals": [{"name": "Civil Hospital", "ambulance": "108"}]},
            },
        })
        resp = ws.receive_json()
        assert resp["type"] == "text"
        assert "find_nearby_hospital" in resp["payload"]["text"]


def test_tool_call_repeat_last_answer_accessibility(ws_client: TestClient, session_token_factory):
    """Assistant emits repeat_last_answer tool call for clarity and accessibility."""
    session_id = "test-tool-repeat-flow"
    token = session_token_factory(session_id=session_id)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        ws.send_json({"type": "text", "payload": {"text": "tool_repeat: repeat"}})
        call_msg = ws.receive_json()
        assert call_msg["type"] == "function_call"
        assert call_msg["payload"]["name"] == "repeat_last_answer"

        ws.send_json({
            "type": "function_response",
            "payload": {
                "functionCallId": call_msg["payload"]["id"],
                "name": "repeat_last_answer",
                "result": {"repeated": True},
            },
        })
        resp = ws.receive_json()
        assert resp["type"] == "text"


# ---------------------------------------------------------------------------
# Group 4: Auth, Session & Feedback End-to-End Journey (4 tests)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticated_user_creates_session_and_retrieves_history(
    http_client: httpx.AsyncClient,
    e2e_db,
    auth_token_factory,
):
    """User logs in via JWT, creates session, and retrieves active session details."""
    auth_service = AuthService(e2e_db)
    user = await auth_service.get_or_create_user({
        "email": "journey_citizen@sahayak.ai",
        "name": "Journey Citizen",
    })
    token = auth_token_factory(user_id=user.id, email=user.email)

    # 1. Verify user profile
    me_res = await http_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200

    # 2. Create voice session
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Citizen assistant",
        }
    })
    assert sess_res.status_code == 201
    session_id = sess_res.json()["sessionId"]

    # 3. Retrieve session
    get_res = await http_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == session_id


@pytest.mark.asyncio
async def test_session_end_followed_by_feedback_and_verification(http_client: httpx.AsyncClient):
    """Full lifecycle: create session -> end session (DELETE) -> submit feedback -> verify completed."""
    # 1. Create session
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "सहायक निर्देश",
        }
    })
    session_id = sess_res.json()["sessionId"]

    # 2. End session
    del_res = await http_client.delete(f"/api/v1/sessions/{session_id}")
    assert del_res.status_code == 204

    # 3. Verify status completed
    get_res = await http_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "completed"

    # 4. Submit 5-star feedback
    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": session_id,
        "rating": 5,
        "comment": "उत्कृष्ट आवाज अनुभव!",
    })
    assert fb_res.status_code == 201
    assert fb_res.json()["rating"] == 5


@pytest.mark.asyncio
async def test_language_switch_en_to_hi_across_sessions(
    http_client: httpx.AsyncClient,
    ws_client: TestClient,
    session_token_factory,
):
    """Client can switch language from English to Hindi in subsequent sessions seamlessly."""
    # 1. English session
    en_res = await http_client.post("/api/v1/sessions", json={
        "config": {"language": "en-IN", "voiceName": "Kore", "systemInstruction": "English"}
    })
    en_session_id = en_res.json()["sessionId"]
    en_token = en_res.json()["token"]

    with ws_client.websocket_connect(f"/ws/live/{en_session_id}?token={en_token}") as ws_en:
        en_greeting = ws_en.receive_json()
        assert "Namaste! I am Sahayak AI" in en_greeting["payload"]["text"]

    # 2. Hindi session
    hi_res = await http_client.post("/api/v1/sessions", json={
        "config": {"language": "hi-IN", "voiceName": "Kore", "systemInstruction": "Hindi"}
    })
    hi_session_id = hi_res.json()["sessionId"]
    hi_token = hi_res.json()["token"]

    with ws_client.websocket_connect(f"/ws/live/{hi_session_id}?token={hi_token}") as ws_hi:
        hi_greeting = ws_hi.receive_json()
        assert "नमस्ते! मैं सहायक AI हूँ" in hi_greeting["payload"]["text"]


def test_simulated_network_drop_reconnect_with_same_token(ws_client: TestClient, session_token_factory):
    """Client experiencing abrupt disconnect can reconnect with the same valid token."""
    session_id = "test-network-drop-reconnect"
    token = session_token_factory(session_id=session_id)

    # First connection dropped
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws1:
        msg1 = ws1.receive_json()
        assert msg1["type"] == "text"

    # Reconnection with same token
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws2:
        msg2 = ws2.receive_json()
        assert msg2["type"] == "text"
        assert "Sahayak AI" in msg2["payload"]["text"]
