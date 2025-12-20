"""Local Ollama client via HTTP."""

import httpx

from caption_ai.config import config
from caption_ai.llm.base import LLMClient, LLMReply
from caption_ai.prompts import get_system_prompt, get_chat_system_prompt


class LocalOllamaClient(LLMClient):
    """Local Ollama client implementation."""

    def __init__(self, model: str | None = None) -> None:
        """Initialize Ollama client."""
        self.base_url = config.ollama_base_url
        self.model = model or config.ollama_model
        # Keep the original attribute for backward compatibility (used by summarization prompts elsewhere).
        self.system_prompt = get_system_prompt()
        # Dedicated chat prompt to reduce repetition and filler responses.
        # Start with default, will be loaded from storage on first use if available
        self.chat_system_prompt = get_chat_system_prompt()
        self._prompt_loaded = False
    
    def set_model(self, model: str) -> None:
        """Change the model for this client."""
        self.model = model

    async def _load_prompt_from_storage(self) -> None:
        """Load chat system prompt from storage if available."""
        if self._prompt_loaded:
            return
        
        try:
            from caption_ai.web.state import get_storage
            storage = get_storage()
            if storage:
                stored_prompt = await storage.get_setting("chat_system_prompt")
                if stored_prompt:
                    self.chat_system_prompt = stored_prompt
        except Exception as e:
            # If storage is not available or fails, fall back to default
            print(f"[DEBUG] Could not load prompt from storage: {e}, using default")
        finally:
            self._prompt_loaded = True

    def reload_prompt(self, prompt: str | None = None) -> None:
        """Reload the chat system prompt. If prompt is provided, use it directly. Otherwise reload from storage."""
        if prompt is not None:
            self.chat_system_prompt = prompt
            self._prompt_loaded = True
        else:
            # Reset flag to force reload on next use
            self._prompt_loaded = False

    async def complete(self, prompt: str, conversation_history: list[dict] | None = None) -> LLMReply:
        """Complete prompt using local Ollama API.
        
        Args:
            prompt: The user's message
            conversation_history: Optional list of previous messages in format:
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        """
        # Ensure prompt is not empty
        if not prompt or not str(prompt).strip():
            print("[WARNING] Attempted to send empty prompt to Ollama")
            return LLMReply(content="Error: Empty prompt provided", model=self.model)

        prompt = str(prompt).strip()

        # Load prompt from storage if not already loaded
        await self._load_prompt_from_storage()

        def _build_messages(include_history: bool) -> list[dict]:
            """Build Ollama /api/chat messages with optional history."""
            messages: list[dict] = []
            system_content = (self.chat_system_prompt or "").strip()
            if not system_content:
                system_content = "You are a helpful AI assistant."

            messages.append({"role": "system", "content": system_content})

            if include_history and conversation_history:
                for msg in conversation_history[-10:]:
                    role = (msg.get("role", "user") or "user")
                    role = str(role).strip().lower()
                    if role not in ("user", "assistant"):
                        role = "user"
                    content = (msg.get("content", "") or msg.get("message", "") or "").strip()
                    if content:
                        messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": prompt})
            return messages

        def _build_options(retry_minimal: bool) -> dict:
            """Build Ollama options; use safer defaults on retry."""
            if retry_minimal:
                options: dict[str, object] = {
                    "temperature": 0.2,
                    "top_p": 0.9,
                }
            else:
                model_name = (self.model or "").strip().lower()
                temp = config.ollama_temperature
                top_p = config.ollama_top_p
                if model_name.startswith("gemma"):
                    temp = min(temp, 0.5)
                    top_p = min(top_p, 0.9)
                options = {"temperature": temp, "top_p": top_p}

            if config.ollama_top_k is not None:
                options["top_k"] = config.ollama_top_k
            if config.ollama_min_p is not None:
                options["min_p"] = float(config.ollama_min_p)

            # Anti-repetition knobs (common for GGUF/llama.cpp backends)
            if config.ollama_repeat_last_n is not None:
                options["repeat_last_n"] = int(config.ollama_repeat_last_n)
            if config.ollama_repeat_penalty is not None:
                options["repeat_penalty"] = float(config.ollama_repeat_penalty)
            if config.ollama_num_ctx is not None:
                options["num_ctx"] = int(config.ollama_num_ctx)

            if config.ollama_num_predict is not None:
                # Cap for stability: some models behave badly with very large num_predict in chat mode
                cap = 512 if retry_minimal else 1024
                options["num_predict"] = min(int(config.ollama_num_predict), cap)

            return options

        async def _call_chat(include_history: bool, retry_minimal: bool) -> LLMReply:
            url = f"{self.base_url}/api/chat"
            messages = _build_messages(include_history=include_history)
            options = _build_options(retry_minimal=retry_minimal)

            # Debug: log what we're sending
            print("[DEBUG] Sending to Ollama /api/chat:")
            print(f"[DEBUG] Model: {self.model}")
            print(f"[DEBUG] Messages count: {len(messages)} (include_history={include_history}, retry_minimal={retry_minimal})")
            for i, msg in enumerate(messages[-3:]):  # Show last 3 messages
                print(f"[DEBUG] Message {i}: {msg['role']} - {msg['content'][:50]}...")
            print(f"[DEBUG] Options: {options}")

            payload = {"model": self.model, "messages": messages, "stream": False, "options": options}

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    return await self._complete_with_generate(prompt=prompt, conversation_history=conversation_history)
                response.raise_for_status()
                response_text = response.text

                if not response_text or not response_text.strip():
                    print(f"[WARNING] Ollama returned empty response text for model {self.model}")
                    return LLMReply(content="", model=self.model)

                # Parse as JSON first
                import json
                try:
                    data = json.loads(response_text)
                except (ValueError, json.JSONDecodeError) as e:
                    print(f"[DEBUG] Failed to parse as single JSON: {e}")
                    # Fallback: try streaming JSON lines parsing
                    data = None

                if isinstance(data, dict) and "message" in data:
                    content = data.get("message", {}).get("content", "")
                    eval_count = data.get("eval_count", 0)
                    done_reason = data.get("done_reason", "")

                    if not content or not content.strip():
                        print("[WARNING] Ollama response has empty content.")
                        print(f"[DEBUG] Full response: {response_text[:500]}")
                        print(f"[DEBUG] Eval count: {eval_count}, Done reason: {done_reason}")
                    return LLMReply(content=content, model=self.model)

                # Handle streaming JSON lines (multiple JSON objects, one per line)
                content_parts: list[str] = []
                for line in response_text.strip().split("\n"):
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk:
                            msg_content = chunk["message"].get("content", "")
                            if msg_content:
                                content_parts.append(msg_content)
                        if chunk.get("done", False):
                            break
                    except (ValueError, json.JSONDecodeError):
                        continue

                content = "".join(content_parts).strip()
                if not content:
                    print(f"[WARNING] Ollama returned empty content after parsing. Response text: {response_text[:500]}")
                    print(f"[DEBUG] Content parts: {content_parts}")
                return LLMReply(content=content, model=self.model)

        try:
            # Google’s Gemma + Ollama docs primarily use /api/generate (prompt-based).
            # Prefer /api/generate first for Gemma models to avoid chat-mode edge cases
            # (e.g., empty assistant content with done_reason=stop).
            model_name = (self.model or "").strip().lower()
            prefer_generate = model_name.startswith("gemma")

            if prefer_generate:
                # Attempt 1: /api/generate with history
                reply = await self._complete_with_generate(prompt=prompt, conversation_history=conversation_history)
                if reply and reply.content and reply.content.strip():
                    return reply

                # Attempt 2: /api/generate without history
                reply = await self._complete_with_generate(prompt=prompt, conversation_history=None)
                if reply and reply.content and reply.content.strip():
                    return reply

            # Attempt 3: /api/chat with history
            reply = await _call_chat(include_history=True, retry_minimal=False)
            if reply and reply.content and reply.content.strip():
                return reply

            # Attempt 4: /api/chat without history (common workaround for models that stop early with context)
            if conversation_history:
                reply = await _call_chat(include_history=False, retry_minimal=True)
                if reply and reply.content and reply.content.strip():
                    return reply

            # Final fallback: /api/generate (if we didn’t already try it or it was empty)
            reply = await self._complete_with_generate(prompt=prompt, conversation_history=conversation_history)
            if reply and reply.content and reply.content.strip():
                return reply

            reply = await self._complete_with_generate(prompt=prompt, conversation_history=None)
            return reply
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Fallback to generate endpoint
                return await self._complete_with_generate(prompt=prompt, conversation_history=conversation_history)
            return LLMReply(
                content=f"HTTP error calling Ollama: {e}",
            )
        except httpx.RequestError as e:
            return LLMReply(
                content=f"Error connecting to Ollama: {e}. "
                f"Make sure Ollama is running at {self.base_url}",
            )
        except Exception as e:
            return LLMReply(
                content=f"Error calling Ollama: {e}",
            )
    
    async def _complete_with_generate(self, prompt: str, conversation_history: list[dict] | None = None) -> LLMReply:
        """Fallback to /api/generate endpoint."""
        url = f"{self.base_url}/api/generate"
        
        # Build prompt with system instructions
        system_instructions = (self.chat_system_prompt or "").strip()
        if not system_instructions:
            system_instructions = "You are a helpful AI assistant."
        
        # Include a lightweight history transcript when falling back to /api/generate
        history_text = ""
        if conversation_history:
            lines = []
            for msg in conversation_history[-10:]:
                role = (msg.get("role", "user") or "user")
                role = str(role).strip().lower()
                if role not in ("user", "assistant"):
                    role = "user"
                content = (msg.get("content", "") or msg.get("message", "") or "").strip()
                if not content:
                    continue
                prefix = "User" if role == "user" else "Assistant"
                lines.append(f"{prefix}: {content}")
            if lines:
                history_text = "\n".join(lines).strip() + "\n\n"

        model_name = (self.model or "").strip().lower()

        # Gemma 3 GGUFs are commonly used with the official chat template:
        # <start_of_turn>user\n...\n<end_of_turn>\n<start_of_turn>model\n...
        # (See Unsloth's guide.) We'll format prompts that way for Gemma models.
        if model_name.startswith("gemma"):
            def _turn(role: str, content: str) -> str:
                content = (content or "").strip()
                return f"<start_of_turn>{role}\n{content}<end_of_turn>\n"

            transcript = ""
            if conversation_history:
                for msg in conversation_history[-10:]:
                    role = (msg.get("role", "user") or "user")
                    role = str(role).strip().lower()
                    if role not in ("user", "assistant"):
                        role = "user"
                    content = (msg.get("content", "") or msg.get("message", "") or "").strip()
                    if not content:
                        continue
                    gemma_role = "user" if role == "user" else "model"
                    transcript += _turn(gemma_role, content)

            # Put system instructions at the top of the user turn as plain text.
            user_block = f"{system_instructions}\n\n{prompt}".strip()
            full_prompt = f"{transcript}{_turn('user', user_block)}<start_of_turn>model\n"
        else:
            # Generic prompt-based template
            if history_text and not history_text.endswith("\n\n"):
                history_text = history_text.strip() + "\n\n"
            full_prompt = f"""{system_instructions}

{history_text}User: {prompt}
Assistant:"""
        
        # Gemma tends to behave better with lower temperature for consistency.
        base_temp = config.ollama_temperature
        base_top_p = config.ollama_top_p
        if model_name.startswith("gemma"):
            # Unsloth notes the Gemma team's recommended inference defaults:
            # temperature=1.0, top_k=64, top_p=0.95, min_p=0.00, repeat_penalty=1.0
            # We keep your configured values, but clamp only if they are more extreme.
            base_temp = min(base_temp, 1.0)
            base_top_p = min(base_top_p, 0.95)

        options = {
            "temperature": base_temp,
            "top_p": base_top_p,
        }
        if config.ollama_top_k is not None:
            options["top_k"] = config.ollama_top_k
        if config.ollama_min_p is not None:
            options["min_p"] = float(config.ollama_min_p)
        if config.ollama_repeat_last_n is not None:
            options["repeat_last_n"] = int(config.ollama_repeat_last_n)
        if config.ollama_repeat_penalty is not None:
            options["repeat_penalty"] = float(config.ollama_repeat_penalty)
        if config.ollama_num_ctx is not None:
            options["num_ctx"] = int(config.ollama_num_ctx)
        if config.ollama_num_predict is not None:
            options["num_predict"] = min(int(config.ollama_num_predict), 1024)
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            # Stop if the model starts continuing the transcript.
            "stop": ["<end_of_turn>", "\nUser:", "\nUSER:", "\nuser:"],
            "options": options
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                # Some Ollama-compatible servers expose only /api/chat; if /api/generate is missing,
                # return empty content so the caller can fall back to /api/chat.
                if response.status_code == 404:
                    print(f"[WARNING] Ollama /api/generate returned 404 at {url}. Falling back to /api/chat.")
                    return LLMReply(content="", model=self.model)
                response.raise_for_status()
                
                # Read response text and handle both single JSON and JSON lines
                response_text = response.text
                
                # Try parsing as single JSON first
                try:
                    import json
                    data = json.loads(response_text)
                    content = data.get("response", "")
                    return LLMReply(
                        content=content,
                        model=self.model,
                    )
                except (ValueError, json.JSONDecodeError):
                    pass
                
                # Handle streaming JSON lines
                content_parts = []
                for line in response_text.strip().split('\n'):
                    if not line.strip():
                        continue
                    try:
                        import json
                        chunk = json.loads(line)
                        if "response" in chunk:
                            content_parts.append(chunk["response"])
                        if chunk.get("done", False):
                            break
                    except (ValueError, json.JSONDecodeError):
                        continue
                
                content = "".join(content_parts) if content_parts else response_text
                
                # Debug logging
                if not content or not content.strip():
                    print(f"[WARNING] Ollama generate endpoint returned empty content. Response text: {response_text[:500]}")
                    print(f"[DEBUG] Content parts: {content_parts}")
                
                return LLMReply(
                    content=content,
                    model=self.model,
                )
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                print(f"[WARNING] Ollama /api/generate HTTP 404 at {url}. Falling back to /api/chat.")
                return LLMReply(content="", model=self.model)
            return LLMReply(
                content=f"HTTP error calling Ollama generate endpoint: {e}",
                model=self.model,
            )
        except httpx.RequestError as e:
            return LLMReply(
                content=f"Error connecting to Ollama generate endpoint: {e}. Make sure Ollama is running at {self.base_url}",
                model=self.model,
            )
        except Exception as e:
            return LLMReply(
                content=f"Error calling Ollama generate endpoint: {e}",
                model=self.model,
            )

