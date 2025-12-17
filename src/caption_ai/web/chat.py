"""Chat message handling."""

import re

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from caption_ai.code_reader import code_reader
from caption_ai.config import config
from caption_ai.web.state import get_storage, get_llm_client
from caption_ai.web.state import get_telegram_bot_instance


async def handle_chat_message(
    message: str,
    websocket: WebSocket,
    session_id: str = "default",
    file_content: str | None = None,
    file_name: str | None = None
) -> None:
    """Handle chat message from user and respond with Glup."""
    llm_client = get_llm_client()
    if not llm_client:
        await websocket.send_json({
            "type": "chat_response",
            "response": "Error: LLM client not initialized. Please check configuration.",
        })
        return

    try:
        # Normalize session_id to avoid polluting conversation history with null/blank IDs
        if not isinstance(session_id, str) or not session_id.strip():
            session_id = "default"
        else:
            session_id = session_id.strip()

        storage = get_storage()
        # Ensure session exists
        if storage:
            await storage.ensure_session(session_id)
        
        # Save user message to conversation history
        if storage:
            full_message = message
            if file_content and file_name:
                full_message = f"[File: {file_name}]\n{file_content}\n\n{message}"
            await storage.save_conversation(session_id, "user", full_message)
        
        # Get conversation history for context
        conversation_history = []
        if storage:
            conversation_history = await storage.get_conversation_history(
                session_id, limit=20
            )

        def _parse_telegram_contacts() -> dict[str, int]:
            """Parse TELEGRAM_CONTACTS into {alias: chat_id}."""
            raw = (config.telegram_contacts or "").strip()
            if not raw:
                return {}
            out: dict[str, int] = {}
            for part in raw.split(","):
                part = part.strip()
                if not part or "=" not in part:
                    continue
                alias, chat_id_str = part.split("=", 1)
                alias = alias.strip().lstrip("@").lower()
                chat_id_str = chat_id_str.strip()
                if not alias or not chat_id_str:
                    continue
                try:
                    out[alias] = int(chat_id_str)
                except ValueError:
                    continue
            return out

        # AI-driven mention sending:
        # If the user message contains a mention like "@alice" and alice is in TELEGRAM_CONTACTS,
        # we will ask the LLM to draft the outgoing message and send it via Telegram.
        msg_stripped = (message or "").strip()
        contacts = _parse_telegram_contacts()
        if contacts:
            mentions = re.findall(r"(?<!\\w)@([a-zA-Z0-9_]{2,32})", msg_stripped)
            # Only support one recipient per message to avoid accidental mass sends.
            if len(mentions) == 1:
                alias = mentions[0].lower()
                if alias in contacts:
                    bot = get_telegram_bot_instance()
                    if not bot or not getattr(bot, "enabled", False):
                        await websocket.send_json({"type": "chat_response", "response": "Error: Telegram bot is not enabled."})
                        return

                    chat_id = contacts[alias]

                    # Remove the mention from the text; remaining text is the intent.
                    remaining = re.sub(rf"(?<!\\w)@{re.escape(mentions[0])}(?!\\w)", "", msg_stripped).strip()
                    if not remaining:
                        await websocket.send_json({"type": "chat_response", "response": f"Usage: include text after @{alias}, e.g. '@{alias} tell them I'm late'."})
                        return

                    # Ask LLM to draft a clean Telegram message. If LLM fails/empty, fall back to remaining text.
                    drafted = None
                    try:
                        draft_prompt = (
                            f"Draft a short Telegram message to {alias} based on the user's request below.\n"
                            f"Output ONLY the message text to send (no quotes, no extra commentary).\n\n"
                            f"User request:\n{remaining}\n"
                        )
                        reply = await llm_client.complete(draft_prompt)
                        drafted = (reply.content if reply else "").strip()
                    except Exception:
                        drafted = None

                    outgoing = drafted if drafted else remaining
                    try:
                        await bot.send_text(chat_id=chat_id, text=outgoing)
                        await websocket.send_json({
                            "type": "chat_response",
                            "response": f"Sent to @{alias} (chat_id={chat_id}).",
                        })
                        return
                    except PermissionError as e:
                        await websocket.send_json({"type": "chat_response", "response": f"Error: {str(e)}"})
                        return
                    except Exception as e:
                        await websocket.send_json({"type": "chat_response", "response": f"Error sending Telegram message: {str(e)}"})
                        return

        # Command: /telegram <chat_id> <message>
        # This allows the user (and only the user) to trigger an outbound Telegram send.
        # It does not rely on the LLM deciding to message someone.
        if msg_stripped.startswith("/telegram "):
            parts = msg_stripped.split(" ", 2)
            if len(parts) < 3:
                response = "Usage: /telegram <chat_id> <message>"
            else:
                try:
                    chat_id = int(parts[1])
                    outgoing = parts[2].strip()
                    bot = get_telegram_bot_instance()
                    if not bot or not getattr(bot, "enabled", False):
                        response = "Error: Telegram bot is not enabled."
                    else:
                        await bot.send_text(chat_id=chat_id, text=outgoing)
                        response = f"Sent to Telegram chat_id={chat_id}."
                except ValueError:
                    response = "Error: chat_id must be an integer."
                except PermissionError as e:
                    response = f"Error: {str(e)}"
                except Exception as e:
                    response = f"Error sending Telegram message: {str(e)}"

            # Send immediate response and skip LLM
            await websocket.send_json({"type": "chat_response", "response": response})
            return
        # Check if user wants to read code or analyze code
        message_lower = message.lower()
        code_context = ""
        
        # Detect code-related queries
        code_keywords = ['read code', 'show code', 'analyze code', 'explain code', 
                        'read file', 'show file', 'code in', 'file:', 'function', 
                        'class', 'module', 'import', 'search code', 'find code']
        
        if any(keyword in message_lower for keyword in code_keywords):
            # Try to extract file path or search query
            if 'file:' in message_lower or 'read ' in message_lower:
                # Extract potential file path
                parts = message.split()
                file_path = None
                for i, part in enumerate(parts):
                    if 'file:' in part.lower() or (i > 0 and parts[i-1].lower() in ['read', 'show', 'file']):
                        if 'file:' in part:
                            file_path = part.split(':', 1)[1]
                        else:
                            file_path = part
                        break
                
                if file_path:
                    file_data = code_reader.read_file(file_path)
                    if file_data:
                        code_context = f"\n\nCode file: {file_data['path']}\n```{file_data['extension'][1:] if file_data['extension'] else 'text'}\n{file_data['content']}\n```\n"
                    else:
                        code_context = f"\n\nNote: Could not read file '{file_path}'. Use /list to see available files."
            
            elif 'search' in message_lower or 'find' in message_lower:
                # Extract search query
                search_terms = message
                if 'search' in message_lower:
                    search_terms = message.split('search', 1)[-1].strip()
                elif 'find' in message_lower:
                    search_terms = message.split('find', 1)[-1].strip()
                
                results = code_reader.search_in_files(search_terms, max_results=5)
                if results:
                    code_context = "\n\nSearch results in codebase:\n"
                    for result in results:
                        code_context += f"\nFile: {result['file']} ({result['match_count']} matches)\n"
                        for match in result['matches'][:2]:
                            code_context += f"  Line {match['line']}: {match['content']}\n"
                else:
                    code_context = f"\n\nNo code found matching: {search_terms}"
            
            elif 'list' in message_lower or 'files' in message_lower:
                files = code_reader.list_code_files(max_depth=3)
                if files:
                    code_context = f"\n\nAvailable code files ({len(files)} total):\n"
                    for file_info in files[:20]:  # Limit to first 20
                        code_context += f"  - {file_info['path']}\n"
                    if len(files) > 20:
                        code_context += f"  ... and {len(files) - 20} more files\n"
                else:
                    code_context = "\n\nNo code files found."
        
        # Build conversation history for Ollama (format: [{"role": "user", "content": "..."}, ...])
        formatted_history = []
        if conversation_history and len(conversation_history) > 1:
            # Include last 10 messages for context (excluding current)
            for conv in conversation_history[-10:-1]:
                content = (conv.get("message", "") or "").strip()
                role = (conv.get("role", "user") or "user").strip().lower()
                if role not in ("user", "assistant"):
                    role = "user"
                # Only add non-empty messages
                if content:
                    formatted_history.append({
                        "role": role,
                        "content": content
                    })
        
        # Build chat prompt with code context
        chat_prompt = message
        if code_context:
            chat_prompt = f"""{message}
{code_context}"""
        
        # Pass conversation history to the LLM client
        try:
            print(f"[DEBUG] Sending prompt to LLM (model: {llm_client.model if hasattr(llm_client, 'model') else 'unknown'})")
            print(f"[DEBUG] Prompt: {chat_prompt[:200]}...")
            print(f"[DEBUG] Prompt length: {len(chat_prompt)} chars, History: {len(formatted_history)} messages")
            if formatted_history:
                print(f"[DEBUG] History preview: {formatted_history[-1] if formatted_history else 'None'}")
            reply = await llm_client.complete(chat_prompt, conversation_history=formatted_history)
            response = reply.content if reply else None
            
            print(f"[DEBUG] LLM response received: {len(response) if response else 0} chars")
            if response:
                print(f"[DEBUG] Response preview: {response[:100]}...")
            
            # Ensure response is not empty
            if not response or not response.strip():
                print(f"[WARNING] LLM returned empty response. Reply object: {reply}")
                response = "I received your message but couldn't generate a response. Please try again."
        except Exception as llm_error:
            print(f"[ERROR] LLM client error: {llm_error}")
            import traceback
            traceback.print_exc()
            response = f"Error: Failed to get response from LLM. {str(llm_error)}"
        
        # Validate response before saving and sending
        if not response or not response.strip():
            response = "Error: Empty response from LLM. Please try again."
        
        # Save Glup's response to conversation history
        # Do NOT persist fallback/error strings, otherwise they pollute the next-turn context and quality drops.
        is_fallback_response = (
            response.startswith("Error:")
            or response.startswith("I received your message but couldn't generate a response.")
            or response.startswith("Error processing your message:")
        )

        if storage and response and not is_fallback_response:
            try:
                await storage.save_conversation(session_id, "assistant", response)
            except Exception as save_error:
                print(f"[WARNING] Failed to save conversation: {save_error}")
                # Continue even if save fails
        
        # Send response to client (ensure it's not empty)
        if response and response.strip():
            try:
                await websocket.send_json({
                    "type": "chat_response",
                    "response": response,
                })
            except (WebSocketDisconnect, RuntimeError) as send_error:
                # Connection closed, don't log as error - this is normal
                print(f"[INFO] WebSocket disconnected while sending response")
                # Don't re-raise - connection is already closed
            except Exception as send_error:
                print(f"[ERROR] Failed to send response to client: {send_error}")
                import traceback
                traceback.print_exc()
                # Don't re-raise - let the WebSocket handler continue processing
        else:
            print("[WARNING] Attempted to send empty response, skipping")
    except Exception as e:
        print(f"[ERROR] Error in handle_chat_message: {e}")
        import traceback
        traceback.print_exc()
        # Try to send error response, but don't fail if we can't
        try:
            await websocket.send_json({
                "type": "chat_response",
                "response": f"Error processing your message: {str(e)}",
            })
        except (WebSocketDisconnect, RuntimeError):
            # Connection closed, this is normal
            print("[INFO] WebSocket disconnected while sending error response")
        except Exception as send_error:
            print(f"[ERROR] Failed to send error response: {send_error}")
            # Don't re-raise - just log and let the WebSocket handler continue

