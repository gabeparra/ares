#!/usr/bin/env python3
"""
Fetch all available models from OpenRouter API and save to JSON.
This helps us keep the model list up-to-date.
"""
import os
import json
import httpx
from typing import Dict, List

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY environment variable not set")
    exit(1)

def fetch_all_models() -> List[Dict]:
    """Fetch all models from OpenRouter API."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{OPENROUTER_BASE_URL}/models",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

def categorize_model(model: Dict) -> str:
    """Categorize model by provider and characteristics."""
    model_id = model.get("id", "").lower()
    name = model.get("name", "").lower()
    
    # Check pricing
    pricing = model.get("pricing", {})
    prompt_price = pricing.get("prompt", "0")
    completion_price = pricing.get("completion", "0")
    
    # Try to parse prices (format: "$0.00015" or "0.00015")
    try:
        prompt_val = float(prompt_price.replace("$", "").replace(",", ""))
        completion_val = float(completion_price.replace("$", "").replace(",", ""))
        avg_price = (prompt_val + completion_val) / 2
    except:
        avg_price = 999  # Unknown pricing
    
    # Free models
    if "free" in model_id or avg_price == 0:
        return "free"
    
    # Economic tier (< $0.50 per 1M tokens average)
    if avg_price < 0.5:
        return "economic"
    
    # Balanced tier ($0.50 - $2.00 per 1M tokens)
    if avg_price < 2.0:
        return "balanced"
    
    # Premium tier (> $2.00 per 1M tokens)
    return "premium"

def main():
    print("Fetching models from OpenRouter...")
    models = fetch_all_models()
    
    if not models:
        print("No models found!")
        return
    
    print(f"Found {len(models)} models")
    
    # Organize models
    organized = {
        "free": [],
        "economic": [],
        "balanced": [],
        "premium": [],
        "specialized": [],
    }
    
    # Special handling for known models
    special_models = {
        "openrouter/auto": {"tier": "auto", "name": "Auto Router (Smart Selection)", "provider": "OpenRouter"},
        "deepseek/deepseek-chat": {"tier": "free", "name": "DeepSeek Chat", "provider": "DeepSeek"},
        "deepseek/deepseek-v3-base:free": {"tier": "free", "name": "DeepSeek V3 Base (Free)", "provider": "DeepSeek"},
    }
    
    for model in models:
        model_id = model.get("id", "")
        
        # Skip if it's a special model we handle manually
        if model_id in special_models:
            continue
        
        # Extract provider from model ID
        provider = model_id.split("/")[0] if "/" in model_id else "Unknown"
        provider = provider.title()
        
        # Get model name
        name = model.get("name", model_id)
        
        # Categorize
        tier = categorize_model(model)
        
        # Check if specialized
        model_id_lower = model_id.lower()
        if any(keyword in model_id_lower for keyword in ["code", "coder", "codestral", "sonar", "r1", "reasoning"]):
            tier = "specialized"
        
        organized[tier].append({
            "id": model_id,
            "name": name,
            "provider": provider,
            "tier": tier,
            "context_length": model.get("context_length"),
            "pricing": model.get("pricing"),
        })
    
    # Sort each tier by name
    for tier in organized:
        organized[tier].sort(key=lambda x: x["name"])
    
    # Save to JSON
    output_file = "openrouter_models.json"
    with open(output_file, "w") as f:
        json.dump(organized, f, indent=2)
    
    print(f"\nModels organized by tier:")
    print(f"  Free: {len(organized['free'])}")
    print(f"  Economic: {len(organized['economic'])}")
    print(f"  Balanced: {len(organized['balanced'])}")
    print(f"  Premium: {len(organized['premium'])}")
    print(f"  Specialized: {len(organized['specialized'])}")
    print(f"\nSaved to {output_file}")
    
    # Print top models in each category
    print("\n=== Top Models by Tier ===")
    for tier, models_list in organized.items():
        if models_list:
            print(f"\n{tier.upper()}:")
            for model in models_list[:10]:  # Top 10 per tier
                pricing = model.get("pricing", {})
                prompt = pricing.get("prompt", "N/A")
                completion = pricing.get("completion", "N/A")
                print(f"  - {model['name']} ({model['id']}) - ${prompt}/${completion} per 1M tokens")

if __name__ == "__main__":
    main()

