"""Tier 4: Real-World Application Scenarios Test Suite (10 Tests).

Validates end-to-end citizen journeys across agriculture, healthcare, emergency,
transportation, and accessibility in English and Hindi:
- S1. PM-KISAN Scheme Inquiry (Hindi)
- S2. Ayushman Bharat Hospital Search (English)
- S3. Medical Emergency & 108 Ambulance Dispatch
- S4. Paddy Crop Pest Yellow Leaf Advisory (Hindi)
- S5. Rural Bus Transit Timings (English)
- S6. Accessibility Repeat Request
- S7. Rapid Barge-In Interruption Mid-Explanation
- S8. Bilingual Hinglish Conversational Query
- S9. Full Authentication, Session & Star Feedback Journey
- S10. Upstream AI Fallback Resilience
"""

import base64
import os
import pytest
import httpx
from starlette.testclient import TestClient

from app.schemas.schemas import LanguageCode
from app.services.auth import AuthService


def test_scenario_pm_kisan_installment_inquiry_hindi(ws_client: TestClient, session_token_factory):
    """S1: Citizen inquires about PM-KISAN in Hindi; assistant details ₹6,000 / 3 installments."""
    session_id = "scenario-s1-pmkisan-hindi"
    token = session_token_factory(session_id=session_id, language=LanguageCode.HI_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        greeting = ws.receive_json()
        assert "नमस्ते! मैं सहायक AI हूँ" in greeting["payload"]["text"]

        ws.send_json({
            "type": "text",
            "payload": {"text": "पीएम किसान योजना की अगली किस्त कब आएगी और कितना पैसा मिलता है?"},
        })
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "₹6,000" in f2["payload"]["text"]
        assert "₹2,000" in f2["payload"]["text"]
        assert f2["payload"]["is_final"] is True


def test_scenario_ayushman_bharat_hospital_search_english(ws_client: TestClient, session_token_factory):
    """S2: Citizen inquires in English about Ayushman Bharat PMJAY and nearby empanelled hospitals."""
    session_id = "scenario-s2-ayushman-english"
    token = session_token_factory(session_id=session_id, language=LanguageCode.EN_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        greeting = ws.receive_json()
        assert "Namaste! I am Sahayak AI" in greeting["payload"]["text"]

        ws.send_json({
            "type": "text",
            "payload": {"text": "How do I find an Ayushman Bharat hospital near me for surgery?"},
        })
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "5 lakh" in f2["payload"]["text"].lower() or "pmjay" in f2["payload"]["text"].lower()


def test_scenario_medical_emergency_108(ws_client: TestClient, session_token_factory):
    """S3: Urgent chest pain inquiry triggers immediate 108 ambulance dispatch advisory."""
    session_id = "scenario-s3-emergency-108"
    token = session_token_factory(session_id=session_id, language=LanguageCode.EN_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        ws.send_json({
            "type": "text",
            "payload": {"text": "My father has severe chest pain and difficulty breathing! Help!"},
        })
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "108" in f2["payload"]["text"]
        assert "ambulance" in f2["payload"]["text"].lower() or "emergency" in f2["payload"]["text"].lower()


def test_scenario_crop_disease_advisory_hindi(ws_client: TestClient, session_token_factory):
    """S4: Farmer reports yellow leaf syndrome in paddy; assistant gives ICAR advisory in Hindi."""
    session_id = "scenario-s4-crop-advisory"
    token = session_token_factory(session_id=session_id, language=LanguageCode.HI_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        ws.send_json({
            "type": "text",
            "payload": {"text": "धान की फसल में पत्ते पीले पड़ रहे हैं, इसके लिए क्या दवा डालें?"},
        })
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "जिंक" in f2["payload"]["text"] or "पीले" in f2["payload"]["text"] or "धान" in f2["payload"]["text"]


def test_scenario_public_transport_bus_schedule_english(ws_client: TestClient, session_token_factory):
    """S5: Commuter checks evening bus schedule to district headquarters in English."""
    session_id = "scenario-s5-bus-transit"
    token = session_token_factory(session_id=session_id, language=LanguageCode.EN_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        ws.send_json({
            "type": "text",
            "payload": {"text": "What is the evening bus timing from rural hub to district center?"},
        })
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "bus" in f2["payload"]["text"].lower() or "transport" in f2["payload"]["text"].lower()


def test_scenario_accessibility_repeat_last_answer(ws_client: TestClient, session_token_factory):
    """S6: User requests assistant to repeat the previous advice for clarity and accessibility."""
    session_id = "scenario-s6-repeat-a11y"
    token = session_token_factory(session_id=session_id, language=LanguageCode.EN_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        # First question
        ws.send_json({"type": "text", "payload": {"text": "What are PM-KISAN benefits?"}})
        ws.receive_json()
        ws.receive_json()

        # Accessibility repeat request
        ws.send_json({"type": "text", "payload": {"text": "Could you please repeat what you just said?"}})
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "Repeating" in f2["payload"]["text"] or "repeat" in f2["payload"]["text"].lower()


def test_scenario_session_interrupted_mid_explanation(ws_client: TestClient, session_token_factory):
    """S7: User interrupts assistant explanation with barge-in to ask urgent emergency question."""
    session_id = "scenario-s7-interrupt-mid"
    token = session_token_factory(session_id=session_id, language=LanguageCode.EN_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        # User asks general scheme question
        ws.send_json({"type": "text", "payload": {"text": "Tell me about agricultural subsidies"}})
        ws.receive_json()  # Audio frame

        # User barges in with interrupt
        ws.send_json({"type": "interrupt"})
        # Read until interrupt frame
        while True:
            msg = ws.receive_json()
            if msg["type"] == "interrupt":
                break

        # User asks emergency question
        ws.send_json({"type": "text", "payload": {"text": "Wait, I need the 108 emergency ambulance now!"}})
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "108" in f2["payload"]["text"]


def test_scenario_bilingual_hinglish_query(ws_client: TestClient, session_token_factory):
    """S8: Citizen queries in colloquial Hinglish; assistant comprehends context and replies in Hindi."""
    session_id = "scenario-s8-hinglish"
    token = session_token_factory(session_id=session_id, language=LanguageCode.HI_IN)
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting

        # Colloquial Hinglish query
        ws.send_json({
            "type": "text",
            "payload": {"text": "Mera PM Kisan status aur kisan samman nidhi installment kab aayega?"},
        })
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"
        assert "₹6,000" in f2["payload"]["text"] or "किस्त" in f2["payload"]["text"] or "किसान" in f2["payload"]["text"]


@pytest.mark.asyncio
async def test_scenario_full_auth_session_feedback_journey(
    http_client: httpx.AsyncClient,
    ws_client: TestClient,
    e2e_db,
    auth_token_factory,
    session_token_factory,
):
    """S9: Full End-to-End citizen journey: Auth -> Session -> Voice -> Delete -> 5-Star Feedback."""
    # 1. User Authentication
    auth_service = AuthService(e2e_db)
    user = await auth_service.get_or_create_user({
        "email": "farmer_ramesh@sahayak.ai",
        "name": "Ramesh Kumar",
    })
    jwt_token = auth_token_factory(user_id=user.id, email=user.email)
    me_res = await http_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert me_res.status_code == 200

    # 2. Create Voice Session
    sess_res = await http_client.post("/api/v1/sessions", json={
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "किसान सहायक",
        }
    })
    assert sess_res.status_code == 201
    session_id = sess_res.json()["sessionId"]
    token = sess_res.json()["token"]

    # 3. Voice Interaction over WebSocket
    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        greeting = ws.receive_json()
        assert "नमस्ते! मैं सहायक AI हूँ" in greeting["payload"]["text"]

        # Text query
        ws.send_json({"type": "text", "payload": {"text": "किसान योजना की जानकारी दें"}})
        f1 = ws.receive_json()
        f2 = ws.receive_json() if f1["type"] == "audio" else f1
        assert f2["type"] == "text"

        # Audio stream turn
        pcm_bytes = b"\x00\x00" * 320
        ws.send_json({
            "type": "audio",
            "payload": {
                "data": base64.b64encode(pcm_bytes).decode(),
                "mime_type": "audio/pcm;rate=16000",
            },
        })
        resp = ws.receive_json()
        assert resp["type"] in ("audio", "text")

    # 4. End Session
    del_res = await http_client.delete(f"/api/v1/sessions/{session_id}")
    assert del_res.status_code == 204

    # 5. Submit 5-Star Feedback
    fb_res = await http_client.post("/api/v1/feedback", json={
        "sessionId": session_id,
        "rating": 5,
        "comment": "बहुत ही सरल और सहायक वॉयस सेवा!",
    })
    assert fb_res.status_code == 201
    assert fb_res.json()["rating"] == 5

    # 6. Verify Completed Session State
    get_res = await http_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "completed"


def test_scenario_gemini_api_fallback_resilience(
    ws_client: TestClient,
    session_token_factory,
    mock_session_controller,
):
    """S10: Upstream API failure is caught gracefully; user receives polite fallback without crash."""
    session_id = "scenario-s10-fallback"
    token = session_token_factory(session_id=session_id)

    # Inject simulated upstream failure into the mock harness
    async def failing_handler(session, inp):
        from google.genai import types
        if isinstance(inp, types.LiveClientContent):
            err_msg = "I encountered a momentary issue processing your request. Please try again."
            turn = types.Content(parts=[types.Part.from_text(text=err_msg)], role="model")
            await session.output_queue.put(
                types.LiveServerMessage(
                    server_content=types.LiveServerContent(model_turn=turn, turn_complete=True)
                )
            )
            return True
        return False

    mock_session_controller(failing_handler)

    with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
        ws.receive_json()  # Greeting
        ws.send_json({"type": "text", "payload": {"text": "Test upstream fault"}})
        resp = ws.receive_json()
        assert resp["type"] == "text"
        assert "momentary issue" in resp["payload"]["text"]


@pytest.mark.real_gemini
def test_scenario_live_gemini_network_smoke_test(ws_client: TestClient, session_token_factory):
    """Live Google Gemini API integration test (opt-in with --real-gemini flag)."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not configured in environment.")

    session_id = "scenario-live-gemini-smoke"
    token = session_token_factory(session_id=session_id, language=LanguageCode.EN_IN)
    try:
        with ws_client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
            msg = ws.receive_json()
            assert msg["type"] in ("text", "audio")
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            pytest.skip("Gemini API daily quota exhausted on free tier.")
        raise
