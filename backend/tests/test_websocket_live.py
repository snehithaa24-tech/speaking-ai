"""
Integration test suite for FastAPI WebSocket endpoint (/ws/live/{session_id}).
Verifies authentication, bidirectional audio, text turns, interruption handling,
multi-turn persistence, and graceful cleanup using a high-fidelity mock Gemini Live session.
"""

import asyncio
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, List

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from google.genai import types
from jose import jwt

from app.main import app
from app.core.config import settings
from app.services.gemini_live import gemini_live_service
from app.api.v1.websocket import live_session_manager
from app.schemas.schemas import VoiceSessionConfig, LanguageCode


class MockGeminiLiveSession:
    """
    High-fidelity mock simulating google.genai.live.AsyncSession for ASGI WebSocket tests.
    Supports continuous multi-turn streaming, auto-reply, manual queueing, server barge-in,
    client interruption, and clean teardown.
    """
    def __init__(self, auto_reply: bool = True):
        self.inbound_queue: asyncio.Queue[Optional[types.LiveServerMessage]] = asyncio.Queue()
        self.received_inputs: List[Any] = []
        self.is_closed: bool = False
        self.auto_reply: bool = auto_reply
        self.interrupt_event: asyncio.Event = asyncio.Event()

    async def send(self, *args, **kwargs):
        inp = kwargs.get("input") or (args[0] if args else None)
        self.received_inputs.append(inp)

        # Detect client-initiated interrupt (LiveClientContent with empty turns)
        if isinstance(inp, types.LiveClientContent) and not inp.turns:
            self.interrupt_event.set()
            return

        if self.auto_reply:
            if isinstance(inp, types.LiveClientContent) and inp.turns:
                prompt = inp.turns[0].parts[0].text if inp.turns[0].parts else ""
                await self.inbound_queue.put(
                    types.LiveServerMessage(
                        server_content=types.LiveServerContent(
                            model_turn=types.Content(
                                parts=[types.Part.from_text(text=f"Echo: {prompt}")],
                                role="model",
                            ),
                            turn_complete=True,
                        )
                    )
                )
            elif isinstance(inp, types.LiveClientRealtimeInput) and inp.media_chunks:
                # Respond with 24kHz PCM mono audio chunk (480 bytes = 10ms of 24kHz 16-bit PCM)
                pcm_24k_chunk = b"\x00\x02" * 240
                await self.inbound_queue.put(
                    types.LiveServerMessage(
                        server_content=types.LiveServerContent(
                            model_turn=types.Content(
                                parts=[
                                    types.Part(
                                        inline_data=types.Blob(
                                            data=pcm_24k_chunk,
                                            mime_type="audio/pcm;rate=24000",
                                        )
                                    )
                                ],
                                role="model",
                            ),
                            turn_complete=True,
                        )
                    )
                )

    async def receive(self):
        """Continuous generator yielding messages across turns."""
        while not self.is_closed:
            try:
                msg = await asyncio.wait_for(self.inbound_queue.get(), timeout=0.1)
                if msg is None or self.is_closed:
                    break
                yield msg
            except asyncio.TimeoutError:
                if self.is_closed:
                    break

    async def close(self):
        self.is_closed = True
        await self.inbound_queue.put(None)

    async def inject_server_message(self, message: types.LiveServerMessage):
        await self.inbound_queue.put(message)


@pytest.fixture
def mock_gemini():
    session = MockGeminiLiveSession(auto_reply=True)
    orig_create = gemini_live_service.create_session

    async def _mock_create_session(config: VoiceSessionConfig):
        return session

    gemini_live_service.create_session = _mock_create_session
    yield session
    gemini_live_service.create_session = orig_create


@pytest.fixture
def auth_tokens():
    config = VoiceSessionConfig(
        language=LanguageCode.EN_IN,
        voice_name="Kore",
        system_instruction="You are Sahayak AI.",
        temperature=0.7,
        max_output_tokens=2048,
    )
    session_id = "test-ws-session-001"
    token = gemini_live_service.create_session_token(session_id, config)
    return session_id, token, config


def test_ws_connection_and_auth_success(mock_gemini, auth_tokens):
    session_id, token, _ = auth_tokens
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
            ws.send_json({"type": "text", "payload": {"text": "Hello"}})
            resp = ws.receive_json()
            assert resp["type"] == "text"
            assert live_session_manager.get_gemini_session(session_id) is not None
            ws.send_json({"type": "close"})


def test_ws_missing_token_rejected():
    with TestClient(app) as client:
        with pytest.raises((WebSocketDisconnect, Exception)):
            with client.websocket_connect("/ws/live/sess-no-token"):
                pass


def test_ws_invalid_token_rejected():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/live/sess-123?token=invalid_token") as ws:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_json()
            assert exc_info.value.code == 1008


def test_ws_session_id_mismatch_rejected(auth_tokens):
    _, token, _ = auth_tokens
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/mismatched-session-id?token={token}") as ws:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_json()
            assert exc_info.value.code == 1008


def test_ws_expired_token_rejected():
    config = VoiceSessionConfig(
        language=LanguageCode.EN_IN,
        voice_name="Kore",
        system_instruction="You are Sahayak AI.",
    )
    session_id = "test-expired-sess"
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": session_id,
        "session_id": session_id,
        "config": config.model_dump(),
        "exp": int((now - timedelta(hours=2)).timestamp()),
        "iat": int((now - timedelta(hours=3)).timestamp()),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/{session_id}?token={expired_token}") as ws:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_json()
            assert exc_info.value.code == 1008


def test_ws_audio_streaming_roundtrip(mock_gemini, auth_tokens):
    session_id, token, _ = auth_tokens
    pcm_16k = b"\x00\x01" * 160
    base64_audio = base64.b64encode(pcm_16k).decode()

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
            ws.send_json({
                "type": "audio",
                "payload": {
                    "data": base64_audio,
                    "mime_type": "audio/pcm;rate=16000",
                },
            })
            resp = ws.receive_json()
            assert resp["type"] == "audio"
            assert resp["payload"]["mime_type"] == "audio/pcm;rate=24000"
            raw_pcm_24k = base64.b64decode(resp["payload"]["data"])
            assert len(raw_pcm_24k) == 480
            ws.send_json({"type": "close"})

    assert len(mock_gemini.received_inputs) == 1
    chunk = mock_gemini.received_inputs[0].media_chunks[0]
    assert chunk.data == pcm_16k
    assert chunk.mime_type == "audio/pcm;rate=16000"


def test_ws_text_message_roundtrip(mock_gemini, auth_tokens):
    session_id, token, _ = auth_tokens
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
            ws.send_json({
                "type": "text",
                "payload": {"text": "नमस्ते, आप कौन हैं?"},
            })
            resp = ws.receive_json()
            assert resp["type"] == "text"
            assert resp["payload"]["speaker"] == "assistant"
            assert "नमस्ते" in resp["payload"]["text"]
            assert resp["payload"]["is_final"] is True
            ws.send_json({"type": "close"})

    assert len(mock_gemini.received_inputs) == 1
    assert mock_gemini.received_inputs[0].turns[0].parts[0].text == "नमस्ते, आप कौन हैं?"


def test_ws_server_initiated_interruption(mock_gemini, auth_tokens):
    session_id, token, _ = auth_tokens
    mock_gemini.auto_reply = False

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
            mock_gemini.inbound_queue.put_nowait(
                types.LiveServerMessage(
                    server_content=types.LiveServerContent(interrupted=True)
                )
            )
            resp = ws.receive_json()
            assert resp == {"type": "interrupt"}
            ws.send_json({"type": "close"})


def test_ws_client_initiated_interruption(mock_gemini, auth_tokens):
    session_id, token, _ = auth_tokens
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
            ws.send_json({"type": "interrupt"})
            interrupt_echo = ws.receive_json()
            assert interrupt_echo == {"type": "interrupt"}

            # Pipeline remains functional after interrupt for subsequent query
            ws.send_json({"type": "text", "payload": {"text": "Post-interrupt query"}})
            resp = ws.receive_json()
            assert "Post-interrupt query" in resp["payload"]["text"]
            ws.send_json({"type": "close"})

    # Verify interrupt input sent to Gemini Live was types.LiveClientContent with empty turns (NOT media_chunks=[])
    interrupt_inputs = [
        inp for inp in mock_gemini.received_inputs
        if isinstance(inp, types.LiveClientContent) and len(inp.turns) == 0
    ]
    assert len(interrupt_inputs) >= 1
    # Ensure NO empty media_chunks were sent (which causes IndexError)
    assert not any(
        isinstance(inp, types.LiveClientRealtimeInput) and len(inp.media_chunks) == 0
        for inp in mock_gemini.received_inputs
    )


def test_ws_multi_turn_conversation_persistence(mock_gemini, auth_tokens):
    session_id, token, _ = auth_tokens
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
            # Turn 1
            ws.send_json({"type": "text", "payload": {"text": "First turn query"}})
            r1 = ws.receive_json()
            assert r1["payload"]["text"] == "Echo: First turn query"
            assert live_session_manager.get_gemini_session(session_id) is not None

            # Turn 2 (verifies session did NOT terminate after Turn 1)
            ws.send_json({"type": "text", "payload": {"text": "Second turn query"}})
            r2 = ws.receive_json()
            assert r2["payload"]["text"] == "Echo: Second turn query"
            assert live_session_manager.get_gemini_session(session_id) is not None

            # Turn 3 (Audio chunk)
            pcm_16k = b"\x00\x05" * 160
            ws.send_json({
                "type": "audio",
                "payload": {"data": base64.b64encode(pcm_16k).decode(), "mime_type": "audio/pcm;rate=16000"},
            })
            r3 = ws.receive_json()
            assert r3["type"] == "audio"
            assert live_session_manager.get_gemini_session(session_id) is not None

            # Graceful cleanup
            ws.send_json({"type": "close"})

    assert mock_gemini.is_closed is True
    assert live_session_manager.get_gemini_session(session_id) is None


def test_ws_abrupt_disconnect_cleanup(mock_gemini, auth_tokens):
    session_id, token, _ = auth_tokens
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/live/{session_id}?token={token}") as ws:
            ws.send_json({"type": "text", "payload": {"text": "Hello"}})
            resp = ws.receive_json()
            assert live_session_manager.get_gemini_session(session_id) is not None
            # Abrupt exit without sending {"type": "close"}

    # Cleanup in finally block must run
    assert mock_gemini.is_closed is True
    assert live_session_manager.get_gemini_session(session_id) is None
