"""
Prompt Assembler - Single Source of Truth for Prompt Structure

This module ensures that IDENTICAL prompts are sent to both local and cloud LLMs.
Any divergence in behavior must come from routing decisions, not prompt shape.

CRITICAL: This is the ONLY place where prompts should be assembled.
"""

import logging
from typing import Dict, List, Optional
from ares_mind.memory_store import memory_store

logger = logging.getLogger(__name__)


class PromptAssembler:
    """
    Assembles prompts with strict structure for consistency.
    
    Prompt structure (MUST be identical for local and cloud):
    1. SYSTEM: Personality profile (from identity memory)
    2. SYSTEM: Identity memory (preferences, habits, communication style)
    3. SYSTEM: Factual memory (stable facts)
    4. SYSTEM: Working memory (calendar, date, time, active context)
    5. SYSTEM: Episodic memory (recent conversational summary)
    6. USER: Current user input ONLY
    
    NO raw chat history should be included. Only episodic summaries.
    """
    
    def __init__(self):
        """Initialize prompt assembler."""
        self.memory_store = memory_store
    
    def assemble(
        self,
        user_id: str,
        current_message: str,
        session_id: Optional[str] = None,
        system_prompt_override: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Assemble a complete prompt for LLM consumption.
        
        This method MUST return identical structure for both local and cloud models.
        
        Args:
            user_id: User identifier
            current_message: The current user message
            session_id: Session identifier (optional)
            system_prompt_override: Override the default system prompt (for specialized tasks)
            
        Returns:
            List of message dicts in OpenAI format [{"role": "system", "content": "..."}, ...]
        """
        logger.info(f"Assembling prompt for user_id={user_id}, session_id={session_id}")
        
        messages = []
        
        # =====================================================================
        # SYSTEM: Base personality and instructions
        # =====================================================================
        
        if system_prompt_override:
            # For specialized tasks (e.g., transcript analysis), use override
            system_prompt = system_prompt_override
            logger.info("Using system prompt override")
        else:
            # Get base system prompt from settings or default
            system_prompt = self._get_base_system_prompt()
            
            # Inject AI self-knowledge (identity)
            self_memory = self._get_self_memory_context()
            if self_memory:
                system_prompt = system_prompt + "\n\n" + self_memory
            
            # Inject Telegram instructions if applicable
            system_prompt = self._add_telegram_instructions(system_prompt)
            
            # Inject memory layers
            memory_context = self.memory_store.format_for_prompt(user_id, session_id)
            if memory_context:
                system_prompt = system_prompt + "\n\n" + memory_context
            
            # Inject code context (if available)
            code_context = self._get_code_context()
            if code_context:
                system_prompt = system_prompt + "\n\n" + code_context
        
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # =====================================================================
        # USER: Current message ONLY
        # =====================================================================
        
        messages.append({
            "role": "user",
            "content": current_message
        })
        
        # Log prompt stats
        total_chars = sum(len(m["content"]) for m in messages)
        logger.info(f"Assembled prompt: {len(messages)} messages, {total_chars} chars")
        
        return messages
    
    def _get_base_system_prompt(self) -> str:
        """Get the base system prompt from settings or use default."""
        try:
            from api.utils import _get_setting, _get_default_system_prompt
            
            prompt = _get_setting("chat_system_prompt")
            if not prompt:
                prompt = _get_default_system_prompt()
            
            return prompt
        except Exception as e:
            logger.error(f"Error getting base system prompt: {e}")
            return "You are a helpful AI assistant."
    
    def _get_self_memory_context(self) -> Optional[str]:
        """Get AI self-knowledge/identity context."""
        try:
            from api.memory_views import get_self_memory_context
            return get_self_memory_context()
        except Exception as e:
            logger.error(f"Error getting self memory context: {e}")
            return None
    
    def _add_telegram_instructions(self, system_prompt: str) -> str:
        """Add Telegram messaging instructions if not already present."""
        if "[TELEGRAM_SEND:" in system_prompt:
            return system_prompt
        
        telegram_instructions = """

## Telegram Messaging
You can send messages to Telegram users. When the user asks you to send a message to someone via Telegram, use this format in your response:
[TELEGRAM_SEND:identifier:message_text]

Where:
- identifier: The name, username, or nickname of the Telegram user (e.g., "gabu", "gabe", "@username")
- message_text: The actual message content to send

Example: If asked to "send hello to gabu", include in your response:
[TELEGRAM_SEND:gabu:Hello from ARES!]

After sending, the system will replace this marker with a confirmation. Always confirm that you've sent the message in your response.
"""
        return system_prompt + telegram_instructions
    
    def _get_code_context(self) -> Optional[str]:
        """Get code context if available."""
        try:
            from api.code_views import get_code_context_summary
            return get_code_context_summary()
        except Exception as e:
            # Code context is optional, don't fail if not available
            logger.debug(f"Code context not available: {e}")
            return None
    
    def validate_consistency(
        self,
        messages_local: List[Dict],
        messages_cloud: List[Dict]
    ) -> bool:
        """
        Validate that two prompts have identical structure.
        
        This is used in testing to ensure local and cloud prompts match.
        
        Args:
            messages_local: Messages for local model
            messages_cloud: Messages for cloud model
            
        Returns:
            True if identical, False otherwise
        """
        if len(messages_local) != len(messages_cloud):
            logger.error("Prompt length mismatch")
            return False
        
        for i, (local, cloud) in enumerate(zip(messages_local, messages_cloud)):
            if local["role"] != cloud["role"]:
                logger.error(f"Role mismatch at index {i}")
                return False
            if local["content"] != cloud["content"]:
                logger.error(f"Content mismatch at index {i}")
                return False
        
        return True


# Singleton instance
prompt_assembler = PromptAssembler()

