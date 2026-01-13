"""
Memory Store - Four-Layer Memory System for ARES

This module implements the centralized memory architecture:
1. Identity Memory - Long-term, slow-changing (communication style, habits, personality)
2. Factual Memory - Long-term stable facts (timezone, location, tools, projects)
3. Working Memory - Short-term, rebuilt every request (date/time, calendar, active task)
4. Episodic Memory - Recent conversational context (summarized tone, open threads)

All memory is stored in structured JSON and persisted to the database.
LLMs must NEVER own memory - they are stateless reasoning engines.
"""

import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Centralized memory store managing all four memory layers.
    
    This is the single source of truth for AI memory. LLMs are stateless
    and receive memory through structured prompt injection only.
    """
    
    def __init__(self):
        """Initialize memory store."""
        pass
    
    # =========================================================================
    # IDENTITY MEMORY (Layer 1)
    # =========================================================================
    
    def get_identity_memory(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Get identity memory for a user.
        
        Identity memory is long-term and slow-changing:
        - Communication style preferences
        - Habits and routines
        - Personality traits
        - Repeated frustrations or interests
        
        Extracted mostly from small talk and behavioral patterns.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with identity memory structure
        """
        from api.models import UserPreference
        
        try:
            # Get identity-related preferences
            # We use UserPreference with a special prefix for identity memories
            identity_prefs = UserPreference.objects.filter(
                user_id=user_id,
                preference_key__startswith="identity_"
            )
            
            identity = {
                "communication_style": {},
                "habits": {},
                "personality_traits": {},
                "interests": {},
            }
            
            for pref in identity_prefs:
                # Parse preference key (e.g., "identity_communication_style_directness")
                parts = pref.preference_key.split("_", 2)
                if len(parts) >= 3:
                    category = parts[1]  # e.g., "communication", "habits"
                    key = parts[2] if len(parts) > 2 else ""
                    
                    if category in ["communication", "style"]:
                        identity["communication_style"][key] = pref.preference_value
                    elif category == "habits":
                        identity["habits"][key] = pref.preference_value
                    elif category in ["personality", "traits"]:
                        identity["personality_traits"][key] = pref.preference_value
                    elif category == "interests":
                        identity["interests"][key] = pref.preference_value
            
            return identity
            
        except Exception as e:
            logger.error(f"Error getting identity memory for {user_id}: {e}")
            return {
                "communication_style": {},
                "habits": {},
                "personality_traits": {},
                "interests": {},
            }
    
    def update_identity_memory(
        self, 
        user_id: str, 
        category: str, 
        key: str, 
        value: str
    ) -> bool:
        """
        Update a specific identity memory entry.
        
        Args:
            user_id: User identifier
            category: Category (communication_style, habits, personality_traits, interests)
            key: Specific key within category
            value: Value to store
            
        Returns:
            True if successful, False otherwise
        """
        from api.models import UserPreference
        
        try:
            # Create preference key with identity prefix
            pref_key = f"identity_{category}_{key}"
            
            UserPreference.objects.update_or_create(
                user_id=user_id,
                preference_key=pref_key,
                defaults={"preference_value": value}
            )
            
            logger.info(f"Updated identity memory for {user_id}: {category}.{key}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating identity memory: {e}")
            return False
    
    # =========================================================================
    # FACTUAL MEMORY (Layer 2)
    # =========================================================================
    
    def get_factual_memory(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Get factual memory for a user.
        
        Factual memory contains stable, verified facts:
        - Timezone
        - Location
        - Tools used
        - Projects being worked on
        - System setup (local LLM + cloud fallback)
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with factual memory structure
        """
        from api.models import UserFact
        
        try:
            facts = UserFact.objects.filter(user_id=user_id)
            
            factual = {
                "identity": {},  # Name, age, location
                "professional": {},  # Job, company, skills
                "personal": {},  # Hobbies, interests
                "context": {},  # Current projects, tools, system setup
            }
            
            for fact in facts:
                if fact.fact_type == UserFact.TYPE_IDENTITY:
                    factual["identity"][fact.fact_key] = fact.fact_value
                elif fact.fact_type == UserFact.TYPE_PROFESSIONAL:
                    factual["professional"][fact.fact_key] = fact.fact_value
                elif fact.fact_type == UserFact.TYPE_PERSONAL:
                    factual["personal"][fact.fact_key] = fact.fact_value
                elif fact.fact_type == UserFact.TYPE_CONTEXT:
                    factual["context"][fact.fact_key] = fact.fact_value
            
            return factual
            
        except Exception as e:
            logger.error(f"Error getting factual memory for {user_id}: {e}")
            return {
                "identity": {},
                "professional": {},
                "personal": {},
                "context": {},
            }
    
    def update_factual_memory(
        self,
        user_id: str,
        fact_type: str,
        key: str,
        value: str,
        confidence: float = 1.0
    ) -> bool:
        """
        Update a specific factual memory entry.
        
        Args:
            user_id: User identifier
            fact_type: Type (identity, professional, personal, context)
            key: Fact key
            value: Fact value
            confidence: Confidence level (0.0-1.0)
            
        Returns:
            True if successful, False otherwise
        """
        from api.models import UserFact
        
        try:
            UserFact.objects.update_or_create(
                user_id=user_id,
                fact_type=fact_type,
                fact_key=key,
                defaults={
                    "fact_value": value,
                    "confidence": confidence,
                    "source": UserFact.SOURCE_CONVERSATION,
                }
            )
            
            logger.info(f"Updated factual memory for {user_id}: {fact_type}.{key}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating factual memory: {e}")
            return False
    
    # =========================================================================
    # WORKING MEMORY (Layer 3)
    # =========================================================================
    
    def build_working_memory(
        self,
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build working memory for the current request.
        
        Working memory is rebuilt on EVERY request and contains:
        - Current date/time
        - Calendar snapshot (today / near future)
        - Active task or focus
        - Short-term mood or stress (if relevant)
        
        This is ephemeral and NOT persisted long-term.
        
        Args:
            user_id: User identifier
            session_id: Session identifier (optional)
            
        Returns:
            Dict with working memory structure
        """
        working = {
            "timestamp": timezone.now().isoformat(),
            "date": timezone.now().strftime("%Y-%m-%d"),
            "time": timezone.now().strftime("%H:%M:%S"),
            "day_of_week": timezone.now().strftime("%A"),
            "calendar": None,
            "active_task": None,
            "context": None,
        }
        
        # Get calendar snapshot
        try:
            from api.calendar_views import get_calendar_context_summary
            calendar_summary = get_calendar_context_summary(user_id=user_id, message="")
            working["calendar"] = calendar_summary
        except Exception as e:
            logger.warning(f"Failed to get calendar for working memory: {e}")
            working["calendar"] = "Calendar not available"
        
        # Get active task/focus from session (if exists)
        if session_id:
            try:
                from api.models import ChatSession
                session = ChatSession.objects.filter(session_id=session_id).first()
                if session and session.title:
                    working["active_task"] = session.title
            except Exception as e:
                logger.warning(f"Failed to get active task: {e}")
        
        return working
    
    # =========================================================================
    # EPISODIC MEMORY (Layer 4)
    # =========================================================================
    
    def get_episodic_memory(
        self,
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get episodic memory (recent conversational context).
        
        Episodic memory is NOT raw chat logs. It contains:
        - Summarized conversational tone
        - What the user has been discussing recently
        - Open conversational threads
        - Recent focus areas
        
        Args:
            user_id: User identifier
            session_id: Session identifier (optional)
            
        Returns:
            Dict with episodic memory structure
        """
        from api.models import ConversationSummary
        
        episodic = {
            "recent_topics": [],
            "conversational_tone": None,
            "open_threads": [],
            "recent_focus": None,
        }
        
        if not session_id:
            return episodic
        
        try:
            # Get conversation summary for this session
            summary = ConversationSummary.objects.filter(
                session__session_id=session_id,
                user_id=user_id
            ).first()
            
            if summary:
                episodic["recent_topics"] = summary.topics or []
                episodic["recent_focus"] = summary.summary
                # key_facts contains extracted information
                if summary.key_facts:
                    episodic["open_threads"] = summary.key_facts
            
            return episodic
            
        except Exception as e:
            logger.error(f"Error getting episodic memory: {e}")
            return episodic
    
    def update_episodic_memory(
        self,
        user_id: str,
        session_id: str,
        summary: str,
        topics: list,
        key_facts: list
    ) -> bool:
        """
        Update episodic memory for a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            summary: Conversation summary (NOT raw dialogue)
            topics: List of topics discussed
            key_facts: Key facts or open threads
            
        Returns:
            True if successful, False otherwise
        """
        from api.models import ConversationSummary, ChatSession, ConversationMessage
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
            message_count = ConversationMessage.objects.filter(session=session).count()
            
            ConversationSummary.objects.update_or_create(
                session=session,
                user_id=user_id,
                defaults={
                    "summary": summary,
                    "topics": topics,
                    "key_facts": key_facts,
                    "message_count": message_count,
                }
            )
            
            logger.info(f"Updated episodic memory for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating episodic memory: {e}")
            return False
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_all_memory_layers(
        self,
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all four memory layers in one call.
        
        This is used by the prompt assembler to inject memory into prompts.
        
        Args:
            user_id: User identifier
            session_id: Session identifier (optional)
            
        Returns:
            Dict with all four memory layers
        """
        return {
            "identity": self.get_identity_memory(user_id),
            "factual": self.get_factual_memory(user_id),
            "working": self.build_working_memory(user_id, session_id),
            "episodic": self.get_episodic_memory(user_id, session_id),
        }
    
    def format_for_prompt(
        self,
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> str:
        """
        Format all memory layers into a structured prompt string.
        
        This is a convenience method for the prompt assembler.
        
        Args:
            user_id: User identifier
            session_id: Session identifier (optional)
            
        Returns:
            Formatted memory string for prompt injection
        """
        memory = self.get_all_memory_layers(user_id, session_id)
        
        sections = []
        
        # Identity Memory
        if any(memory["identity"].values()):
            sections.append("## Identity & Communication")
            if memory["identity"]["communication_style"]:
                sections.append("### Communication Style")
                for key, value in memory["identity"]["communication_style"].items():
                    sections.append(f"- {key}: {value}")
            if memory["identity"]["habits"]:
                sections.append("### Habits")
                for key, value in memory["identity"]["habits"].items():
                    sections.append(f"- {key}: {value}")
            if memory["identity"]["personality_traits"]:
                sections.append("### Personality Traits")
                for key, value in memory["identity"]["personality_traits"].items():
                    sections.append(f"- {key}: {value}")
        
        # Factual Memory
        if any(memory["factual"].values()):
            sections.append("\n## User Facts")
            for category, facts in memory["factual"].items():
                if facts:
                    sections.append(f"### {category.title()}")
                    for key, value in facts.items():
                        sections.append(f"- {key}: {value}")
        
        # Working Memory
        sections.append("\n## Current Context")
        sections.append(f"- Date: {memory['working']['date']}")
        sections.append(f"- Time: {memory['working']['time']}")
        sections.append(f"- Day: {memory['working']['day_of_week']}")
        if memory["working"]["active_task"]:
            sections.append(f"- Active Task: {memory['working']['active_task']}")
        if memory["working"]["calendar"]:
            sections.append("\n### Calendar")
            sections.append(memory["working"]["calendar"])
        
        # Episodic Memory
        if memory["episodic"]["recent_focus"] or memory["episodic"]["recent_topics"]:
            sections.append("\n## Recent Conversation Context")
            if memory["episodic"]["recent_focus"]:
                sections.append(f"Summary: {memory['episodic']['recent_focus']}")
            if memory["episodic"]["recent_topics"]:
                sections.append(f"Topics: {', '.join(memory['episodic']['recent_topics'])}")
        
        return "\n".join(sections)


# Singleton instance
memory_store = MemoryStore()

