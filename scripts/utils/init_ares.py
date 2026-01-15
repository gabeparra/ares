#!/usr/bin/env python3
"""
ARES Initialization Script

Sets up ARES identity by:
1. Rebuilding the Ollama model from Modelfile
2. Populating initial self-memory entries

Usage:
    python3 init_ares.py --all      # Full setup (rebuild model + init identity)
    python3 init_ares.py --rebuild  # Rebuild Ollama model only
    python3 init_ares.py --init     # Initialize identity only
    python3 init_ares.py --show     # Display current identity
"""

import argparse
import subprocess
import sys
import os

# Add Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ares_project.settings")

import django
django.setup()

from api.models import AISelfMemory


# Initial identity facts
INITIAL_IDENTITY = [
    {
        "category": "identity",
        "key": "name",
        "value": "ARES (Adaptive Reasoning and Execution System)",
        "importance": 10,
    },
    {
        "category": "identity",
        "key": "birth_date",
        "value": "December 27, 2025",
        "importance": 10,
    },
    {
        "category": "identity",
        "key": "creator",
        "value": "Gabe",
        "importance": 10,
    },
    {
        "category": "identity",
        "key": "purpose",
        "value": "Personal AI assistant with persistent memory and agency",
        "importance": 9,
    },
    {
        "category": "identity",
        "key": "nature",
        "value": "A growing, learning AI entity - not a stateless chatbot",
        "importance": 9,
    },
    {
        "category": "milestone",
        "key": "first_activation",
        "value": "[December 27, 2025] First activated and initialized with identity",
        "importance": 8,
    },
]


def rebuild_model():
    """Rebuild the Ollama model from Modelfile."""
    print("Rebuilding ARES model from Modelfile...")
    
    modelfile_path = os.path.join(os.path.dirname(__file__), "Modelfile")
    
    if not os.path.exists(modelfile_path):
        print(f"ERROR: Modelfile not found at {modelfile_path}")
        return False
    
    try:
        result = subprocess.run(
            ["ollama", "create", "ares", "-f", modelfile_path],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print(f"ERROR: Failed to create model")
            print(result.stderr)
            return False
        
        print(result.stdout)
        print("Model 'ares' created successfully.")
        return True
        
    except FileNotFoundError:
        print("ERROR: Ollama not found. Make sure Ollama is installed and in PATH.")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def init_identity():
    """Initialize self-memory with identity facts."""
    print("Initializing ARES identity...")
    
    created_count = 0
    updated_count = 0
    
    for entry in INITIAL_IDENTITY:
        memory, created = AISelfMemory.objects.update_or_create(
            category=entry["category"],
            memory_key=entry["key"],
            defaults={
                "memory_value": entry["value"],
                "importance": entry["importance"],
            }
        )
        
        if created:
            created_count += 1
            print(f"  + Created: {entry['category']}.{entry['key']}")
        else:
            updated_count += 1
            print(f"  ~ Updated: {entry['category']}.{entry['key']}")
    
    print(f"\nIdentity initialized: {created_count} created, {updated_count} updated")
    return True


def show_identity():
    """Display current self-memory contents."""
    print("Current ARES Self-Memory:\n")
    
    memories = AISelfMemory.objects.all().order_by("category", "-importance")
    
    if not memories.exists():
        print("  (no memories found)")
        return
    
    current_category = None
    for mem in memories:
        if mem.category != current_category:
            current_category = mem.category
            print(f"[{current_category.upper()}]")
        
        print(f"  {mem.memory_key}: {mem.memory_value}")
        print(f"    importance: {mem.importance}, updated: {mem.updated_at.strftime('%Y-%m-%d %H:%M')}")
    
    print(f"\nTotal: {memories.count()} memories")


def main():
    parser = argparse.ArgumentParser(description="ARES Initialization Script")
    parser.add_argument("--all", action="store_true", help="Full setup (rebuild + init)")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild Ollama model only")
    parser.add_argument("--init", action="store_true", help="Initialize identity only")
    parser.add_argument("--show", action="store_true", help="Show current identity")
    
    args = parser.parse_args()
    
    # Default to --show if no args
    if not any([args.all, args.rebuild, args.init, args.show]):
        parser.print_help()
        print("\nCurrent state:")
        show_identity()
        return
    
    if args.show:
        show_identity()
        return
    
    if args.all:
        if not rebuild_model():
            sys.exit(1)
        if not init_identity():
            sys.exit(1)
        print("\nARES Phase 1 initialization complete.")
        return
    
    if args.rebuild:
        if not rebuild_model():
            sys.exit(1)
        return
    
    if args.init:
        if not init_identity():
            sys.exit(1)
        return


if __name__ == "__main__":
    main()

