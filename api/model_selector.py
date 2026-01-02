"""
Smart model selection based on task analysis.
Analyzes the user's message and selects the most appropriate OpenRouter model.
"""
import re
from typing import Dict, List, Optional

# Task patterns and their recommended models
TASK_PATTERNS = {
    "simple": {
        "patterns": [
            r"\b(hi|hello|hey|thanks|thank you|yes|no|ok|okay)\b",
            r"^.{0,50}$",  # Very short messages
        ],
        "models": [
            "deepseek/deepseek-chat",  # Free
            "google/gemini-2.0-flash-exp:free",  # Free
            "openai/gpt-4o-mini",  # Economic
        ],
        "description": "Simple queries, greetings, short responses"
    },
    "coding": {
        "patterns": [
            r"\b(code|function|class|import|def |async |await |python|javascript|typescript|react|vue|sql|api|endpoint)\b",
            r"```[\s\S]*```",  # Code blocks
            r"write.*code|implement|debug|fix.*bug|refactor",
        ],
        "models": [
            "deepseek/deepseek-chat",  # Free and good at coding
            "mistralai/codestral-2501",  # Specialized
            "qwen/qwen-2.5-coder-32b-instruct",  # Specialized
            "openai/gpt-4o",  # Balanced
        ],
        "description": "Code generation, debugging, technical tasks"
    },
    "reasoning": {
        "patterns": [
            r"\b(why|how|explain|analyze|reason|logic|think|solve|problem|calculate|math)\b",
            r"step.*by.*step|show.*work|derive|prove",
        ],
        "models": [
            "deepseek/deepseek-r1",  # Reasoning focused
            "openai/o1-mini",  # Reasoning model
            "anthropic/claude-3.5-sonnet",  # Balanced
            "openai/gpt-4o",  # Balanced
        ],
        "description": "Complex reasoning, math, analysis"
    },
    "creative": {
        "patterns": [
            r"\b(write|story|poem|essay|creative|imagine|describe|narrative|fiction)\b",
            r"write.*about|tell.*story|create.*character",
        ],
        "models": [
            "anthropic/claude-3.5-sonnet",  # Best for creative
            "openai/gpt-4o",  # Good for creative
            "google/gemini-pro-1.5",  # Balanced
        ],
        "description": "Creative writing, storytelling"
    },
    "research": {
        "patterns": [
            r"\b(research|find|search|latest|current|recent|news|information about)\b",
            r"what.*happened|when.*did|who.*is|where.*is",
        ],
        "models": [
            "perplexity/llama-3.1-sonar-large-128k-online",  # Web search
            "perplexity/llama-3.1-sonar-small-128k-online",  # Web search
            "openai/gpt-4o",  # Fallback
        ],
        "description": "Research, web search, current events"
    },
    "conversation": {
        "patterns": [
            r"\b(chat|talk|discuss|conversation|opinion|what.*think|advice)\b",
        ],
        "models": [
            "deepseek/deepseek-chat",  # Free default
            "anthropic/claude-3.5-haiku",  # Economic
            "openai/gpt-4o-mini",  # Economic
        ],
        "description": "General conversation, advice"
    },
    "complex": {
        "patterns": [
            r".{500,}",  # Long messages
            r"\b(complex|detailed|comprehensive|thorough|extensive)\b",
        ],
        "models": [
            "anthropic/claude-3.5-sonnet",  # Best for complex
            "openai/gpt-4o",  # Good for complex
            "google/gemini-pro-1.5",  # Large context
        ],
        "description": "Complex, detailed tasks"
    },
}

# Default fallback models (economic but capable)
DEFAULT_ECONOMIC_MODELS = [
    "deepseek/deepseek-chat",  # Free default
    "google/gemini-2.0-flash-001",  # Economic
    "openai/gpt-4o-mini",  # Economic
]


def analyze_task(message: str) -> Dict[str, any]:
    """
    Analyze a message to determine task type and complexity.
    Returns a dict with task_type, confidence, and recommended models.
    """
    message_lower = message.lower()
    message_length = len(message)
    
    # Check for code blocks
    has_code = bool(re.search(r"```[\s\S]*```", message))
    
    # Score each task type
    task_scores = {}
    for task_type, config in TASK_PATTERNS.items():
        score = 0
        for pattern in config["patterns"]:
            matches = len(re.findall(pattern, message_lower, re.IGNORECASE))
            score += matches
        
        # Boost coding score if code blocks present
        if task_type == "coding" and has_code:
            score += 5
        
        # Boost simple score for very short messages
        if task_type == "simple" and message_length < 50:
            score += 3
        
        # Boost complex score for long messages
        if task_type == "complex" and message_length > 500:
            score += 2
        
        if score > 0:
            task_scores[task_type] = score
    
    # Determine primary task type
    if task_scores:
        primary_task = max(task_scores.items(), key=lambda x: x[1])
        task_type = primary_task[0]
        confidence = min(primary_task[1] / 5.0, 1.0)  # Normalize to 0-1
    else:
        task_type = "conversation"
        confidence = 0.3
    
    # Get recommended models for this task
    recommended_models = TASK_PATTERNS.get(task_type, {}).get("models", DEFAULT_ECONOMIC_MODELS)
    
    return {
        "task_type": task_type,
        "confidence": confidence,
        "recommended_models": recommended_models,
        "description": TASK_PATTERNS.get(task_type, {}).get("description", "General task"),
    }


def select_model_for_task(message: str, use_auto: bool = False, preferred_tier: Optional[str] = None) -> str:
    """
    Select the best model for a given task.
    
    Args:
        message: User's message
        use_auto: If True, use OpenRouter's auto router
        preferred_tier: Preferred cost tier ("free", "economic", "balanced", "premium")
    
    Returns:
        Model ID string
    """
    # If auto router is enabled, use it
    if use_auto:
        return "openrouter/auto"
    
    # Analyze the task
    analysis = analyze_task(message)
    
    # Get recommended models
    models = analysis["recommended_models"]
    
    # If preferred tier is specified, filter models by tier
    # (This would require model tier metadata - for now, just use first recommended)
    if models:
        return models[0]  # Return the first (most recommended) model
    
    # Fallback to default economic model
    return DEFAULT_ECONOMIC_MODELS[0]

