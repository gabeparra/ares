"""
AI Orchestrator - Central Coordinator for ARES

This orchestrator sits BETWEEN the frontend and the LLMs, managing:
- Memory (all four layers)
- Prompt assembly (consistent across models)
- Model routing (local vs cloud)
- Tool execution coordination

CRITICAL PRINCIPLE: LLMs are stateless reasoning engines.
- They do NOT own memory, tools, or personality
- All state lives in the orchestrator/backend
- Prompts sent to local and cloud LLMs MUST be IDENTICAL
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import httpx
from django.conf import settings

from ares_mind.memory_store import memory_store
from ares_core.prompt_assembler import prompt_assembler

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResponse:
    """Response from orchestrator."""
    content: str
    provider: str
    model: str
    session_id: Optional[str] = None
    tokens_used: Optional[int] = None


class ModelRouter:
    """
    Determines whether to use local or cloud LLM.
    
    Routing is deterministic and based on:
    - Local machine availability
    - Task requirements (text-only vs multimodal)
    - Latency requirements
    - Reliability requirements
    
    Routing MUST NOT affect memory or prompt structure.
    """
    
    def __init__(self):
        self.local_available = self._check_local_availability()
        self.cloud_available = self._check_cloud_availability()
    
    def _check_local_availability(self) -> bool:
        """Check if local Ollama is available."""
        try:
            ollama_url = getattr(settings, 'OLLAMA_BASE_URL', None)
            if not ollama_url:
                return False
            
            # Quick health check (with short timeout)
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{ollama_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Local LLM not available: {e}")
            return False
    
    def _check_cloud_availability(self) -> bool:
        """Check if cloud LLM (OpenRouter) is configured."""
        try:
            from api.utils import _get_setting
            import os
            
            # Check if OpenRouter is configured
            api_key = os.environ.get("OPENROUTER_API_KEY")
            return bool(api_key)
        except Exception:
            return False
    
    def route(
        self,
        task_context: Dict[str, Any],
        prefer_local: bool = False
    ) -> Tuple[str, Dict]:
        """
        Determine which model to use.
        
        Args:
            task_context: Context about the task (for future routing logic)
            prefer_local: Prefer local model if available
            
        Returns:
            Tuple of (provider, config)
            - provider: "local" or "openrouter"
            - config: Dict with model configuration
        """
        # Get provider preference from settings
        try:
            from api.utils import _get_setting
            import os
            
            provider = _get_setting("llm_provider")
            if not provider:
                provider = os.environ.get("LLM_PROVIDER", "local")
            
            # Normalize provider
            if provider not in ["local", "openrouter"]:
                provider = "local"
        except Exception:
            provider = "local"
        
        # Override with prefer_local if specified
        if prefer_local and self.local_available:
            provider = "local"
        
        # Routing logic
        if provider == "local":
            if self.local_available:
                logger.info("Routing to local LLM")
                return "local", {"model": getattr(settings, 'OLLAMA_MODEL', 'mistral')}
            elif self.cloud_available:
                logger.warning("Local LLM unavailable, falling back to cloud")
                return "openrouter", self._get_cloud_config()
            else:
                logger.error("No LLM provider available")
                raise RuntimeError("No LLM provider available")
        
        elif provider == "openrouter":
            if self.cloud_available:
                logger.info("Routing to cloud LLM (OpenRouter)")
                return "openrouter", self._get_cloud_config()
            elif self.local_available:
                logger.warning("Cloud LLM unavailable, falling back to local")
                return "local", {"model": getattr(settings, 'OLLAMA_MODEL', 'mistral')}
            else:
                logger.error("No LLM provider available")
                raise RuntimeError("No LLM provider available")
        
        # Default fallback
        if self.local_available:
            return "local", {"model": getattr(settings, 'OLLAMA_MODEL', 'mistral')}
        elif self.cloud_available:
            return "openrouter", self._get_cloud_config()
        else:
            raise RuntimeError("No LLM provider available")
    
    def _get_cloud_config(self) -> Dict:
        """Get cloud model configuration."""
        try:
            from api.utils import _get_setting
            import os
            
            model = _get_setting("openrouter_model")
            if not model:
                model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
            
            return {"model": model}
        except Exception:
            return {"model": "deepseek/deepseek-chat"}


class AIOrchestrator:
    """
    Central orchestrator managing all AI interactions.
    
    This sits between the frontend and the LLMs, ensuring:
    1. Consistent memory management
    2. Identical prompts for local and cloud
    3. Proper tool execution
    4. Deterministic routing
    """
    
    def __init__(self):
        self.memory_store = memory_store
        self.prompt_assembler = prompt_assembler
        self.router = ModelRouter()
    
    def process_chat_request(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
        system_prompt_override: Optional[str] = None,
        prefer_local: bool = False,
    ) -> OrchestratorResponse:
        """
        Main entry point for chat requests.
        
        This replaces direct calls to LLMs from views.
        
        Args:
            user_id: User identifier
            message: User message
            session_id: Session identifier (optional)
            system_prompt_override: Override system prompt (for specialized tasks)
            prefer_local: Prefer local model if available
            
        Returns:
            OrchestratorResponse with content and metadata
        """
        logger.info(f"Processing chat request: user_id={user_id}, session_id={session_id}")
        
        # Step 1: Assemble prompt (identical for local and cloud)
        messages = self.prompt_assembler.assemble(
            user_id=user_id,
            current_message=message,
            session_id=session_id,
            system_prompt_override=system_prompt_override,
        )
        
        # Step 2: Route to appropriate model
        provider, config = self.router.route(
            task_context={"message": message},
            prefer_local=prefer_local
        )
        
        # Step 3: Call the LLM
        if provider == "local":
            response = self._call_local_llm(messages, config)
        elif provider == "openrouter":
            response = self._call_cloud_llm(messages, config)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Step 4: Process response (handle tool calls, etc.)
        processed_content = self._process_response(response["content"], user_id)
        
        # Step 5: Update memory if needed (async/background)
        # TODO: Implement delta-based memory extraction trigger
        
        return OrchestratorResponse(
            content=processed_content,
            provider=provider,
            model=response["model"],
            session_id=session_id,
            tokens_used=response.get("tokens_used"),
        )
    
    def _call_local_llm(self, messages: List[Dict], config: Dict) -> Dict:
        """
        Call local Ollama LLM.
        
        Args:
            messages: Messages in OpenAI format
            config: Model configuration
            
        Returns:
            Dict with response data
        """
        try:
            from api.utils import _get_model_config
            
            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/chat"
            model_config = _get_model_config()
            
            payload = {
                'model': config.get('model', 'mistral'),
                'messages': messages,
                'stream': False,
                'options': {
                    'temperature': model_config['temperature'],
                    'top_p': model_config['top_p'],
                    'top_k': model_config.get('top_k', 40),
                    'repeat_penalty': model_config.get('repeat_penalty', 1.1),
                    'num_gpu': int(model_config.get('num_gpu', 40)),
                }
            }
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(ollama_url, json=payload)
                response.raise_for_status()
                result = response.json()
            
            content = result.get('message', {}).get('content', '')
            
            return {
                "content": content,
                "model": config.get('model', 'mistral'),
                "provider": "local",
            }
            
        except Exception as e:
            logger.error(f"Error calling local LLM: {e}")
            raise
    
    def _call_cloud_llm(self, messages: List[Dict], config: Dict) -> Dict:
        """
        Call cloud LLM (OpenRouter).
        
        Args:
            messages: Messages in OpenAI format
            config: Model configuration
            
        Returns:
            Dict with response data
        """
        try:
            import os
            from api.utils import _get_model_config
            
            service_url = os.environ.get("OPENROUTER_SERVICE_URL", "http://localhost:3100")
            internal_api_key = os.environ.get("INTERNAL_API_KEY", "change-me-in-production")
            model_config = _get_model_config()
            
            payload = {
                "model": config.get('model', 'deepseek/deepseek-chat'),
                "messages": messages,
                "temperature": model_config.get('temperature', 0.7),
                "max_tokens": int(os.environ.get("OPENROUTER_MAX_TOKENS", "2048")),
            }
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{service_url}/v1/chat/completions",
                    json=payload,
                    headers={"X-API-KEY": internal_api_key},
                )
                response.raise_for_status()
                result = response.json()
            
            # Extract content
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
            else:
                content = ""
            
            return {
                "content": content,
                "model": config.get('model', 'deepseek/deepseek-chat'),
                "provider": "openrouter",
                "tokens_used": result.get("usage", {}).get("total_tokens"),
            }
            
        except Exception as e:
            logger.error(f"Error calling cloud LLM: {e}")
            raise
    
    def _process_response(self, content: str, user_id: str) -> str:
        """
        Process LLM response (handle Telegram commands, etc.).
        
        Args:
            content: Raw LLM response
            user_id: User identifier
            
        Returns:
            Processed content
        """
        # Process Telegram send commands
        try:
            from api.chat_views import _process_telegram_send_commands
            content = _process_telegram_send_commands(content, user_id=user_id)
        except Exception as e:
            logger.error(f"Error processing Telegram commands: {e}")
        
        return content
    
    def execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """
        Execute tool calls requested by the LLM.
        
        LLMs should NEVER execute tools directly. They request tools
        via structured JSON, and the orchestrator executes them.
        
        Args:
            tool_calls: List of tool call requests
            
        Returns:
            List of tool results
        """
        # TODO: Implement tool execution framework
        # This will be part of Phase 5
        logger.warning("Tool execution not yet implemented")
        return []
    
    def update_working_memory(
        self,
        user_id: str,
        session_id: str,
        tool_results: List[Dict]
    ):
        """
        Update working memory after tool execution.
        
        Tool results should be promoted into working memory
        so they're available in the next LLM call.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            tool_results: Results from tool execution
        """
        # TODO: Implement working memory updates from tool results
        # This will be part of Phase 5
        logger.warning("Working memory updates not yet implemented")


# Singleton instance
orchestrator = AIOrchestrator()

