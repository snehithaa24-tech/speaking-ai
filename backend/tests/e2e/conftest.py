"""E2E Test Configuration and High-Fidelity Gemini Live Mock Harness.

Provides:
- In-memory SQLite async database isolation using StaticPool.
- Pre-seeded knowledge base with authentic government schemes, agriculture, hospitals.
- Async HTTP client (httpx.AsyncClient with ASGITransport).
- In-process WebSocket client (starlette.testclient.TestClient).
- Deterministic, high-fidelity Mock Gemini Live harness supporting audio streaming,
  text transcripts, turn completions, barge-in interruptions, and knowledge tool calls.
- Opt-in `real_gemini` marker for live Google Gemini API network verification.
"""

import os
import sys
import json
import base64
import secrets
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import pytest
import pytest_asyncio
import httpx
from starlette.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt
from google.genai import types

# Ensure backend directory is in python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.database.session import Base, get_db
from app.core.config import settings
from app.services.gemini_live import gemini_live_service
from app.services.knowledge import KnowledgeService
from app.services.auth import AuthService
from app.schemas.schemas import VoiceSessionConfig, LanguageCode, KnowledgeCategory

# In-memory SQLite database URL with StaticPool
E2E_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

e2e_engine = create_async_engine(
    E2E_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

E2ESessionLocal = async_sessionmaker(
    e2e_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def pytest_addoption(parser):
    """Add CLI option for opt-in live Google Gemini API network tests."""
    parser.addoption(
        "--real-gemini",
        action="store_true",
        default=False,
        help="Execute live Google Gemini API network tests (requires active quota).",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "real_gemini: mark test to run against live Google Gemini API network endpoint.",
    )


def pytest_collection_modifyitems(config, items):
    """Skip real_gemini marked tests unless --real-gemini flag or -m real_gemini is specified."""
    run_real = config.getoption("--real-gemini")
    mark_expr = config.getoption("-m") or ""
    if not run_real and "real_gemini" not in mark_expr:
        skip_real = pytest.mark.skip(
            reason="Pass --real-gemini or -m real_gemini to run live Google Gemini network tests."
        )
        for item in items:
            if "real_gemini" in item.keywords:
                item.add_marker(skip_real)


# ---------------------------------------------------------------------------
# Rate Limiter Reset Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset sliding window rate limiter before each test to prevent 429 flakes across bulk runs."""
    try:
        from app.core.rate_limit import rate_limiter
        rate_limiter.reset()
    except (ImportError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# Database & Seed Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def e2e_db():
    """Provides isolated database lifecycle with pre-seeded knowledge documents."""
    async with e2e_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Pre-seed domain knowledge
    async with E2ESessionLocal() as session:
        knowledge_service = KnowledgeService(session)
        await knowledge_service.seed_initial_data()

    async with E2ESessionLocal() as session:
        yield session

    async with e2e_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def http_client(e2e_db: AsyncSession):
    """Asynchronous HTTP test client with database dependency overrides."""
    async def override_get_db():
        yield e2e_db

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
def ws_client(e2e_db: AsyncSession):
    """Synchronous WebSocket test client with database dependency overrides."""
    async def override_get_db():
        yield e2e_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Auth and Session Token Factories
# ---------------------------------------------------------------------------

@pytest.fixture
def session_token_factory():
    """Generates valid, expired, tampered, and custom voice session tokens."""
    def _create_token(
        session_id: str,
        language: LanguageCode = LanguageCode.EN_IN,
        voice_name: str = "Kore",
        expired: bool = False,
        tampered: bool = False,
        malformed: bool = False,
        wrong_session: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        system_instruction: str = "You are Sahayak AI.",
    ) -> str:
        if malformed:
            return "not-a-valid-jwt-token-string"

        target_session = wrong_session if wrong_session else session_id
        config = VoiceSessionConfig(
            language=language,
            voice_name=voice_name,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        if expired:
            now = datetime.now(timezone.utc)
            expire = now - timedelta(hours=2)
            payload = {
                "sub": target_session,
                "session_id": target_session,
                "config": config.model_dump(),
                "exp": int(expire.timestamp()),
                "iat": int((now - timedelta(hours=3)).timestamp()),
            }
            return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        if tampered:
            now = datetime.now(timezone.utc)
            expire = now + timedelta(hours=1)
            payload = {
                "sub": target_session,
                "session_id": target_session,
                "config": config.model_dump(),
                "exp": int(expire.timestamp()),
                "iat": int(now.timestamp()),
            }
            return jwt.encode(payload, "tampered_unauthorized_key", algorithm=settings.JWT_ALGORITHM)

        return gemini_live_service.create_session_token(target_session, config)

    return _create_token


@pytest.fixture
def auth_token_factory():
    """Generates valid or expired user JWT tokens for testing authentication."""
    def _create_jwt(
        user_id: str,
        email: str = "testuser@sahayak.ai",
        expired: bool = False,
    ) -> str:
        now = datetime.now(timezone.utc)
        exp_delta = timedelta(minutes=-30) if expired else timedelta(minutes=60)
        payload = {
            "sub": user_id,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int((now + exp_delta).timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return _create_jwt


# ---------------------------------------------------------------------------
# High-Fidelity Deterministic Mock Gemini Live Harness
# ---------------------------------------------------------------------------

class MockGeminiLiveSession:
    """High-fidelity in-memory Gemini Live bidirectional streaming harness.

    Emulates:
    - Instant localized greetings in English and Hindi.
    - Bidirectional audio streaming (16kHz PCM chunks -> 24kHz PCM responses).
    - Natural turn completion flags and speaker attribution.
    - Citizen domain responses (PM-KISAN, Ayushman Bharat, 108 Emergency, Crop Advisory, Bus Transit).
    - Barge-in interruptions via client interrupt signal or audio streaming.
    - Tool call execution loops (search_knowledge, get_scheme_details, find_nearby_hospital).
    - Clean teardown without hanging async tasks.
    """

    def __init__(self, config: VoiceSessionConfig, custom_handler=None):
        self.config = config
        self.output_queue: asyncio.Queue[Optional[types.LiveServerMessage]] = asyncio.Queue()
        self._closed = False
        self.history: List[types.Content] = []
        self.custom_handler = custom_handler
        self.last_spoken_text = ""

        # Initial localized greeting
        greetings = {
            LanguageCode.EN_IN: "Namaste! I am Sahayak AI. How may I assist you today?",
            LanguageCode.HI_IN: "नमस्ते! मैं सहायक AI हूँ। मैं आज आपकी क्या सहायता कर सकता हूँ?",
        }
        if hasattr(LanguageCode, "TE_IN"):
            greetings[LanguageCode.TE_IN] = "నమస్తే! నేను సహాయక్ AI. ఈరోజు నేను మీకు ఎలా సహాయపడగలను?"

        greeting_text = greetings.get(config.language, greetings[LanguageCode.EN_IN])
        self.last_spoken_text = greeting_text
        welcome_turn = types.Content(
            parts=[types.Part.from_text(text=greeting_text)],
            role="model",
        )
        self.history.append(welcome_turn)
        self.output_queue.put_nowait(
            types.LiveServerMessage(
                server_content=types.LiveServerContent(
                    model_turn=welcome_turn,
                    turn_complete=True,
                )
            )
        )

    async def receive(self):
        """Asynchronously yield server messages from output queue."""
        while not self._closed:
            try:
                msg = await self.output_queue.get()
                if msg is None:
                    break
                yield msg
            except asyncio.CancelledError:
                break

    async def send(self, input: Any = None, *args, **kwargs):
        """Handle client messages and enqueue appropriate mock server messages."""
        if self._closed:
            return

        inp = input if input is not None else kwargs.get("input")
        if inp is None and args:
            inp = args[0]

        # Allow test-specific custom handler hook
        if self.custom_handler:
            handled = await self.custom_handler(self, inp)
            if handled:
                return

        # 1. Text input
        if isinstance(inp, types.LiveClientContent):
            text_parts = []
            for turn in inp.turns or []:
                for p in turn.parts or []:
                    if p.text:
                        text_parts.append(p.text)
            query = " ".join(text_parts).strip()
            if not query:
                # Interruption or empty control signal - do not emit model turn
                return
            query_lower = query.lower()

            # Tool triggers
            if "tool_search:" in query_lower:
                term = query.split("tool_search:", 1)[1].strip()
                fc = types.FunctionCall(
                    id=f"call_{secrets.token_hex(3)}",
                    name="search_knowledge",
                    args={"query": term},
                )
                await self.output_queue.put(
                    types.LiveServerMessage(
                        tool_call=types.LiveServerToolCall(function_calls=[fc])
                    )
                )
                return

            if "tool_hospital:" in query_lower:
                fc = types.FunctionCall(
                    id=f"call_{secrets.token_hex(3)}",
                    name="find_nearby_hospital",
                    args={"location": "District Hospital"},
                )
                await self.output_queue.put(
                    types.LiveServerMessage(
                        tool_call=types.LiveServerToolCall(function_calls=[fc])
                    )
                )
                return

            if "tool_scheme:" in query_lower:
                scheme_id = query.split("tool_scheme:", 1)[1].strip() or "pm-kisan"
                fc = types.FunctionCall(
                    id=f"call_{secrets.token_hex(3)}",
                    name="get_scheme_details",
                    args={"schemeId": scheme_id},
                )
                await self.output_queue.put(
                    types.LiveServerMessage(
                        tool_call=types.LiveServerToolCall(function_calls=[fc])
                    )
                )
                return

            if "tool_repeat:" in query_lower:
                fc = types.FunctionCall(
                    id=f"call_{secrets.token_hex(3)}",
                    name="repeat_last_answer",
                    args={},
                )
                await self.output_queue.put(
                    types.LiveServerMessage(
                        tool_call=types.LiveServerToolCall(function_calls=[fc])
                    )
                )
                return

            # Citizen domain knowledge matching
            if "kisan" in query_lower or "किसान" in query_lower:
                reply = (
                    "पीएम-किसान योजना के तहत पात्र किसान परिवारों को प्रति वर्ष ₹6,000 की वित्तीय सहायता "
                    "₹2,000 की तीन समान किस्तों में प्रत्यक्ष बैंक अंतरण (DBT) के माध्यम से प्रदान की जाती है।"
                    if self.config.language == LanguageCode.HI_IN
                    else "PM-KISAN provides income support of ₹6,000 per year to eligible farmer families in three installments of ₹2,000."
                )
            elif "ayushman" in query_lower or "pmjay" in query_lower or "hospital" in query_lower:
                reply = (
                    "Ayushman Bharat PMJAY provides health insurance coverage of up to ₹5 lakh per family per year "
                    "at empaneled hospitals. In case of immediate medical emergency, please dial 108."
                )
            elif "108" in query_lower or "emergency" in query_lower or "chest pain" in query_lower or "आपात" in query_lower:
                reply = (
                    "For medical emergencies, please dial 108 immediately for free 24/7 ambulance dispatch. "
                    "Keep the patient calm and seated while the emergency medical response team arrives."
                )
            elif "yellow leaf" in query_lower or "paddy" in query_lower or "पीले" in query_lower or "धान" in query_lower:
                reply = (
                    "धान के पत्तों का पीला पड़ना जिंक की कमी या जीवाणु झुलसा का संकेत हो सकता है। "
                    "आईसीएआर सलाह अनुसार 0.5% जिंक सल्फेट घोल का छिड़काव करें और खेत में पानी का स्तर संतुलित रखें।"
                    if self.config.language == LanguageCode.HI_IN
                    else "Yellowing leaves in paddy often indicate zinc deficiency or bacterial leaf blight. Spray 0.5% zinc sulfate solution as per ICAR guidelines."
                )
            elif "bus" in query_lower or "transport" in query_lower or "timing" in query_lower or "schedule" in query_lower:
                reply = (
                    "State transport buses operate every 30 minutes from the rural junction to the district bus terminus "
                    "between 06:00 and 21:30 daily."
                )
            elif "repeat" in query_lower or "दोहरा" in query_lower:
                reply = f"Repeating previous answer: {self.last_spoken_text}"
            else:
                reply = f"Thank you for your inquiry about '{query}'. Sahayak AI is ready to assist you further."

            self.last_spoken_text = reply
            model_turn = types.Content(
                parts=[
                    # 24kHz PCM audio chunk simulation (960 bytes = 20ms of audio)
                    types.Part(
                        inline_data=types.Blob(
                            data=b"\x00" * 960,
                            mime_type="audio/pcm;rate=24000",
                        )
                    ),
                    types.Part.from_text(text=reply),
                ],
                role="model",
            )
            self.history.append(model_turn)
            await self.output_queue.put(
                types.LiveServerMessage(
                    server_content=types.LiveServerContent(
                        model_turn=model_turn,
                        turn_complete=True,
                    )
                )
            )

        # 2. Real-time audio or interrupt
        elif isinstance(inp, types.LiveClientRealtimeInput):
            if not inp.media_chunks:
                # Interruption signal received
                await self.output_queue.put(
                    types.LiveServerMessage(
                        server_content=types.LiveServerContent(interrupted=True)
                    )
                )
            else:
                # User audio chunk received
                audio_reply = "I received your voice audio input clearly. How can I assist you with this matter?"
                self.last_spoken_text = audio_reply
                model_turn = types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                data=b"\x00" * 960,
                                mime_type="audio/pcm;rate=24000",
                            )
                        ),
                        types.Part.from_text(text=audio_reply),
                    ],
                    role="model",
                )
                await self.output_queue.put(
                    types.LiveServerMessage(
                        server_content=types.LiveServerContent(
                            model_turn=model_turn,
                            turn_complete=True,
                        )
                    )
                )

        # 3. Tool response
        elif isinstance(inp, types.LiveClientToolResponse):
            for fr in inp.function_responses or []:
                result_str = json.dumps(fr.response or {})
                final_answer = f"Based on verified data from {fr.name}: {result_str}"
                self.last_spoken_text = final_answer
                model_turn = types.Content(
                    parts=[types.Part.from_text(text=final_answer)],
                    role="model",
                )
                await self.output_queue.put(
                    types.LiveServerMessage(
                        server_content=types.LiveServerContent(
                            model_turn=model_turn,
                            turn_complete=True,
                        )
                    )
                )

    async def close(self):
        """Cleanly mark session closed and terminate receive stream."""
        self._closed = True
        await self.output_queue.put(None)


@pytest.fixture(autouse=True)
def mock_gemini_harness(monkeypatch, request):
    """Autouse fixture that provides the in-memory mock harness unless real_gemini marker is active."""
    if "real_gemini" in request.keywords:
        yield None
        return

    current_session = {"instance": None, "custom_handler": None}

    async def _mock_create_session(config: VoiceSessionConfig):
        sess = MockGeminiLiveSession(config, custom_handler=current_session["custom_handler"])
        current_session["instance"] = sess
        return sess

    monkeypatch.setattr(gemini_live_service, "create_session", _mock_create_session)
    monkeypatch.setattr(gemini_live_service, "create_live_session", _mock_create_session)

    yield current_session


@pytest.fixture
def mock_session_controller(mock_gemini_harness):
    """Allows individual tests to inject custom handlers or simulate errors."""
    def _set_handler(handler_fn):
        if mock_gemini_harness:
            mock_gemini_harness["custom_handler"] = handler_fn

    return _set_handler
