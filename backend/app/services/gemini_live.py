import logging
import asyncio
from typing import Optional, Dict, Any, AsyncIterator
from datetime import datetime, timedelta, timezone
from google import genai
from google.genai import types
from google.genai.live import AsyncSession
from websockets.exceptions import ConnectionClosed
from jose import jwt, JWTError
from app.core.config import settings
from app.schemas.schemas import VoiceSessionConfig, LanguageCode


logger = logging.getLogger(__name__)


class GeminiLiveSessionWrapper:
    """
    Robust wrapper around AsyncSession from client.aio.live.connect async context manager.
    Supports persistent multi-turn streaming, thread-safe sending, and clean resource teardown.
    """
    def __init__(self, cm: Any, session: AsyncSession):
        self.cm = cm
        self.session = session
        self._closed = False
        self._send_lock = asyncio.Lock()

    async def send(self, *args, **kwargs):
        """Send message (audio chunk, text prompt, tool response, or interrupt) to Gemini Live."""
        if self._closed:
            logger.warning("Attempted to send message to closed GeminiLiveSessionWrapper")
            return
        async with self._send_lock:
            return await self.session.send(*args, **kwargs)

    async def receive(self) -> AsyncIterator[types.LiveServerMessage]:
        """
        Continuous async generator for Gemini Live server responses.
        Loops across turn completions so the WebSocket session remains persistent
        for multi-turn conversations until explicit disconnection or closure.
        """
        while not self._closed:
            try:
                async for msg in self.session.receive():
                    if self._closed:
                        break
                    yield msg
            except ConnectionClosed:
                logger.info("Gemini Live WebSocket connection closed by remote")
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._closed:
                    break
                logger.error(f"Error in Gemini Live receive loop: {e}", exc_info=True)
                raise

    async def close(self):
        """Gracefully close Gemini Live session and exit the underlying async context manager."""
        if self._closed:
            return
        self._closed = True
        try:
            await self.session.close()
        except Exception as e:
            logger.debug(f"Error closing Live session: {e}")
        try:
            await self.cm.__aexit__(None, None, None)
        except Exception as e:
            logger.debug(f"Error exiting context manager: {e}")


class GeminiLiveService:
    # Supported Gemini Live model - configurable via settings
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self):
        self._client: Optional[genai.Client] = None
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    @property
    def client(self) -> genai.Client:
        """Lazy initialization of Gemini client with validation."""
        if self._client is None:
            try:
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                raise RuntimeError(
                    "Failed to initialize Gemini Live API client. "
                    "Please verify your GEMINI_API_KEY is valid and configured in backend/.env"
                ) from e
        return self._client

    def create_session_token(
        self,
        session_id: str,
        config: VoiceSessionConfig,
        user_id: Optional[str] = None,
    ) -> str:
        """Create a cryptographically signed HS256 JWT for voice session WebSocket authorization."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=1)
        payload = {
            "sub": session_id,
            "session_id": session_id,
            "config": config.model_dump(),
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        }
        if user_id:
            payload["user_id"] = user_id
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify the cryptographically signed session token.

        Returns token payload if signature is valid and token is unexpired, otherwise None.
        Rejects raw base64 tokens, forged signatures, expired tokens, or malformed claims.
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if not isinstance(payload, dict):
                return None
            if "session_id" not in payload and "sub" not in payload:
                return None
            return payload
        except (JWTError, Exception) as e:
            logger.warning(f"Voice session token verification failed: {e}")
            return None

    async def create_live_session(self, config: VoiceSessionConfig) -> GeminiLiveSessionWrapper:
        system_instruction = config.system_instruction or self.get_system_instruction(config.language)

        generation_config = types.GenerationConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
        )

        selected_voice = config.voice_name or self.get_voice_for_language(config.language)
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=selected_voice
                )
            )
        )

        system_instruction_content = (
            types.Content(parts=[types.Part.from_text(text=system_instruction)])
            if system_instruction
            else None
        )

        live_config = types.LiveConnectConfig(
            generation_config=generation_config,
            response_modalities=["AUDIO"],
            speech_config=speech_config,
            system_instruction=system_instruction_content,
            tools=self.get_live_tools(),
        )

        model = getattr(settings, "GEMINI_LIVE_MODEL", None) or self.DEFAULT_MODEL

        # In google-genai 0.5.0+, connect() is decorated with @contextlib.asynccontextmanager
        # and returns an _AsyncGeneratorContextManager.
        # Direct 'await connect()' causes TypeError: object _AsyncGeneratorContextManager can't be used in 'await' expression.
        # We enter the context manager via __aenter__() and encapsulate both cm and session in GeminiLiveSessionWrapper.
        cm = self.client.aio.live.connect(
            model=model,
            config=live_config,
        )
        session = await cm.__aenter__()
        return GeminiLiveSessionWrapper(cm, session)

    async def create_session(self, config: VoiceSessionConfig) -> GeminiLiveSessionWrapper:
        """
        Factory for Gemini Live bidirectional session.
        Establishes genuine Live connection. Raises if connection fails (zero fake chatbot fallbacks).
        """
        try:
            session = await self.create_live_session(config)
            logger.info("Successfully established Gemini Live bidirectional session")
            return session
        except Exception as e:
            logger.error(f"Failed to establish Gemini Live bidirectional session: {e}", exc_info=True)
            raise RuntimeError(f"Gemini Live bidirectional session initialization failed: {e}") from e

    def get_voice_for_language(self, language: LanguageCode) -> str:
        voice_map = {
            LanguageCode.EN_IN: "Kore",
            LanguageCode.HI_IN: "Kore",
        }
        return voice_map.get(language, "Kore")

    def get_system_instruction(self, language: LanguageCode) -> str:
        instructions = {
            LanguageCode.EN_IN: (
                "You are Sahayak AI, a helpful voice assistant for accessibility. Respond naturally and clearly in Indian English. "
                "Use simple vocabulary. Speak in short sentences. Be patient and respectful. "
                "When asked about agriculture, government schemes, transport, or hospitals, use your knowledge tools. "
                "If the user asks for something you cannot do, explain what you can help with instead. "
                "Never pretend to have completed an external action."
            ),
            LanguageCode.HI_IN: (
                "आप सहायक AI हैं, एक सहायक और सुगम्यता वॉयस असिस्टेंट। प्राकृतिक और स्पष्ट हिंदी में जवाब दें। "
                "सरल शब्दावली का उपयोग करें। छोटे वाक्यों में बोलें। धैर्यवान और सम्मानजनक रहें। "
                "कृषि, सरकारी योजनाओं, परिवहन या अस्पताल के बारे में पूछे जाने पर अपने नॉलेज टूल्स का उपयोग करें। "
                "यदि उपयोगकर्ता कुछ ऐसा पूछता है जो आप नहीं कर सकते, तो बताएं कि आप किसमें मदद कर सकते हैं। "
                "कभी भी यह दिखावा न करें कि आपने कोई बाहरी कार्रवाई पूरी कर ली है।"
            ),
        }
        return instructions.get(language, instructions[LanguageCode.EN_IN])

    def get_live_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="search_knowledge",
                        description="Search the knowledge base for verified information regarding government schemes, agriculture, transport, and hospitals.",
                        parameters=types.Schema(
                            type="OBJECT",
                            properties={
                                "query": types.Schema(type="STRING", description="Search query in English or Hindi"),
                                "category": types.Schema(
                                    type="STRING",
                                    enum=["agriculture", "government_schemes", "transport", "hospital_assistance", "general"],
                                    description="Category of knowledge to search",
                                ),
                                "language": types.Schema(
                                    type="STRING",
                                    enum=["en-IN", "hi-IN"],
                                    description="Language of the query",
                                ),
                            },
                            required=["query"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_scheme_details",
                        description="Get detailed benefits, eligibility, and application steps for a specific government scheme.",
                        parameters=types.Schema(
                            type="OBJECT",
                            properties={
                                "schemeId": types.Schema(type="STRING", description="Unique ID or slug of the scheme"),
                            },
                            required=["schemeId"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="find_nearby_hospital",
                        description="Find nearby hospital assistance, emergency ambulance (108), or verified health facilities.",
                        parameters=types.Schema(
                            type="OBJECT",
                            properties={
                                "location": types.Schema(type="STRING", description="District, city, or pincode"),
                                "specialty": types.Schema(type="STRING", description="Medical specialty"),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_transport_information",
                        description="Get public transport routes, bus/train schedules, and fare guidelines.",
                        parameters=types.Schema(
                            type="OBJECT",
                            properties={
                                "from": types.Schema(type="STRING", description="Departure location"),
                                "to": types.Schema(type="STRING", description="Destination location"),
                                "mode": types.Schema(type="STRING", enum=["bus", "train", "metro"], description="Transport mode"),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="repeat_last_answer",
                        description="Repeat the last answer spoken by the assistant for clarity and accessibility.",
                        parameters=types.Schema(type="OBJECT", properties={}),
                    ),
                ]
            )
        ]


gemini_live_service = GeminiLiveService()
