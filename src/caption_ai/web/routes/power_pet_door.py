"""Power Pet Door API endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from caption_ai.power_pet_door import get_power_pet_door_client
from caption_ai.web.state import get_power_pet_door_client as get_state_client, set_power_pet_door_client

router = APIRouter()


def _get_power_pet_door_client():
    """Get or initialize Power Pet Door client."""
    client = get_state_client()
    if client is None:
        client = get_power_pet_door_client()
        set_power_pet_door_client(client)
    return client


@router.get("/api/powerpetdoor/status")
async def get_power_pet_door_status() -> JSONResponse:
    """Get Power Pet Door connection status."""
    client = _get_power_pet_door_client()
    return JSONResponse({
        "enabled": client.enabled,
        "connected": client.enabled,
    })


@router.get("/api/powerpetdoor/door")
async def get_door_state() -> JSONResponse:
    """Get current door state."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        state = await client.get_door_state()
        return JSONResponse(state)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/powerpetdoor/door/open")
async def open_door() -> JSONResponse:
    """Open the door."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        result = await client.open_door()
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/powerpetdoor/door/close")
async def close_door() -> JSONResponse:
    """Close the door."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        result = await client.close_door()
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/powerpetdoor/door/stop")
async def stop_door() -> JSONResponse:
    """Stop the door."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        result = await client.stop_door()
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/powerpetdoor/door/cycle")
async def cycle_door() -> JSONResponse:
    """Cycle the door (open/close)."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        result = await client.cycle_door()
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/powerpetdoor/switch/{switch_name}")
async def get_switch_state(switch_name: str) -> JSONResponse:
    """Get state of a switch."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        state = await client.get_switch_state(switch_name)
        return JSONResponse(state)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/powerpetdoor/switch/{switch_name}/toggle")
async def toggle_switch(switch_name: str) -> JSONResponse:
    """Toggle a switch."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        result = await client.toggle_switch(switch_name)
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/powerpetdoor/switch/{switch_name}/on")
async def turn_on_switch(switch_name: str) -> JSONResponse:
    """Turn on a switch."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        result = await client.turn_on_switch(switch_name)
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/powerpetdoor/switch/{switch_name}/off")
async def turn_off_switch(switch_name: str) -> JSONResponse:
    """Turn off a switch."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        result = await client.turn_off_switch(switch_name)
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/powerpetdoor/sensor/{sensor_name}")
async def get_sensor_value(sensor_name: str) -> JSONResponse:
    """Get value of a sensor."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        state = await client.get_sensor_value(sensor_name)
        return JSONResponse(state)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/powerpetdoor/all")
async def get_all_states() -> JSONResponse:
    """Get all Power Pet Door entity states."""
    try:
        client = _get_power_pet_door_client()
        if not client.enabled:
            return JSONResponse({"error": "Power Pet Door not configured"}, status_code=503)
        states = await client.get_all_states()
        return JSONResponse({"states": states})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

