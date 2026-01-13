#!/usr/bin/env python3
"""
Quick validation script for the orchestrator refactoring.

Run this to verify the basic functionality works:
    python3 test_orchestrator_basic.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ares_project.settings')
django.setup()

def test_imports():
    """Test that all new modules can be imported."""
    print("Testing imports...")
    try:
        from ares_mind.memory_store import memory_store
        print("✅ memory_store imported")
        
        from ares_core.prompt_assembler import prompt_assembler
        print("✅ prompt_assembler imported")
        
        from ares_core.orchestrator import orchestrator
        print("✅ orchestrator imported")
        
        from api import debug_views
        print("✅ debug_views imported")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_store():
    """Test memory store basic functionality."""
    print("\nTesting memory store...")
    try:
        from ares_mind.memory_store import memory_store
        
        # Test getting memory layers
        memory = memory_store.get_all_memory_layers(user_id="test_user")
        
        assert "identity" in memory
        assert "factual" in memory
        assert "working" in memory
        assert "episodic" in memory
        print("✅ Memory store has all 4 layers")
        
        # Test formatting for prompt
        formatted = memory_store.format_for_prompt(user_id="test_user")
        assert isinstance(formatted, str)
        print("✅ Memory store can format for prompt")
        
        return True
    except Exception as e:
        print(f"❌ Memory store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_assembler():
    """Test prompt assembler basic functionality."""
    print("\nTesting prompt assembler...")
    try:
        from ares_core.prompt_assembler import prompt_assembler
        
        # Test assembling a prompt
        messages = prompt_assembler.assemble(
            user_id="test_user",
            current_message="Hello, test message",
            session_id=None,
        )
        
        assert isinstance(messages, list)
        assert len(messages) >= 2  # At least system + user
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Hello, test message"
        print("✅ Prompt assembler creates valid messages")
        
        # Check that system prompt is not empty
        assert len(messages[0]["content"]) > 0
        print("✅ System prompt is populated")
        
        return True
    except Exception as e:
        print(f"❌ Prompt assembler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_orchestrator():
    """Test orchestrator basic functionality."""
    print("\nTesting orchestrator...")
    try:
        from ares_core.orchestrator import orchestrator
        
        # Test that orchestrator is initialized
        assert orchestrator.memory_store is not None
        print("✅ Orchestrator has memory store")
        
        assert orchestrator.prompt_assembler is not None
        print("✅ Orchestrator has prompt assembler")
        
        assert orchestrator.router is not None
        print("✅ Orchestrator has model router")
        
        # Test routing
        provider, config = orchestrator.router.route(
            task_context={"message": "test"},
            prefer_local=False
        )
        assert provider in ["local", "openrouter"]
        print(f"✅ Orchestrator can route (selected: {provider})")
        
        return True
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_router():
    """Test model router availability checks."""
    print("\nTesting model router...")
    try:
        from ares_core.orchestrator import orchestrator
        
        router = orchestrator.router
        
        print(f"  Local available: {router.local_available}")
        print(f"  Cloud available: {router.cloud_available}")
        
        if not router.local_available and not router.cloud_available:
            print("⚠️  WARNING: No LLM provider available!")
            print("     Configure Ollama or OpenRouter to use the system")
        else:
            print("✅ At least one LLM provider is available")
        
        return True
    except Exception as e:
        print(f"❌ Model router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("ARES Orchestrator Validation")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Memory Store", test_memory_store),
        ("Prompt Assembler", test_prompt_assembler),
        ("Orchestrator", test_orchestrator),
        ("Model Router", test_model_router),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All validation tests passed!")
        print("\nNext steps:")
        print("  1. Start the Django server: python manage.py runserver")
        print("  2. Test the debug endpoints:")
        print("     - http://localhost:8000/api/v1/debug/status")
        print("     - http://localhost:8000/api/v1/debug/memory?user_id=default")
        print("  3. Try a chat request with the orchestrator")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

