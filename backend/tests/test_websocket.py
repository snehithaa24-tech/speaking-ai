import pytest
from google.genai import types
from app.services.gemini_live import gemini_live_service, GeminiLiveSessionWrapper
from app.schemas.schemas import VoiceSessionConfig, LanguageCode


def test_token_creation_and_verification():
    config = VoiceSessionConfig(
        language=LanguageCode.EN_IN,
        voice_name="Kore",
        system_instruction="Test system instruction",
        temperature=0.7,
        max_output_tokens=2048,
    )
    session_id = "test-session-12345"
    token = gemini_live_service.create_session_token(session_id, config)

    assert isinstance(token, str)
    assert len(token) > 0

    # Verify valid token
    token_data = gemini_live_service.verify_session_token(token)
    assert token_data is not None
    assert token_data["session_id"] == session_id
    assert token_data["config"]["language"] == "en-IN"


def test_invalid_token_verification():
    invalid_token = "invalid_base64_string_xyz"
    assert gemini_live_service.verify_session_token(invalid_token) is None


def test_live_tools_declarations():
    tools = gemini_live_service.get_live_tools()
    assert len(tools) > 0
    declarations = tools[0].function_declarations
    names = [d.name for d in declarations]
    assert "search_knowledge" in names
    assert "get_scheme_details" in names
    assert "find_nearby_hospital" in names
    assert "get_transport_information" in names
    assert "repeat_last_answer" in names

    # Ensure search_knowledge language enum only contains en-IN and hi-IN
    search_decl = next(d for d in declarations if d.name == "search_knowledge")
    lang_prop = search_decl.parameters.properties["language"]
    assert "te-IN" not in lang_prop.enum
    assert set(lang_prop.enum) == {"en-IN", "hi-IN"}


def test_multilingual_system_instructions():
    en_inst = gemini_live_service.get_system_instruction(LanguageCode.EN_IN)
    hi_inst = gemini_live_service.get_system_instruction(LanguageCode.HI_IN)

    assert "Sahayak AI" in en_inst
    assert "सहायक AI" in hi_inst
    assert "सुगम्यता" in hi_inst or "सहायक" in hi_inst


@pytest.mark.asyncio
async def test_live_session_wrapper_unit():
    class MockAsyncSession:
        def __init__(self):
            self.closed = False
            self.sent = []

        async def send(self, *args, **kwargs):
            self.sent.append((args, kwargs))

        async def receive(self):
            yield types.LiveServerMessage(
                server_content=types.LiveServerContent(
                    model_turn=types.Content(parts=[types.Part(text="Hello")]),
                    turn_complete=True,
                )
            )

        async def close(self):
            self.closed = True

    class MockContextManager:
        def __init__(self, session):
            self.session = session
            self.entered = False
            self.exited = False

        async def __aenter__(self):
            self.entered = True
            return self.session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.exited = True

    mock_sess = MockAsyncSession()
    mock_cm = MockContextManager(mock_sess)
    wrapper = GeminiLiveSessionWrapper(mock_cm, mock_sess)

    # Test send
    await wrapper.send(input="test")
    assert len(mock_sess.sent) == 1

    # Test receive single turn
    msgs = []
    async for m in wrapper.receive():
        msgs.append(m)
        break
    assert len(msgs) == 1

    # Test close cleans up session and exits context manager
    await wrapper.close()
    assert wrapper._closed is True
    assert mock_sess.closed is True
    assert mock_cm.exited is True


@pytest.mark.asyncio
async def test_create_session_no_fake_fallback(monkeypatch):
    config = VoiceSessionConfig(
        language=LanguageCode.EN_IN,
        voice_name="Kore",
        system_instruction="You are Sahayak AI.",
        temperature=0.7,
        max_output_tokens=100,
    )

    async def _failing_create_live(cfg):
        raise ConnectionError("Upstream Gemini Live unavailable")

    monkeypatch.setattr(gemini_live_service, "create_live_session", _failing_create_live)

    # Must raise RuntimeError and NOT return a fake conversational session
    with pytest.raises(RuntimeError) as exc_info:
        await gemini_live_service.create_session(config)

    assert "Gemini Live bidirectional session initialization failed" in str(exc_info.value)
