import json
import base64
import logging
import asyncio
from typing import Optional, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from google.genai import types
from websockets.exceptions import ConnectionClosed

from app.services.gemini_live import gemini_live_service
from app.schemas.schemas import VoiceSessionConfig

router = APIRouter()
logger = logging.getLogger(__name__)


class LiveSessionManager:
    def __init__(self):
        self.gemini_sessions: Dict[str, Any] = {}
        self.session_configs: Dict[str, VoiceSessionConfig] = {}

    async def create_gemini_session(self, session_id: str, config: VoiceSessionConfig) -> Any:
        session = await gemini_live_service.create_session(config)
        self.gemini_sessions[session_id] = session
        self.session_configs[session_id] = config
        return session

    def get_gemini_session(self, session_id: str) -> Optional[Any]:
        return self.gemini_sessions.get(session_id)

    def remove_session(self, session_id: str):
        self.gemini_sessions.pop(session_id, None)
        self.session_configs.pop(session_id, None)


live_session_manager = LiveSessionManager()


@router.websocket("/ws/live/{session_id}")
async def websocket_live_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
):
    await websocket.accept()
    logger.info(f"WebSocket connection attempt for session: {session_id}")

    token_data = gemini_live_service.verify_session_token(token)
    if not token_data:
        logger.warning(f"Invalid or expired token for session: {session_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    if token_data.get("session_id") != session_id:
        logger.warning(f"Token session ID mismatch: {token_data.get('session_id')} != {session_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token session ID mismatch")
        return

    config_data = token_data.get("config", {})
    try:
        config = VoiceSessionConfig(**config_data)
    except Exception as e:
        logger.error(f"Invalid config in token: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid session configuration")
        return

    gemini_session: Optional[Any] = None
    receive_task: Optional[asyncio.Task] = None
    send_task: Optional[asyncio.Task] = None

    try:
        gemini_session = await live_session_manager.create_gemini_session(session_id, config)
        logger.info(f"Voice session initialized for: {session_id}")

        async def receive_from_client():
            try:
                while True:
                    message = await websocket.receive_text()
                    await handle_client_message(message, gemini_session, session_id, websocket)
            except WebSocketDisconnect:
                logger.info(f"Client disconnected from session: {session_id}")
            except asyncio.CancelledError:
                logger.debug(f"receive_from_client task cancelled for session: {session_id}")
                raise
            except Exception as e:
                logger.error(f"Error receiving from client in session {session_id}: {e}", exc_info=True)

        async def send_to_client():
            try:
                # Outer loop keeps generator alive across multi-turn exchanges
                while not getattr(gemini_session, "_closed", False):
                    turn_received = False
                    async for response in gemini_session.receive():
                        turn_received = True
                        await handle_gemini_response(response, websocket, session_id)
                        if getattr(gemini_session, "_closed", False):
                            break

                    if not turn_received:
                        if getattr(gemini_session, "_closed", False):
                            break
                        await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                logger.debug(f"send_to_client task cancelled for session: {session_id}")
                raise
            except WebSocketDisconnect:
                logger.info(f"Client disconnected during send_to_client for session: {session_id}")
            except ConnectionClosed as e:
                logger.info(f"Gemini Live upstream connection closed for session {session_id}: {e}")
            except Exception as e:
                logger.error(f"Error in Gemini response stream for session {session_id}: {e}", exc_info=True)

        receive_task = asyncio.create_task(receive_from_client(), name=f"ws-recv-{session_id}")
        send_task = asyncio.create_task(send_to_client(), name=f"ws-send-{session_id}")

        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, (asyncio.CancelledError, WebSocketDisconnect)):
                logger.error(f"Task {task.get_name()} completed with error: {exc}", exc_info=exc)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            err_msg = str(e)
            if "API_KEY" in err_msg or "403" in err_msg or "api_key" in err_msg:
                err_msg = "Gemini API key is not configured or invalid. Please set a valid GEMINI_API_KEY in backend/.env"
            if websocket.client_state.name != "CONNECTED":
                await websocket.accept()
            await websocket.send_json({
                "type": "error",
                "payload": {
                    "code": "SESSION_ERROR",
                    "message": err_msg,
                },
            })
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=err_msg[:100])
        except Exception:
            pass
    finally:
        # Guarantee task cancellation
        for task in [receive_task, send_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        # Guarantee Gemini session closure and context manager exit
        if gemini_session:
            try:
                if hasattr(gemini_session, "close"):
                    await gemini_session.close()
                elif hasattr(gemini_session, "cm"):
                    await gemini_session.cm.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing Gemini session: {e}")

        live_session_manager.remove_session(session_id)

        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except Exception:
            pass

        logger.info(f"Cleaned up session: {session_id}")


async def handle_client_message(
    message: str,
    gemini_session: Any,
    session_id: str,
    websocket: Optional[WebSocket] = None,
):
    try:
        data = json.loads(message)
        msg_type = data.get("type")
        payload = data.get("payload", {})

        if msg_type == "setup":
            logger.debug(f"Setup message received for session: {session_id}")

        elif msg_type == "audio":
            if not gemini_session or getattr(gemini_session, "_closed", False):
                logger.warning(f"Audio received for inactive session: {session_id}")
                return
            audio_data = payload.get("data")
            mime_type = payload.get("mime_type", "audio/pcm;rate=16000")
            if audio_data:
                try:
                    pcm_bytes = base64.b64decode(audio_data)
                    blob = types.Blob(data=pcm_bytes, mime_type=mime_type)
                    realtime_input = types.LiveClientRealtimeInput(media_chunks=[blob])
                    await gemini_session.send(input=realtime_input)
                except Exception as e:
                    logger.error(f"Error sending audio chunk for session {session_id}: {e}")

        elif msg_type == "text":
            if not gemini_session or getattr(gemini_session, "_closed", False):
                logger.warning(f"Text received for inactive session: {session_id}")
                return
            text = payload.get("text")
            if text:
                content = types.Content(parts=[types.Part.from_text(text=text)], role="user")
                client_content = types.LiveClientContent(turns=[content], turn_complete=True)
                await gemini_session.send(input=client_content)

        elif msg_type == "function_response":
            if not gemini_session or getattr(gemini_session, "_closed", False):
                return
            function_call_id = payload.get("functionCallId")
            result = payload.get("result")
            error = payload.get("error")
            if function_call_id:
                resp = result if isinstance(result, dict) else {"result": result} if result is not None else {"error": error}
                function_response = types.FunctionResponse(
                    id=function_call_id,
                    name=payload.get("name", ""),
                    response=resp,
                )
                tool_response = types.LiveClientToolResponse(function_responses=[function_response])
                await gemini_session.send(input=tool_response)

        elif msg_type == "interrupt":
            logger.info(f"Client interruption requested for session: {session_id}")
            # Notify Gemini Live model to halt active generation using LiveClientContent
            if gemini_session and not getattr(gemini_session, "_closed", False):
                try:
                    client_content = types.LiveClientContent(turns=[], turn_complete=False)
                    await gemini_session.send(input=client_content)
                except Exception as e:
                    logger.debug(f"Interrupt signal to Gemini Live failed (harmless if idle): {e}")
            # Echo interrupt confirmation to client to clear local Web Audio queues
            if websocket:
                try:
                    await websocket.send_json({"type": "interrupt"})
                except Exception:
                    pass

        elif msg_type == "close":
            logger.info(f"Client requested graceful close for session: {session_id}")
            if websocket:
                try:
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Client requested close")
                except Exception:
                    pass
            raise WebSocketDisconnect(code=status.WS_1000_NORMAL_CLOSURE, reason="Client requested close")

        else:
            logger.warning(f"Unknown message type received for session {session_id}: {msg_type}")

    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON received for session {session_id}: {message[:100]}")
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error(f"Error handling client message for session {session_id}: {e}", exc_info=True)


async def handle_gemini_response(response: types.LiveServerMessage, websocket: WebSocket, session_id: str):
    try:
        if response.setup_complete is not None:
            logger.debug(f"Gemini Live setup complete for session: {session_id}")

        if response.server_content is not None:
            server_content = response.server_content

            # PRIORITY 1: Check server-detected interruption FIRST
            if server_content.interrupted:
                logger.info(f"Server-detected interruption (barge-in) for session: {session_id}")
                await websocket.send_json({"type": "interrupt"})
                return

            # PRIORITY 2: Emit audio and transcript parts
            if server_content.model_turn is not None:
                for part in server_content.model_turn.parts or []:
                    if part.inline_data is not None and part.inline_data.data:
                        base64_audio = base64.b64encode(part.inline_data.data).decode()
                        mime_type = part.inline_data.mime_type or "audio/pcm;rate=24000"
                        await websocket.send_json({
                            "type": "audio",
                            "payload": {"data": base64_audio, "mime_type": mime_type},
                        })
                    elif part.text is not None:
                        await websocket.send_json({
                            "type": "text",
                            "payload": {
                                "text": part.text,
                                "is_final": server_content.turn_complete or False,
                                "speaker": "assistant",
                            },
                        })

            if server_content.turn_complete:
                logger.debug(f"Turn complete for session: {session_id}")

        if response.tool_call is not None:
            for function_call in response.tool_call.function_calls or []:
                await websocket.send_json({
                    "type": "function_call",
                    "payload": {
                        "id": function_call.id,
                        "name": function_call.name,
                        "args": function_call.args or {},
                    },
                })

        if response.tool_call_cancellation is not None:
            logger.info(f"Tool call cancelled for session: {session_id}")

    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error(f"Error sending Gemini response to client in session {session_id}: {e}", exc_info=True)
