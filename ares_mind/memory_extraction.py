"""
Memory Extraction System for ARES Mind

Uses OpenRouter AI to analyze conversations and extract memory spots,
user facts, preferences, and track AI capabilities.

This module handles:
- Extracting memories from conversations
- Tracking which conversations have been revised
- Maintaining important values from previous extractions
- Manual revision process (run via: python3 manage.py revise_memories)

NOTE: Memory revision is MANUAL only - it makes external API calls to OpenRouter.
      Run it when you want to analyze conversations for new memories.
"""

import json
import os
import httpx
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

logger = None
def _get_logger():
    global logger
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)
    return logger


def _call_openrouter_for_extraction(messages: List[Dict], system_prompt: str) -> Optional[str]:
    """
    Call OpenRouter API for memory extraction analysis.
    
    Returns the response text or None if failed.
    """
    # Get OpenRouter configuration
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        _get_logger().warning("OPENROUTER_API_KEY not set, cannot extract memories")
        return None
    
    # Try to get model from settings
    try:
        from api.utils import _get_setting
        model = _get_setting("openrouter_model")
    except:
        model = None
    
    if not model:
        model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    service_url = os.environ.get("OPENROUTER_SERVICE_URL", "http://localhost:3100")
    
    # Try service URL first (TypeScript wrapper), fallback to direct API
    try:
        # Internal API key for service-to-service authentication
        internal_api_key = os.environ.get("INTERNAL_API_KEY", "change-me-in-production")
        
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "temperature": 0.3,  # Lower temperature for more consistent extraction
            "max_tokens": 4000,
        }
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{service_url}/v1/chat/completions",
                json=payload,
                headers={"X-API-KEY": internal_api_key},
            )
            response.raise_for_status()
            result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0].get("message", {}).get("content", "")
    except Exception as e:
        _get_logger().debug(f"OpenRouter service failed, trying direct API: {e}")
        
        # Fallback to direct OpenRouter API
        try:
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "temperature": 0.3,
                "max_tokens": 4000,
            }
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://github.com/gabeparra/ares",
                        "X-Title": "ARES Memory Extraction",
                    },
                )
                response.raise_for_status()
                result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0].get("message", {}).get("content", "")
        except Exception as e2:
            _get_logger().error(f"OpenRouter direct API also failed: {e2}")
            return None
    
    return None


def _parse_extraction_response(response_text: str) -> Dict:
    """
    Parse the AI's extraction response into structured data.
    
    Expected format is JSON with:
    {
        "user_facts": [...],
        "user_preferences": [...],
        "ai_self_memories": [...],
        "capabilities": [...],
        "general_memories": [...]
    }
    """
    try:
        # Try to extract JSON from the response
        # The AI might wrap JSON in markdown code blocks
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Find the JSON part
            json_start = None
            json_end = None
            for i, line in enumerate(lines):
                if line.strip().startswith("```") and json_start is None:
                    json_start = i + 1
                elif line.strip().startswith("```") and json_start is not None:
                    json_end = i
                    break
            
            if json_start is not None and json_end is not None:
                text = "\n".join(lines[json_start:json_end])
            elif json_start is not None:
                text = "\n".join(lines[json_start:])
        
        # Parse JSON
        data = json.loads(text)
        
        # Ensure all expected keys exist
        result = {
            "user_facts": data.get("user_facts", []),
            "user_preferences": data.get("user_preferences", []),
            "ai_self_memories": data.get("ai_self_memories", []),
            "capabilities": data.get("capabilities", []),
            "general_memories": data.get("general_memories", []),
        }
        
        return result
    except json.JSONDecodeError as e:
        _get_logger().warning(f"Failed to parse extraction response as JSON: {e}")
        _get_logger().debug(f"Response text: {response_text[:500]}")
        # Return empty structure
        return {
            "user_facts": [],
            "user_preferences": [],
            "ai_self_memories": [],
            "capabilities": [],
            "general_memories": [],
        }
    except Exception as e:
        _get_logger().error(f"Unexpected error parsing extraction: {e}")
        return {
            "user_facts": [],
            "user_preferences": [],
            "ai_self_memories": [],
            "capabilities": [],
            "general_memories": [],
        }


def _get_existing_memories_for_session(session_id: str) -> Dict:
    """
    Get existing extracted memories for a session to maintain important values.
    
    Returns a dict with existing memories organized by type.
    """
    try:
        from api.models import MemorySpot
        
        existing = MemorySpot.objects.filter(
            session__session_id=session_id,
            status__in=["extracted", "reviewed", "applied"]
        ).order_by("-importance", "-confidence")
        
        result = {
            "user_facts": [],
            "user_preferences": [],
            "ai_self_memories": [],
            "capabilities": [],
            "general_memories": [],
        }
        
        for spot in existing:
            if spot.memory_type == "user_fact":
                result["user_facts"].append(spot.metadata if isinstance(spot.metadata, dict) else {})
            elif spot.memory_type == "user_preference":
                result["user_preferences"].append(spot.metadata if isinstance(spot.metadata, dict) else {})
            elif spot.memory_type == "ai_self_memory":
                result["ai_self_memories"].append(spot.metadata if isinstance(spot.metadata, dict) else {})
            elif spot.memory_type == "capability":
                result["capabilities"].append(spot.metadata if isinstance(spot.metadata, dict) else {})
            elif spot.memory_type == "general":
                result["general_memories"].append(spot.metadata if isinstance(spot.metadata, dict) else {})
        
        return result
    except Exception as e:
        _get_logger().error(f"Error getting existing memories: {e}")
        return {
            "user_facts": [],
            "user_preferences": [],
            "ai_self_memories": [],
            "capabilities": [],
            "general_memories": [],
        }


def _get_all_existing_memories(user_id: str = "default") -> Dict:
    """
    Get ALL existing extracted memories (across all sessions) to check for redundancies.
    
    Returns a dict with existing memories organized by type.
    Only includes applied or reviewed memories to avoid checking against unverified extractions.
    """
    try:
        from api.models import MemorySpot
        
        existing = MemorySpot.objects.filter(
            user_id=user_id,
            status__in=["reviewed", "applied"]  # Only check against verified memories
        ).order_by("-importance", "-confidence")
        
        result = {
            "user_facts": [],
            "user_preferences": [],
            "ai_self_memories": [],
            "capabilities": [],
            "general_memories": [],
        }
        
        for spot in existing:
            # Use metadata directly (it contains the memory structure)
            # Add importance and confidence if not already in metadata
            memory_entry = dict(spot.metadata) if isinstance(spot.metadata, dict) else {}
            if "importance" not in memory_entry:
                memory_entry["importance"] = spot.importance
            if "confidence" not in memory_entry and hasattr(spot, 'confidence'):
                memory_entry["confidence"] = spot.confidence
            
            if spot.memory_type == "user_fact":
                result["user_facts"].append(memory_entry)
            elif spot.memory_type == "user_preference":
                result["user_preferences"].append(memory_entry)
            elif spot.memory_type == "ai_self_memory":
                result["ai_self_memories"].append(memory_entry)
            elif spot.memory_type == "capability":
                result["capabilities"].append(memory_entry)
            elif spot.memory_type == "general":
                result["general_memories"].append(memory_entry)
        
        return result
    except Exception as e:
        _get_logger().error(f"Error getting all existing memories: {e}")
        return {
            "user_facts": [],
            "user_preferences": [],
            "ai_self_memories": [],
            "capabilities": [],
            "general_memories": [],
        }


def _call_gpt4_for_redundancy_filter(new_memories: Dict, existing_memories: Dict) -> Dict:
    """
    Use GPT-4 to filter redundant memories by comparing new memories against existing ones.
    
    Args:
        new_memories: Dict with structure like extracted_data (user_facts, user_preferences, etc.)
        existing_memories: Dict with existing memories organized by type
    
    Returns:
        Dict with the same structure as new_memories, but with redundant items filtered out
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        _get_logger().warning("OPENROUTER_API_KEY not set, skipping redundancy filtering")
        return new_memories
    
    # Use GPT-4 specifically for redundancy filtering
    model = "openai/gpt-4-turbo"  # Use GPT-4 Turbo for better performance
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    service_url = os.environ.get("OPENROUTER_SERVICE_URL", "http://localhost:3100")
    
    # Build prompt for GPT-4
    filter_prompt = """You are analyzing new memories extracted from a conversation to identify and filter out redundancies with existing memories.

Your task:
1. Compare each new memory against ALL existing memories of the same type
2. Identify redundancies: memories that convey the same or very similar information
3. Keep new memories that:
   - Add genuinely new information
   - Provide significant updates to existing memories (e.g., more specific, higher importance)
   - Don't duplicate information already captured in existing memories

For each memory type:
- user_facts: Check if the same fact (key/value) already exists
- user_preferences: Check if the same preference already exists
- ai_self_memories: Check if similar self-knowledge already exists
- capabilities: Check if the same capability is already tracked
- general_memories: Check if similar content/insights already exist

Be conservative: Only filter out clear redundancies. If there's any doubt, keep the new memory.

Existing memories:
{existing_memories}

New memories to filter:
{new_memories}

Return a JSON object with the same structure as the new_memories input, but containing only the non-redundant memories. If a memory is redundant, omit it from the result.

Format your response as JSON only, no markdown or explanations.""".format(
        existing_memories=json.dumps(existing_memories, indent=2),
        new_memories=json.dumps(new_memories, indent=2)
    )
    
    messages = [
        {
            "role": "system",
            "content": "You are a memory filtering system. Analyze memories for redundancies and return filtered JSON results."
        },
        {
            "role": "user",
            "content": filter_prompt
        }
    ]
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,  # Low temperature for consistent filtering
        "max_tokens": 8000,
    }
    
    try:
        # Try service URL first, fallback to direct API
        try:
            # Internal API key for service-to-service authentication
            internal_api_key = os.environ.get("INTERNAL_API_KEY", "change-me-in-production")
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{service_url}/v1/chat/completions",
                    json=payload,
                    headers={"X-API-KEY": internal_api_key},
                )
                response.raise_for_status()
                result = response.json()
        except Exception as e:
            _get_logger().debug(f"OpenRouter service failed, trying direct API: {e}")
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://github.com/gabeparra/ares",
                        "X-Title": "ARES Memory Redundancy Filtering",
                    },
                )
                response.raise_for_status()
                result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            response_text = result["choices"][0].get("message", {}).get("content", "")
            
            # Parse JSON from response
            text = response_text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                json_start = None
                json_end = None
                for i, line in enumerate(lines):
                    if line.strip().startswith("```") and json_start is None:
                        json_start = i + 1
                    elif line.strip().startswith("```") and json_start is not None:
                        json_end = i
                        break
                
                if json_start is not None and json_end is not None:
                    text = "\n".join(lines[json_start:json_end])
                elif json_start is not None:
                    text = "\n".join(lines[json_start:])
            
            filtered_data = json.loads(text)
            
            # Ensure all expected keys exist
            return {
                "user_facts": filtered_data.get("user_facts", []),
                "user_preferences": filtered_data.get("user_preferences", []),
                "ai_self_memories": filtered_data.get("ai_self_memories", []),
                "capabilities": filtered_data.get("capabilities", []),
                "general_memories": filtered_data.get("general_memories", []),
            }
        else:
            _get_logger().warning("No response from GPT-4 for redundancy filtering, using original memories")
            return new_memories
            
    except json.JSONDecodeError as e:
        _get_logger().warning(f"Failed to parse GPT-4 redundancy filter response: {e}")
        _get_logger().debug(f"Response text: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
        return new_memories
    except Exception as e:
        _get_logger().error(f"Error calling GPT-4 for redundancy filtering: {e}")
        return new_memories


def extract_memories_from_conversation(
    session_id: str,
    user_id: str = "default",
    max_messages: int = 50,
    revision: bool = False
) -> Tuple[int, List[str]]:
    """
    Extract memory spots from a conversation session.
    
    Args:
        session_id: Session ID to extract from
        user_id: User ID
        max_messages: Maximum messages to analyze
        revision: If True, this is a revision pass (maintains important existing values)
    
    Returns:
        (count, errors) - number of memories extracted and list of errors
    """
    try:
        from api.models import ChatSession, ConversationMessage, MemorySpot
        
        # Get the session
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return 0, [f"Session {session_id} not found"]
        
        # Check if already revised (unless this is a new extraction)
        if revision:
            # Check if this session was recently revised
            last_revision = MemorySpot.objects.filter(
                session__session_id=session_id,
                status__in=["extracted", "reviewed", "applied"]
            ).order_by("-extracted_at").first()
            
            if last_revision:
                # Only revise if it's been at least an hour since last revision
                time_since = timezone.now() - last_revision.extracted_at
                if time_since < timedelta(hours=1):
                    return 0, [f"Session revised {time_since} ago, skipping (minimum 1 hour)"]
        
        # Get conversation messages
        messages = list(
            ConversationMessage.objects.filter(session=session)
            .order_by("created_at")[:max_messages]
        )
        
        if len(messages) < 2:  # Need at least user + assistant message
            return 0, ["Conversation too short to extract memories"]
        
        # Build conversation text
        conversation_text = []
        for msg in messages:
            role_name = "User" if msg.role == ConversationMessage.ROLE_USER else "Assistant"
            conversation_text.append(f"{role_name}: {msg.message}")
        
        conversation_str = "\n\n".join(conversation_text)
        
        # Get existing memories if this is a revision
        existing_memories = {}
        if revision:
            existing_memories = _get_existing_memories_for_session(session_id)
        
        # Create extraction prompt
        if revision:
            extraction_prompt = """You are revising memories extracted from a conversation.

Your task is to:
1. Review the existing extracted memories (provided below)
2. Analyze the conversation for any NEW important memories
3. Update or refine existing memories if needed
4. Maintain the most important values that were already sorted out

Focus on:
- **User Facts**: Concrete facts about the user (name, job, location, interests, etc.)
- **User Preferences**: Preferences, communication style, likes/dislikes
- **AI Self Memories**: Things the AI learned about itself, its capabilities, or its behavior
- **Capabilities**: New capabilities demonstrated or areas where the AI improved
- **General Memories**: Other important insights or learnings

IMPORTANT: Only extract NEW memories or update existing ones if there's new information.
Do not duplicate existing memories unless they've changed.

Existing memories:
{existing_memories}

Return your analysis as a JSON object with this structure:
{{
    "user_facts": [
        {{
            "type": "identity|professional|personal|context",
            "key": "fact_key",
            "value": "fact_value",
            "confidence": 0.0-1.0,
            "importance": 1-10
        }}
    ],
    "user_preferences": [
        {{
            "key": "preference_key",
            "value": "preference_value",
            "importance": 1-10
        }}
    ],
    "ai_self_memories": [
        {{
            "category": "identity|milestone|observation|preference|relationship",
            "key": "memory_key",
            "value": "memory_value",
            "importance": 1-10
        }}
    ],
    "capabilities": [
        {{
            "name": "capability_name",
            "domain": "general|coding|reasoning|creative|analysis|memory|tools",
            "description": "description",
            "proficiency_level": 1-10,
            "evidence": ["example1", "example2"]
        }}
    ],
    "general_memories": [
        {{
            "content": "memory_content",
            "importance": 1-10,
            "tags": ["tag1", "tag2"]
        }}
    ]
}}

Only extract memories that are:
- Factual and verifiable
- Important enough to remember (importance >= 5)
- NEW or UPDATED (not duplicates of existing memories)
- Specific and actionable

Be conservative - quality over quantity.""".format(
                existing_memories=json.dumps(existing_memories, indent=2)
            )
        else:
            extraction_prompt = """You are analyzing a conversation to extract important memories and insights.

Your task is to identify:
1. **User Facts**: Concrete facts about the user (name, job, location, interests, etc.)
2. **User Preferences**: Preferences, communication style, likes/dislikes
3. **AI Self Memories**: Things the AI learned about itself, its capabilities, or its behavior
4. **Capabilities**: New capabilities demonstrated or areas where the AI improved
5. **General Memories**: Other important insights or learnings

Return your analysis as a JSON object with this structure:
{{
    "user_facts": [
        {{
            "type": "identity|professional|personal|context",
            "key": "fact_key",
            "value": "fact_value",
            "confidence": 0.0-1.0,
            "importance": 1-10
        }}
    ],
    "user_preferences": [
        {{
            "key": "preference_key",
            "value": "preference_value",
            "importance": 1-10
        }}
    ],
    "ai_self_memories": [
        {{
            "category": "identity|milestone|observation|preference|relationship",
            "key": "memory_key",
            "value": "memory_value",
            "importance": 1-10
        }}
    ],
    "capabilities": [
        {{
            "name": "capability_name",
            "domain": "general|coding|reasoning|creative|analysis|memory|tools",
            "description": "description",
            "proficiency_level": 1-10,
            "evidence": ["example1", "example2"]
        }}
    ],
    "general_memories": [
        {{
            "content": "memory_content",
            "importance": 1-10,
            "tags": ["tag1", "tag2"]
        }}
    ]
}}

Only extract memories that are:
- Factual and verifiable
- Important enough to remember (importance >= 5)
- Not already obvious from the conversation structure
- Specific and actionable

Be conservative - quality over quantity."""

        # Call OpenRouter for extraction
        analysis_messages = [
            {
                "role": "user",
                "content": f"Analyze this conversation and extract memories:\n\n{conversation_str}"
            }
        ]
        
        response_text = _call_openrouter_for_extraction(analysis_messages, extraction_prompt)
        
        if not response_text:
            return 0, ["Failed to get response from OpenRouter"]
        
        # Parse the response
        extracted_data = _parse_extraction_response(response_text)
        
        # Filter redundant memories using GPT-4
        # Get all existing memories to compare against
        all_existing_memories = _get_all_existing_memories(user_id=user_id)
        
        # Check if there are any existing memories to compare against
        has_existing = any(
            len(all_existing_memories.get(key, [])) > 0
            for key in ["user_facts", "user_preferences", "ai_self_memories", "capabilities", "general_memories"]
        )
        
        if has_existing:
            # Use GPT-4 to filter redundancies
            _get_logger().info("Filtering redundant memories using GPT-4...")
            filtered_data = _call_gpt4_for_redundancy_filter(extracted_data, all_existing_memories)
        else:
            # No existing memories to compare against, skip filtering
            _get_logger().info("No existing memories found, skipping redundancy filtering")
            filtered_data = extracted_data
        
        # Log filtering results if filtering was performed
        if has_existing:
            original_count = (
                len(extracted_data.get("user_facts", [])) +
                len(extracted_data.get("user_preferences", [])) +
                len(extracted_data.get("ai_self_memories", [])) +
                len(extracted_data.get("capabilities", [])) +
                len(extracted_data.get("general_memories", []))
            )
            filtered_count = (
                len(filtered_data.get("user_facts", [])) +
                len(filtered_data.get("user_preferences", [])) +
                len(filtered_data.get("ai_self_memories", [])) +
                len(filtered_data.get("capabilities", [])) +
                len(filtered_data.get("general_memories", []))
            )
            filtered_out = original_count - filtered_count
            
            if filtered_out > 0:
                _get_logger().info(f"GPT-4 filtered out {filtered_out} redundant memories ({original_count} -> {filtered_count})")
            else:
                _get_logger().info("GPT-4 redundancy check: no redundancies found, all memories kept")
        
        # Use filtered data for storage
        extracted_data = filtered_data
        
        # Store extracted memories
        extracted_count = 0
        errors = []
        
        with transaction.atomic():
            # Store user facts
            for fact_data in extracted_data.get("user_facts", []):
                try:
                    # Check if this fact already exists (avoid duplicates in revision)
                    if revision:
                        fact_key = fact_data.get("key")
                        if fact_key:
                            # Check existing spots for this session and type
                            existing_spots = MemorySpot.objects.filter(
                                session__session_id=session_id,
                                memory_type=MemorySpot.TYPE_USER_FACT,
                                status__in=["extracted", "reviewed", "applied"]
                            )
                            existing = None
                            for spot in existing_spots:
                                spot_meta = spot.metadata if isinstance(spot.metadata, dict) else {}
                                if spot_meta.get("key") == fact_key:
                                    existing = spot
                                    break
                            
                            if existing:
                                # Update if new one has higher importance/confidence
                                if (fact_data.get("importance", 0) > existing.importance or
                                    fact_data.get("confidence", 0) > existing.confidence):
                                    existing.metadata = fact_data
                                    existing.content = json.dumps(fact_data)
                                    existing.confidence = fact_data.get("confidence", existing.confidence)
                                    existing.importance = fact_data.get("importance", existing.importance)
                                    existing.save()
                                    extracted_count += 1
                                continue
                    
                    MemorySpot.objects.create(
                        session=session,
                        user_id=user_id,
                        memory_type=MemorySpot.TYPE_USER_FACT,
                        content=json.dumps(fact_data),
                        metadata=fact_data,
                        confidence=fact_data.get("confidence", 0.5),
                        importance=fact_data.get("importance", 5),
                        source_conversation=conversation_str[:500],  # First 500 chars
                    )
                    extracted_count += 1
                except Exception as e:
                    errors.append(f"Failed to store user fact: {e}")
            
            # Store user preferences
            for pref_data in extracted_data.get("user_preferences", []):
                try:
                    if revision:
                        pref_key = pref_data.get("key")
                        if pref_key:
                            existing_spots = MemorySpot.objects.filter(
                                session__session_id=session_id,
                                memory_type=MemorySpot.TYPE_USER_PREFERENCE,
                                status__in=["extracted", "reviewed", "applied"]
                            )
                            existing = None
                            for spot in existing_spots:
                                spot_meta = spot.metadata if isinstance(spot.metadata, dict) else {}
                                if spot_meta.get("key") == pref_key:
                                    existing = spot
                                    break
                            
                            if existing:
                                if pref_data.get("importance", 0) > existing.importance:
                                    existing.metadata = pref_data
                                    existing.content = json.dumps(pref_data)
                                    existing.importance = pref_data.get("importance", existing.importance)
                                    existing.save()
                                    extracted_count += 1
                                continue
                    
                    MemorySpot.objects.create(
                        session=session,
                        user_id=user_id,
                        memory_type=MemorySpot.TYPE_USER_PREFERENCE,
                        content=json.dumps(pref_data),
                        metadata=pref_data,
                        importance=pref_data.get("importance", 5),
                        source_conversation=conversation_str[:500],
                    )
                    extracted_count += 1
                except Exception as e:
                    errors.append(f"Failed to store user preference: {e}")
            
            # Store AI self memories
            for mem_data in extracted_data.get("ai_self_memories", []):
                try:
                    if revision:
                        mem_key = mem_data.get("key")
                        if mem_key:
                            existing_spots = MemorySpot.objects.filter(
                                session__session_id=session_id,
                                memory_type=MemorySpot.TYPE_AI_SELF_MEMORY,
                                status__in=["extracted", "reviewed", "applied"]
                            )
                            existing = None
                            for spot in existing_spots:
                                spot_meta = spot.metadata if isinstance(spot.metadata, dict) else {}
                                if spot_meta.get("key") == mem_key:
                                    existing = spot
                                    break
                            
                            if existing:
                                if mem_data.get("importance", 0) > existing.importance:
                                    existing.metadata = mem_data
                                    existing.content = json.dumps(mem_data)
                                    existing.importance = mem_data.get("importance", existing.importance)
                                    existing.save()
                                    extracted_count += 1
                                continue
                    
                    MemorySpot.objects.create(
                        session=session,
                        user_id=user_id,
                        memory_type=MemorySpot.TYPE_AI_SELF_MEMORY,
                        content=json.dumps(mem_data),
                        metadata=mem_data,
                        importance=mem_data.get("importance", 5),
                        source_conversation=conversation_str[:500],
                    )
                    extracted_count += 1
                except Exception as e:
                    errors.append(f"Failed to store AI self memory: {e}")
            
            # Store capabilities
            for cap_data in extracted_data.get("capabilities", []):
                try:
                    if revision:
                        cap_name = cap_data.get("name")
                        if cap_name:
                            existing_spots = MemorySpot.objects.filter(
                                session__session_id=session_id,
                                memory_type=MemorySpot.TYPE_CAPABILITY,
                                status__in=["extracted", "reviewed", "applied"]
                            )
                            existing = None
                            for spot in existing_spots:
                                spot_meta = spot.metadata if isinstance(spot.metadata, dict) else {}
                                if spot_meta.get("name") == cap_name:
                                    existing = spot
                                    break
                            
                            if existing:
                                if cap_data.get("proficiency_level", 0) > existing.importance:
                                    existing.metadata = cap_data
                                    existing.content = json.dumps(cap_data)
                                    existing.importance = cap_data.get("proficiency_level", existing.importance)
                                    existing.save()
                                    extracted_count += 1
                                continue
                    
                    MemorySpot.objects.create(
                        session=session,
                        user_id=user_id,
                        memory_type=MemorySpot.TYPE_CAPABILITY,
                        content=json.dumps(cap_data),
                        metadata=cap_data,
                        importance=cap_data.get("proficiency_level", 5),
                        source_conversation=conversation_str[:500],
                    )
                    extracted_count += 1
                except Exception as e:
                    errors.append(f"Failed to store capability: {e}")
            
            # Store general memories
            for gen_data in extracted_data.get("general_memories", []):
                try:
                    MemorySpot.objects.create(
                        session=session,
                        user_id=user_id,
                        memory_type=MemorySpot.TYPE_GENERAL,
                        content=gen_data.get("content", ""),
                        metadata=gen_data,
                        importance=gen_data.get("importance", 5),
                        source_conversation=conversation_str[:500],
                    )
                    extracted_count += 1
                except Exception as e:
                    errors.append(f"Failed to store general memory: {e}")
        
        return extracted_count, errors
        
    except Exception as e:
        _get_logger().error(f"Unexpected error in extract_memories_from_conversation: {e}")
        return 0, [f"Unexpected error: {str(e)}"]


def revise_memories(limit: int = 20, days_back: Optional[int] = None) -> Dict:
    """
    Manual revision process: Re-analyze conversations to extract new memories
    and maintain important existing values.
    
    NOTE: This function makes external API calls to OpenRouter. Run manually
    via: python3 manage.py revise_memories
    
    Args:
        limit: Maximum number of sessions to process per run
        days_back: How many days back to look for sessions (None = all sessions)
    
    Returns:
        Dict with stats about the revision process
    """
    try:
        from api.models import ChatSession, MemorySpot, ConversationMessage
        from django.db.models import Count
        
        _get_logger().info("Starting manual memory revision...")
        
        # Get sessions that:
        # 1. Have at least 5 messages
        # 2. Haven't been revised in the last hour
        # 3. Have NOT been reviewed, applied, or rejected (these are final states)
        # 4. Optionally filtered by update date if days_back is specified
        cutoff_time = timezone.now() - timedelta(hours=1)
        
        # Get recently revised sessions (skip these)
        recently_revised = set(
            MemorySpot.objects.filter(
                extracted_at__gte=cutoff_time
            ).values_list("session__session_id", flat=True).distinct()
        )
        
        # Get sessions with final status (reviewed, applied, rejected) - never reprocess these
        final_status_sessions = set(
            MemorySpot.objects.exclude(session__isnull=True)
            .filter(status__in=[
                MemorySpot.STATUS_REVIEWED,
                MemorySpot.STATUS_APPLIED,
                MemorySpot.STATUS_REJECTED
            ])
            .values_list("session__session_id", flat=True)
            .distinct()
        )
        
        # Build query for sessions with enough messages
        # Exclude recently revised and final status sessions
        sessions_query = ChatSession.objects.exclude(
            session_id__in=recently_revised
        ).exclude(
            session_id__in=final_status_sessions
        ).annotate(
            message_count=Count("messages")
        ).filter(
            message_count__gte=5
        )
        
        # Optionally filter by date if days_back is specified
        if days_back is not None:
            date_cutoff = timezone.now() - timedelta(days=days_back)
            sessions_query = sessions_query.filter(updated_at__gte=date_cutoff)
            _get_logger().info(f"Filtering sessions updated in the last {days_back} days")
        else:
            _get_logger().info("Processing all sessions (no date filter)")
        
        # Order by most recently updated and apply limit
        sessions = sessions_query.order_by("-updated_at")[:limit]
        
        total_sessions = sessions.count()
        _get_logger().info(f"Found {total_sessions} sessions to revise")
        
        stats = {
            "sessions_processed": 0,
            "sessions_skipped": 0,
            "total_extracted": 0,
            "errors": [],
        }
        
        for session in sessions:
            try:
                # Check if session was revised less than an hour ago
                last_revision = MemorySpot.objects.filter(
                    session__session_id=session.session_id
                ).order_by("-extracted_at").first()
                
                if last_revision:
                    time_since = timezone.now() - last_revision.extracted_at
                    if time_since < timedelta(hours=1):
                        stats["sessions_skipped"] += 1
                        continue
                
                # Extract memories (revision mode)
                count, errors = extract_memories_from_conversation(
                    session_id=session.session_id,
                    user_id="default",
                    revision=True,
                )
                
                stats["sessions_processed"] += 1
                stats["total_extracted"] += count
                
                if errors:
                    stats["errors"].extend(errors)
                
                _get_logger().info(
                    f"Revised session {session.session_id}: {count} memories extracted"
                )
                
            except Exception as e:
                _get_logger().error(f"Error revising session {session.session_id}: {e}")
                stats["errors"].append(f"Session {session.session_id}: {str(e)}")
        
        _get_logger().info(
            f"Manual revision complete: {stats['sessions_processed']} processed, "
            f"{stats['total_extracted']} memories extracted"
        )
        
        return stats
        
    except Exception as e:
        _get_logger().error(f"Manual revision failed: {e}")
        return {"error": str(e)}


def apply_memory_spot(memory_spot_id: int) -> Tuple[bool, str]:
    """
    Apply a memory spot to the appropriate memory system.
    
    Returns (success, message)
    """
    try:
        from api.models import MemorySpot, UserFact, UserPreference, AISelfMemory, AICapability
        
        spot = MemorySpot.objects.get(id=memory_spot_id)
        
        if spot.status == MemorySpot.STATUS_APPLIED:
            return False, "Memory spot already applied"
        
        metadata = spot.metadata if isinstance(spot.metadata, dict) else {}
        
        with transaction.atomic():
            if spot.memory_type == MemorySpot.TYPE_USER_FACT:
                # Apply as UserFact
                fact_type = metadata.get("type", "context")
                fact_key = metadata.get("key", "")
                fact_value = metadata.get("value", "")
                confidence = metadata.get("confidence", spot.confidence)
                
                if fact_key and fact_value:
                    UserFact.objects.update_or_create(
                        user_id=spot.user_id,
                        fact_type=fact_type,
                        fact_key=fact_key,
                        defaults={
                            "fact_value": fact_value,
                            "source": UserFact.SOURCE_CONVERSATION,
                            "confidence": confidence,
                        }
                    )
            
            elif spot.memory_type == MemorySpot.TYPE_USER_PREFERENCE:
                # Apply as UserPreference
                pref_key = metadata.get("key", "")
                pref_value = metadata.get("value", "")
                
                if pref_key and pref_value:
                    UserPreference.objects.update_or_create(
                        user_id=spot.user_id,
                        preference_key=pref_key,
                        defaults={
                            "preference_value": pref_value,
                        }
                    )
            
            elif spot.memory_type == MemorySpot.TYPE_AI_SELF_MEMORY:
                # Apply as AISelfMemory
                category = metadata.get("category", "observation")
                mem_key = metadata.get("key", "")
                mem_value = metadata.get("value", "")
                importance = metadata.get("importance", spot.importance)
                
                if mem_key and mem_value:
                    AISelfMemory.objects.update_or_create(
                        category=category,
                        memory_key=mem_key,
                        defaults={
                            "memory_value": mem_value,
                            "importance": importance,
                        }
                    )
            
            elif spot.memory_type == MemorySpot.TYPE_CAPABILITY:
                # Apply as AICapability
                cap_name = metadata.get("name", "")
                domain = metadata.get("domain", "general")
                description = metadata.get("description", "")
                proficiency = metadata.get("proficiency_level", 5)
                evidence = metadata.get("evidence", [])
                
                if cap_name:
                    capability, created = AICapability.objects.update_or_create(
                        capability_name=cap_name,
                        domain=domain,
                        defaults={
                            "description": description,
                            "proficiency_level": proficiency,
                            "evidence": evidence,
                            "last_demonstrated": timezone.now(),
                        }
                    )
                    if not created and proficiency > capability.proficiency_level:
                        # Update if proficiency increased
                        capability.proficiency_level = proficiency
                        capability.evidence = evidence
                        capability.last_demonstrated = timezone.now()
                        capability.save()
            
            # Mark as applied
            spot.status = MemorySpot.STATUS_APPLIED
            spot.applied_at = timezone.now()
            spot.save()
        
        return True, "Memory spot applied successfully"
        
    except MemorySpot.DoesNotExist:
        return False, "Memory spot not found"
    except Exception as e:
        _get_logger().error(f"Error applying memory spot: {e}")
        return False, f"Error applying memory spot: {str(e)}"


def auto_apply_high_confidence_memories(confidence_threshold: float = 0.8):
    """
    Automatically apply memory spots with high confidence.
    
    Useful for running in background to continuously improve the system.
    """
    try:
        from api.models import MemorySpot
        
        high_confidence_spots = MemorySpot.objects.filter(
            status=MemorySpot.STATUS_EXTRACTED,
            confidence__gte=confidence_threshold,
            importance__gte=7,  # Also require high importance
        )
        
        applied_count = 0
        errors = []
        
        for spot in high_confidence_spots:
            success, message = apply_memory_spot(spot.id)
            if success:
                applied_count += 1
            else:
                errors.append(f"Spot {spot.id}: {message}")
        
        return applied_count, errors
    except Exception as e:
        _get_logger().error(f"Auto-apply failed: {e}")
        return 0, [str(e)]

