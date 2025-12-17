"""Power Pet Door integration via Home Assistant REST API."""

import asyncio
from typing import Any, Optional

import httpx

from caption_ai.config import config


class PowerPetDoorClient:
    """Client for controlling Power Pet Door via Home Assistant."""

    def __init__(self):
        """Initialize Power Pet Door client."""
        self.ha_url = config.home_assistant_url
        self.ha_token = config.home_assistant_token
        self.entity_prefix = config.power_pet_door_entity_prefix
        self.enabled = bool(self.ha_url and self.ha_token)
        
        if self.enabled:
            # Ensure URL doesn't end with /
            self.ha_url = self.ha_url.rstrip('/')
            print(f"[INFO] Power Pet Door client enabled (HA URL: {self.ha_url})")
        else:
            print("[INFO] Power Pet Door client disabled (HA_URL or HA_TOKEN not set)")

    def _get_entity_id(self, entity_type: str, name: str) -> str:
        """Get full entity ID for a Power Pet Door entity."""
        return f"{entity_type}.{self.entity_prefix}_{name}"

    async def _call_service(
        self, 
        domain: str, 
        service: str, 
        entity_id: Optional[str] = None,
        **kwargs
    ) -> dict[str, Any]:
        """Call a Home Assistant service."""
        if not self.enabled:
            raise RuntimeError("Power Pet Door client not enabled")
        
        url = f"{self.ha_url}/api/services/{domain}/{service}"
        headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json",
        }
        
        data = {}
        if entity_id:
            data["entity_id"] = entity_id
        data.update(kwargs)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()

    async def _get_state(self, entity_id: str) -> dict[str, Any]:
        """Get state of a Home Assistant entity."""
        if not self.enabled:
            raise RuntimeError("Power Pet Door client not enabled")
        
        url = f"{self.ha_url}/api/states/{entity_id}"
        headers = {
            "Authorization": f"Bearer {self.ha_token}",
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_door_state(self) -> dict[str, Any]:
        """Get current door state."""
        entity_id = self._get_entity_id("cover", "door")
        return await self._get_state(entity_id)

    async def open_door(self) -> dict[str, Any]:
        """Open the door."""
        entity_id = self._get_entity_id("cover", "door")
        return await self._call_service("cover", "open_cover", entity_id=entity_id)

    async def close_door(self) -> dict[str, Any]:
        """Close the door."""
        entity_id = self._get_entity_id("cover", "door")
        return await self._call_service("cover", "close_cover", entity_id=entity_id)

    async def stop_door(self) -> dict[str, Any]:
        """Stop the door."""
        entity_id = self._get_entity_id("cover", "door")
        return await self._call_service("cover", "stop_cover", entity_id=entity_id)

    async def cycle_door(self) -> dict[str, Any]:
        """Trigger door cycle (open/close)."""
        entity_id = self._get_entity_id("button", "cycle")
        return await self._call_service("button", "press", entity_id=entity_id)

    async def get_switch_state(self, switch_name: str) -> dict[str, Any]:
        """Get state of a switch entity."""
        entity_id = self._get_entity_id("switch", switch_name)
        return await self._get_state(entity_id)

    async def toggle_switch(self, switch_name: str) -> dict[str, Any]:
        """Toggle a switch entity."""
        entity_id = self._get_entity_id("switch", switch_name)
        return await self._call_service("switch", "toggle", entity_id=entity_id)

    async def turn_on_switch(self, switch_name: str) -> dict[str, Any]:
        """Turn on a switch entity."""
        entity_id = self._get_entity_id("switch", switch_name)
        return await self._call_service("switch", "turn_on", entity_id=entity_id)

    async def turn_off_switch(self, switch_name: str) -> dict[str, Any]:
        """Turn off a switch entity."""
        entity_id = self._get_entity_id("switch", switch_name)
        return await self._call_service("switch", "turn_off", entity_id=entity_id)

    async def get_sensor_value(self, sensor_name: str) -> dict[str, Any]:
        """Get value of a sensor entity."""
        entity_id = self._get_entity_id("sensor", sensor_name)
        return await self._get_state(entity_id)

    async def get_all_states(self) -> dict[str, Any]:
        """Get states of all Power Pet Door entities."""
        if not self.enabled:
            raise RuntimeError("Power Pet Door client not enabled")
        
        url = f"{self.ha_url}/api/states"
        headers = {
            "Authorization": f"Bearer {self.ha_token}",
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            all_states = response.json()
            
            # Filter to only Power Pet Door entities
            prefix = f"{self.entity_prefix}_"
            door_states = {}
            for state in all_states:
                entity_id = state.get("entity_id", "")
                if prefix in entity_id:
                    # Extract entity name (e.g., "door" from "cover.power_pet_door_door")
                    parts = entity_id.split(".")
                    if len(parts) == 2:
                        entity_type, full_name = parts
                        if full_name.startswith(prefix):
                            name = full_name[len(prefix):]
                            door_states[f"{entity_type}.{name}"] = state
            
            return door_states


def get_power_pet_door_client() -> PowerPetDoorClient:
    """Get Power Pet Door client instance."""
    return PowerPetDoorClient()

