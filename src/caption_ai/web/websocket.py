"""WebSocket endpoint for real-time updates."""

import json

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketDisconnect as StarletteWebSocketDisconnect

from caption_ai.config import config
from caption_ai.web.state import (
    get_storage,
    get_llm_client,
    get_websocket_connections,
)
from caption_ai.web.llm_client import set_llm_client
from caption_ai.web.chat import handle_chat_message


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    try:
        await websocket.accept()
    except Exception as e:
        print(f"[ERROR] Failed to accept WebSocket connection: {e}")
        return
    
    websocket_connections = get_websocket_connections()
    websocket_connections.append(websocket)

    try:
        storage = get_storage()
        # Send initial data
        try:
            if storage:
                try:
                    segments = []
                    async for segment in storage.fetch_recent(limit=50):
                        segments.append({
                            "timestamp": segment.timestamp.isoformat(),
                            "text": segment.text,
                            "speaker": segment.speaker,
                        })
                    summary = await storage.get_latest_summary()

                    await websocket.send_json({
                        "type": "init",
                        "segments": list(reversed(segments)),
                        "summary": summary,
                        "current_model": config.ollama_model,
                    })
                except Exception as e:
                    print(f"[WARNING] Failed to send initial data: {e}")
                    # Send empty init message so client knows connection is established
                    try:
                        await websocket.send_json({
                            "type": "init",
                            "segments": [],
                            "summary": None,
                            "current_model": config.ollama_model,
                        })
                    except (WebSocketDisconnect, RuntimeError):
                        # Connection already closed, exit
                        return
            else:
                # Storage not initialized yet, send empty init
                try:
                    await websocket.send_json({
                        "type": "init",
                        "segments": [],
                        "summary": None,
                        "current_model": config.ollama_model,
                    })
                except (WebSocketDisconnect, RuntimeError):
                    # Connection already closed, exit
                    return
        except (WebSocketDisconnect, RuntimeError):
            # Connection closed during initialization, exit
            print("[INFO] WebSocket disconnected during initialization")
            return

        # Initialize LLM client if not already done
        if get_llm_client() is None:
            set_llm_client()

        # Keep connection alive and handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                if message_data.get("type") == "chat":
                    # Handle chat message - wrap in try/except to prevent breaking the loop
                    try:
                        user_message = message_data.get("message", "")
                        session_id = message_data.get("session_id", "default")
                        file_content = message_data.get("file_content")
                        file_name = message_data.get("file_name")
                        await handle_chat_message(
                            user_message,
                            websocket,
                            session_id=session_id,
                            file_content=file_content,
                            file_name=file_name
                        )
                    except Exception as e:
                        print(f"[ERROR] Error handling chat message: {e}")
                        import traceback
                        traceback.print_exc()
                        # Try to send error response to client
                        try:
                            await websocket.send_json({
                                "type": "chat_response",
                                "response": f"Error processing message: {str(e)}",
                            })
                        except (WebSocketDisconnect, StarletteWebSocketDisconnect, RuntimeError):
                            # Connection closed, exit loop
                            print("[INFO] WebSocket disconnected while sending error response")
                            break
                        except Exception as send_error:
                            print(f"[ERROR] Failed to send error response: {send_error}")
                            # Test if connection is still alive before breaking
                            try:
                                await websocket.send_json({"type": "ping"})
                                # Connection is still alive, continue processing
                            except (WebSocketDisconnect, StarletteWebSocketDisconnect, RuntimeError):
                                # Connection is broken, exit loop
                                print("[INFO] WebSocket connection broken, closing")
                                break
                            except Exception:
                                # Other error, continue processing
                                pass
                elif message_data.get("type") == "init":
                    # Client requesting initial data - resend it
                    try:
                        storage = get_storage()
                        if storage:
                            try:
                                segments = []
                                async for segment in storage.fetch_recent(limit=50):
                                    segments.append({
                                        "timestamp": segment.timestamp.isoformat(),
                                        "text": segment.text,
                                        "speaker": segment.speaker,
                                    })
                                summary = await storage.get_latest_summary()
                                await websocket.send_json({
                                    "type": "init",
                                    "segments": list(reversed(segments)),
                                    "summary": summary,
                                    "current_model": config.ollama_model,
                                })
                            except Exception as e:
                                print(f"[WARNING] Failed to resend initial data: {e}")
                    except Exception as e:
                        print(f"[ERROR] Error handling init request: {e}")
            except json.JSONDecodeError as e:
                print(f"[WARNING] Invalid JSON received: {e}")
                # Continue loop - don't break on JSON errors
            except (WebSocketDisconnect, StarletteWebSocketDisconnect):
                print("[INFO] WebSocket disconnected by client")
                break
            except RuntimeError as e:
                # RuntimeError can occur when trying to send after connection closed
                if "close message" in str(e).lower() or "cannot call" in str(e).lower():
                    print("[INFO] WebSocket connection already closed")
                    break
                # Other RuntimeError, log and continue
                print(f"[ERROR] WebSocket RuntimeError: {e}")
                import traceback
                traceback.print_exc()
            except Exception as e:
                print(f"[ERROR] WebSocket message handling error: {e}")
                import traceback
                traceback.print_exc()
                # Continue loop - don't break on unexpected errors unless connection is broken
                try:
                    # Test if connection is still alive
                    await websocket.send_json({"type": "ping"})
                except (WebSocketDisconnect, StarletteWebSocketDisconnect, RuntimeError):
                    # Connection is broken, exit loop
                    print("[INFO] WebSocket connection appears to be broken, closing")
                    break
                except Exception:
                    # Other error, continue processing
                    pass
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

