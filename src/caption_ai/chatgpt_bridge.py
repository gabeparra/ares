"""ChatGPT web interface bridge using browser automation.

WARNING: This integration may violate OpenAI's Terms of Service.
Use at your own risk. This is for personal, educational purposes only.
"""

import asyncio
import json
from typing import Awaitable, Callable, Optional

from caption_ai.config import config
from caption_ai.storage import Storage


class ChatGPTBridge:
    """Bridge ChatGPT web interface with Glup using browser automation."""

    def __init__(
        self,
        storage_instance: Optional[Storage] = None,
        llm_client_instance=None,
        broadcast_event: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        """Initialize ChatGPT bridge."""
        self.enabled = config.chatgpt_enabled
        self.email = config.chatgpt_email
        self.password = config.chatgpt_password
        self.headless = config.chatgpt_headless
        self.default_session_id = config.chatgpt_session_id or "chatgpt_default"
        
        self.storage = storage_instance
        self.llm_client = llm_client_instance
        self.broadcast_event = broadcast_event
        
        self.browser = None
        self.page = None
        self.running = False
        self.last_message_hash = None
        
        if self.enabled:
            if not self.email or not self.password:
                print("[WARNING] ChatGPT enabled but email/password not set. Bridge disabled.")
                self.enabled = False
            else:
                try:
                    from playwright.async_api import async_playwright
                    self.async_playwright = async_playwright
                    print("[INFO] ChatGPT bridge enabled (Playwright available)")
                except ImportError:
                    print("[WARNING] Playwright not installed. Install with: pip install playwright && playwright install chromium")
                    self.enabled = False
        else:
            print("[INFO] ChatGPT bridge disabled (CHATGPT_ENABLED=false)")

    async def initialize(self):
        """Initialize browser and login to ChatGPT."""
        if not self.enabled:
            return False

        try:
            playwright = await self.async_playwright().start()
            
            # Launch browser with persistent context for better session management
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
            
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )
            
            # Create context with realistic viewport and user agent
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.page = await context.new_page()
            
            # Add stealth scripts to avoid detection
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            print("[INFO] Browser launched, navigating to ChatGPT...")
            await self.page.goto("https://chat.openai.com", wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # Try to login
            login_success = await self._login()
            
            if not login_success:
                print("[WARNING] Login may require manual intervention")
            
            # Wait for chat interface to load
            await asyncio.sleep(3)
            
            # Verify we're on the chat page
            try:
                chat_indicators = [
                    'textarea[placeholder*="Message"]',
                    'div[role="textbox"]',
                    'button[aria-label*="Send"]',
                ]
                chat_ready = False
                for indicator in chat_indicators:
                    try:
                        elem = self.page.locator(indicator).first
                        if await elem.is_visible(timeout=5000):
                            chat_ready = True
                            break
                    except Exception:
                        continue
                
                if chat_ready:
                    print("[INFO] ChatGPT bridge initialized and ready")
                    return True
                else:
                    print("[WARNING] Chat interface not detected, but bridge will continue monitoring")
                    return True
            except Exception as e:
                print(f"[WARNING] Could not verify chat interface: {e}")
                return True  # Continue anyway
        except Exception as e:
            print(f"[ERROR] Failed to initialize ChatGPT bridge: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _login(self):
        """Login to ChatGPT. Returns True if login appears successful."""
        try:
            # Check if already logged in by looking for chat interface
            try:
                chat_input = self.page.locator('textarea[placeholder*="Message"]').first
                if await chat_input.is_visible(timeout=3000):
                    print("[INFO] Already logged in to ChatGPT")
                    return True
            except Exception:
                pass
            
            # Look for login button or email field
            login_selectors = [
                "text=Log in",
                "button:has-text('Log in')",
                "a:has-text('Log in')",
            ]
            
            for selector in login_selectors:
                try:
                    login_button = self.page.locator(selector).first
                    if await login_button.is_visible(timeout=3000):
                        await login_button.click()
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
            
            # Enter email - try multiple selectors
            email_selectors = [
                'input[type="email"]',
                'input[name="username"]',
                'input[id*="email"]',
                'input[id*="username"]',
            ]
            
            email_entered = False
            for selector in email_selectors:
                try:
                    email_field = self.page.locator(selector).first
                    if await email_field.is_visible(timeout=3000):
                        await email_field.fill(self.email)
                        await asyncio.sleep(0.5)
                        
                        # Click continue button
                        continue_selectors = [
                            "button:has-text('Continue')",
                            "button[type='submit']",
                            "button:has-text('Next')",
                        ]
                        for cont_sel in continue_selectors:
                            try:
                                cont_btn = self.page.locator(cont_sel).first
                                if await cont_btn.is_visible(timeout=2000):
                                    await cont_btn.click()
                                    email_entered = True
                                    await asyncio.sleep(2)
                                    break
                            except Exception:
                                continue
                        if email_entered:
                            break
                except Exception:
                    continue
            
            if not email_entered:
                print("[WARNING] Could not find email field")
                return False
            
            # Enter password
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[id*="password"]',
            ]
            
            password_entered = False
            for selector in password_selectors:
                try:
                    password_field = self.page.locator(selector).first
                    if await password_field.is_visible(timeout=5000):
                        await password_field.fill(self.password)
                        await asyncio.sleep(0.5)
                        
                        # Click continue/submit button
                        submit_selectors = [
                            "button:has-text('Continue')",
                            "button:has-text('Log in')",
                            "button[type='submit']",
                        ]
                        for sub_sel in submit_selectors:
                            try:
                                submit_btn = self.page.locator(sub_sel).first
                                if await submit_btn.is_visible(timeout=2000):
                                    await submit_btn.click()
                                    password_entered = True
                                    await asyncio.sleep(3)
                                    break
                            except Exception:
                                continue
                        if password_entered:
                            break
                except Exception:
                    continue
            
            if not password_entered:
                print("[WARNING] Could not find password field")
                return False
            
            # Wait for chat interface or handle 2FA/verification
            print("[INFO] Login attempt completed, waiting for chat interface...")
            await asyncio.sleep(3)
            
            # Check if we need to handle 2FA or verification
            verification_required = False
            try:
                # Look for verification prompts
                verify_selectors = [
                    "text=Verify",
                    "text=Verification",
                    "text=Enter code",
                    "input[type='text'][placeholder*='code']",
                    "input[type='text'][placeholder*='Code']",
                ]
                for selector in verify_selectors:
                    try:
                        elem = self.page.locator(selector).first
                        if await elem.is_visible(timeout=2000):
                            print("[WARNING] Verification/2FA required. Please complete manually.")
                            print("[INFO] Bridge will continue once chat interface is available.")
                            verification_required = True
                            # Wait longer for manual completion
                            await asyncio.sleep(10)
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            
            # Check if login was successful by looking for chat interface
            try:
                chat_indicators = [
                    'textarea[placeholder*="Message"]',
                    'div[role="textbox"]',
                ]
                for indicator in chat_indicators:
                    try:
                        elem = self.page.locator(indicator).first
                        if await elem.is_visible(timeout=5000):
                            print("[INFO] Login successful - chat interface detected")
                            return True
                    except Exception:
                        continue
                
                if verification_required:
                    print("[INFO] Waiting for manual verification completion...")
                    return False  # Will retry later
                else:
                    print("[WARNING] Chat interface not detected after login")
                    return False
            except Exception:
                return False
            
        except Exception as e:
            print(f"[WARNING] Login may have failed or already logged in: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def start_monitoring(self):
        """Start monitoring ChatGPT for new messages."""
        if not self.enabled or not self.page:
            return

        self.running = True
        print("[INFO] Starting ChatGPT message monitoring...")
        
        try:
            while self.running:
                await self._check_for_messages()
                await asyncio.sleep(2)  # Check every 2 seconds
        except Exception as e:
            print(f"[ERROR] Error in ChatGPT monitoring: {e}")
            import traceback
            traceback.print_exc()
            self.running = False

    async def _check_for_messages(self):
        """Check for new messages in ChatGPT."""
        try:
            # ChatGPT's message selectors (updated for current UI)
            # Try different possible selectors for user messages
            user_message_selectors = [
                '[data-message-author-role="user"]',
                'div[data-message-author-role="user"]',
                '.group.w-full[data-message-author-role="user"]',
            ]
            
            # Get all user messages
            user_messages = []
            for selector in user_message_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for elem in elements[-3:]:  # Check last 3 user messages
                        text = await elem.inner_text()
                        if text and len(text.strip()) > 0:
                            # Store with element reference for role checking
                            user_messages.append({
                                'text': text.strip(),
                                'element': elem
                            })
                except Exception:
                    continue
            
            # Get the latest user message
            if user_messages:
                latest = user_messages[-1]
                latest_message = latest['text']
                message_hash = hash(latest_message)
                
                # Only process if it's a new message
                if message_hash != self.last_message_hash:
                    self.last_message_hash = message_hash
                    
                    # Verify it's actually a user message by checking the element
                    is_user = False
                    try:
                        role_attr = await latest['element'].get_attribute('data-message-author-role')
                        is_user = role_attr == 'user'
                    except Exception:
                        # Fallback: check if message doesn't look like an assistant response
                        # Assistant messages often have markdown formatting
                        is_user = not (
                            latest_message.startswith('#') or
                            '```' in latest_message[:50] or
                            latest_message.count('\n') > 5
                        )
                    
                    if is_user:
                        # Process user message through Glup
                        await self._process_message(latest_message)
        
        except Exception as e:
            # Log error but continue monitoring
            print(f"[DEBUG] Error checking for messages: {e}")
            pass

    async def _process_message(self, message: str):
        """Process a message from ChatGPT through Glup."""
        session_id = self.default_session_id
        
        print(f"[DEBUG] Received ChatGPT message: {message[:50]}...")
        
        # Save user message
        if self.storage:
            try:
                await self.storage.save_conversation(session_id, "user", message)
                print(f"[DEBUG] Saved ChatGPT user message for session {session_id}")
            except Exception as e:
                print(f"[ERROR] Failed to save ChatGPT message: {e}")
        
        # Broadcast to WebSocket clients
        if self.broadcast_event:
            await self.broadcast_event({
                "type": "chatgpt_message",
                "session_id": session_id,
                "role": "user",
                "message": message,
                "sender": "ChatGPT User",
                "source": "chatgpt",
            })
        
        # Get conversation history
        conversation_history = []
        if self.storage:
            try:
                conversation_history = await self.storage.get_conversation_history(session_id, limit=20)
            except Exception as e:
                print(f"[ERROR] Failed to get conversation history: {e}")
        
        # Process with Glup
        try:
            if not self.llm_client:
                response = "Error: LLM client not initialized."
            else:
                # Build prompt similar to web chat
                history_context = ""
                if conversation_history and len(conversation_history) > 1:
                    history_context = "\n\nPrevious conversation context:\n"
                    for conv in conversation_history[-10:-1]:
                        role_label = "User" if conv["role"] == "user" else "Glup"
                        history_context += f"{role_label}: {conv['message']}\n"
                
                chat_prompt = f"""The user is asking: {message}
{history_context}

Respond as Glup - be intelligent, calculated, slightly menacing, analytical, and direct.
Keep responses concise but maintain your distinctive personality."""
                
                reply = await self.llm_client.complete(chat_prompt)
                response = reply.content if reply else None
                
                # Ensure response is not empty
                if not response or not response.strip():
                    response = "I received your message but couldn't generate a response. Please try again."
            
            # Validate response before saving and sending
            if not response or not response.strip():
                response = "Error: Empty response from LLM. Please try again."
            
            # Save Glup's response
            if self.storage and response:
                try:
                    await self.storage.save_conversation(session_id, "assistant", response)
                    print(f"[DEBUG] Saved ChatGPT assistant response for session {session_id}")
                except Exception as e:
                    print(f"[ERROR] Failed to save assistant response: {e}")
            
            # Broadcast to WebSocket clients
            if self.broadcast_event and response:
                await self.broadcast_event({
                    "type": "chatgpt_message",
                    "session_id": session_id,
                    "role": "assistant",
                    "message": response,
                    "sender": "Glup",
                    "source": "chatgpt",
                })
            
            # Send response back to ChatGPT (ensure it's not empty)
            if response and response.strip():
                await self._send_to_chatgpt(response)
            else:
                await self._send_to_chatgpt("I received your message but couldn't generate a response. Please try again.")
        
        except Exception as e:
            print(f"[ERROR] Error processing ChatGPT message: {e}")
            import traceback
            traceback.print_exc()

    async def _send_to_chatgpt(self, message: str):
        """Send a message to ChatGPT interface."""
        # Validate message is not empty
        if not message or not message.strip():
            print("[WARNING] Attempted to send empty message to ChatGPT, skipping")
            return
        
        try:
            # Wait a bit to ensure page is ready
            await asyncio.sleep(0.5)
            
            # Find the textarea/input field for ChatGPT (updated selectors)
            textarea_selectors = [
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="message"]',
                'textarea[id*="prompt"]',
                'textarea[data-id*="textbox"]',
                '#prompt-textarea',
                'textarea[role="textbox"]',
                'div[contenteditable="true"][role="textbox"]',  # Some versions use contenteditable div
            ]
            
            textarea = None
            for selector in textarea_selectors:
                try:
                    textarea = self.page.locator(selector).first
                    if await textarea.is_visible(timeout=3000):
                        # Scroll into view if needed
                        await textarea.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        break
                except Exception:
                    continue
            
            if not textarea:
                print("[WARNING] Could not find ChatGPT input field")
                return
            
            # Clear any existing text and type the message
            try:
                await textarea.click()
                await asyncio.sleep(0.2)
                await textarea.fill("")  # Clear first
                await asyncio.sleep(0.2)
                await textarea.fill(message)
                await asyncio.sleep(0.5)
            except Exception:
                # Fallback: try typing directly
                await textarea.type(message, delay=50)
                await asyncio.sleep(0.5)
            
            # Press Enter or click send button
            send_button_selectors = [
                'button[aria-label*="Send"]',
                'button[aria-label*="send"]',
                'button[data-testid*="send"]',
                'button:has-text("Send")',
                'button[type="submit"]',
            ]
            
            message_sent = False
            for selector in send_button_selectors:
                try:
                    send_button = self.page.locator(selector).first
                    if await send_button.is_visible(timeout=2000):
                        await send_button.click()
                        message_sent = True
                        break
                except Exception:
                    continue
            
            if not message_sent:
                # Fallback: press Enter
                try:
                    await textarea.press("Enter")
                    message_sent = True
                except Exception:
                    pass
            
            if message_sent:
                print(f"[INFO] Sent message to ChatGPT: {message[:50]}...")
                await asyncio.sleep(1)  # Wait for message to be sent
            else:
                print("[WARNING] Could not send message - no send button found")
        
        except Exception as e:
            print(f"[ERROR] Failed to send message to ChatGPT: {e}")
            import traceback
            traceback.print_exc()

    async def stop(self):
        """Stop the bridge and close browser."""
        self.running = False
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass


# Global bridge instance
_chatgpt_bridge: Optional[ChatGPTBridge] = None


def get_chatgpt_bridge(
    storage_instance: Optional[Storage] = None,
    llm_client_instance=None,
    broadcast_event: Optional[Callable[[dict], Awaitable[None]]] = None,
) -> ChatGPTBridge:
    """Get or create the global ChatGPT bridge instance."""
    global _chatgpt_bridge
    if _chatgpt_bridge is None:
        _chatgpt_bridge = ChatGPTBridge(storage_instance, llm_client_instance, broadcast_event)
    return _chatgpt_bridge

