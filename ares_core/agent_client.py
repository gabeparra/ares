"""
ARES Agent Client - Communicates with the agent running on the 4090 rig.

The agent handles:
- Starting/stopping Stable Diffusion with different VRAM modes
- Controlling Ollama (start/stop, adjust parameters)
- Monitoring system resources (GPU, VRAM, CPU)
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class VRAMMode(Enum):
    """VRAM modes for Stable Diffusion startup."""
    LOW = "low"       # --lowvram --no-half-vae (~4GB)
    MEDIUM = "medium" # --medvram (~6-8GB)
    FULL = "full"     # default (~10-12GB+)


class ActionRisk(Enum):
    """Risk levels for agent actions."""
    LOW = "low"       # Auto-execute
    MEDIUM = "medium" # Requires confirmation
    HIGH = "high"     # Requires confirmation + MFA


@dataclass
class AgentAction:
    """Definition of an agent action."""
    id: str
    name: str
    description: str
    risk: ActionRisk
    parameters: Optional[Dict[str, Any]] = None


# Available actions that the agent can perform
AVAILABLE_ACTIONS: List[AgentAction] = [
    AgentAction(
        id="start_sd",
        name="Start Stable Diffusion",
        description="Start Stable Diffusion WebUI with specified VRAM mode",
        risk=ActionRisk.LOW,
        parameters={"vram_mode": ["low", "medium", "full"]},
    ),
    AgentAction(
        id="stop_sd",
        name="Stop Stable Diffusion",
        description="Stop the running Stable Diffusion process",
        risk=ActionRisk.LOW,
    ),
    AgentAction(
        id="start_ollama",
        name="Start Ollama",
        description="Start the Ollama LLM service",
        risk=ActionRisk.LOW,
    ),
    AgentAction(
        id="stop_ollama",
        name="Stop Ollama",
        description="Stop the Ollama LLM service",
        risk=ActionRisk.MEDIUM,
    ),
    AgentAction(
        id="adjust_ollama_params",
        name="Adjust Ollama Parameters",
        description="Adjust Ollama runtime parameters (context length, GPU layers)",
        risk=ActionRisk.LOW,
        parameters={"num_ctx": "int", "num_gpu": "int"},
    ),
    AgentAction(
        id="get_resources",
        name="Get System Resources",
        description="Get current GPU/VRAM/CPU usage",
        risk=ActionRisk.LOW,
    ),
]


class AgentClient:
    """
    Client for communicating with the ARES Agent on the 4090 rig.
    
    Usage:
        client = AgentClient(base_url="http://100.x.x.x:8100", api_key="secret")
        status = client.get_status()
        client.execute_action("start_sd", {"vram_mode": "low"})
    """
    
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        """
        Initialize the agent client.
        
        Args:
            base_url: URL to the agent (e.g., http://100.x.x.x:8100)
            api_key: Shared secret for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self._client = None
    
    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get agent health and system status.
        
        Returns:
            Dict with agent status, resources, and service states
        """
        try:
            client = self._get_client()
            response = client.get(
                f"{self.base_url}/status",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "status": "offline",
                "error": f"Cannot connect to agent at {self.base_url}",
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "error": f"Agent returned {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def get_resources(self) -> Dict[str, Any]:
        """
        Get system resource usage (GPU, VRAM, CPU).
        
        Returns:
            Dict with resource metrics
        """
        try:
            client = self._get_client()
            response = client.get(
                f"{self.base_url}/resources",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting resources: {e}")
            return {"error": str(e)}
    
    def get_logs(self) -> Dict[str, Any]:
        """
        Get agent logs.
        
        Returns:
            Dict with log data
        """
        try:
            client = self._get_client()
            response = client.get(
                f"{self.base_url}/logs",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {
                "error": f"Cannot connect to agent at {self.base_url}",
            }
        except httpx.HTTPStatusError as e:
            return {
                "error": f"Agent returned {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return {"error": str(e)}
    
    def get_actions(self) -> List[Dict[str, Any]]:
        """
        Get list of available actions.
        
        Returns:
            List of action definitions
        """
        return [
            {
                "id": action.id,
                "name": action.name,
                "description": action.description,
                "risk": action.risk.value,
                "parameters": action.parameters,
            }
            for action in AVAILABLE_ACTIONS
        ]
    
    def execute_action(
        self,
        action_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an action on the agent.
        
        Args:
            action_id: ID of the action to execute
            parameters: Optional parameters for the action
            
        Returns:
            Dict with action result
        """
        # Validate action exists
        action = next((a for a in AVAILABLE_ACTIONS if a.id == action_id), None)
        if not action:
            return {
                "success": False,
                "error": f"Unknown action: {action_id}",
            }
        
        try:
            client = self._get_client()
            request_data = {
                "action": action_id,
                "parameters": parameters or {},
            }
            logger.info(f"Sending action request to {self.base_url}/action: {request_data}")
            response = client.post(
                f"{self.base_url}/action",
                headers=self._headers(),
                json=request_data,
            )
            response.raise_for_status()
            result = response.json()
            result["action"] = action_id
            logger.info(f"Agent response for {action_id}: {result}")
            return result
        except httpx.ConnectError:
            return {
                "success": False,
                "action": action_id,
                "error": f"Cannot connect to agent at {self.base_url}",
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "action": action_id,
                "error": f"Agent returned {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            logger.error(f"Error executing action {action_id}: {e}")
            return {
                "success": False,
                "action": action_id,
                "error": str(e),
            }
    
    def is_action_auto_approved(self, action_id: str) -> bool:
        """
        Check if an action can be auto-executed without user approval.
        
        Args:
            action_id: ID of the action
            
        Returns:
            True if action is low-risk and can be auto-executed
        """
        action = next((a for a in AVAILABLE_ACTIONS if a.id == action_id), None)
        if not action:
            return False
        return action.risk == ActionRisk.LOW
    
    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


def get_agent_client() -> Optional[AgentClient]:
    """
    Get an agent client configured from settings or environment variables.
    
    Priority:
    1. Database settings (from web UI)
    2. Environment variables (fallback)
    
    Returns:
        AgentClient if configured and enabled, None otherwise
    """
    try:
        import os
        from api.utils import _get_setting
        
        # Check if agent is enabled (database setting takes priority)
        agent_enabled = _get_setting("agent_enabled")
        if not agent_enabled:
            # Fallback to environment variable
            agent_enabled = os.getenv("ARES_AGENT_ENABLED", "").lower()
        
        if agent_enabled != "true":
            return None
        
        # Get agent URL (database setting takes priority)
        agent_url = _get_setting("agent_url")
        if not agent_url:
            # Fallback to environment variable
            agent_url = os.getenv("ARES_AGENT_URL", "")
        
        # Get agent API key (database setting takes priority)
        agent_api_key = _get_setting("agent_api_key")
        if not agent_api_key:
            # Fallback to environment variable
            agent_api_key = os.getenv("ARES_AGENT_API_KEY", "")
        
        if not agent_url or not agent_api_key:
            return None
        
        return AgentClient(base_url=agent_url, api_key=agent_api_key)
    except Exception as e:
        logger.error(f"Error creating agent client: {e}")
        return None

