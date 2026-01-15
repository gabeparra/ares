#!/usr/bin/env python3
"""
Test script to verify orchestrator works inside Docker.
Run this inside the Docker container (from project root):
    docker-compose -f internaldocuments/docker/docker-compose.yml exec backend python test_docker_orchestrator.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ares_project.settings')
django.setup()

def test_orchestrator_in_docker():
    """Test orchestrator functionality inside Docker."""
    print("=" * 60)
    print("ARES Orchestrator Docker Validation")
    print("=" * 60)
    
    results = []
    
    # Test 1: Import orchestrator
    print("\n[Test 1] Importing orchestrator...")
    try:
        from ares_core.orchestrator import orchestrator
        print("✅ Orchestrator imported")
        results.append(("Import orchestrator", True))
    except Exception as e:
        print(f"❌ Failed: {e}")
        results.append(("Import orchestrator", False))
        return results
    
    # Test 2: Import memory store
    print("\n[Test 2] Importing memory store...")
    try:
        from ares_mind.memory_store import memory_store
        print("✅ Memory store imported")
        results.append(("Import memory store", True))
    except Exception as e:
        print(f"❌ Failed: {e}")
        results.append(("Import memory store", False))
        return results
    
    # Test 3: Import prompt assembler
    print("\n[Test 3] Importing prompt assembler...")
    try:
        from ares_core.prompt_assembler import prompt_assembler
        print("✅ Prompt assembler imported")
        results.append(("Import prompt assembler", True))
    except Exception as e:
        print(f"❌ Failed: {e}")
        results.append(("Import prompt assembler", False))
        return results
    
    # Test 4: Get memory layers
    print("\n[Test 4] Testing memory store...")
    try:
        memory = memory_store.get_all_memory_layers('test_user')
        assert "identity" in memory
        assert "factual" in memory
        assert "working" in memory
        assert "episodic" in memory
        print(f"✅ Memory store has all 4 layers: {list(memory.keys())}")
        results.append(("Memory store layers", True))
    except Exception as e:
        print(f"❌ Failed: {e}")
        results.append(("Memory store layers", False))
    
    # Test 5: Assemble prompt
    print("\n[Test 5] Testing prompt assembler...")
    try:
        messages = prompt_assembler.assemble(
            user_id='test_user',
            current_message='Hello from Docker!',
            session_id=None
        )
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        print(f"✅ Prompt assembled: {len(messages)} messages, {sum(len(m['content']) for m in messages)} chars")
        results.append(("Prompt assembly", True))
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Prompt assembly", False))
    
    # Test 6: Check model routing
    print("\n[Test 6] Testing model router...")
    try:
        router = orchestrator.router
        print(f"   Local available: {router.local_available}")
        print(f"   Cloud available: {router.cloud_available}")
        
        if not router.local_available and not router.cloud_available:
            print("⚠️  No LLM provider configured (this is okay for testing)")
        
        # Try to get a routing decision
        provider, config = router.route(
            task_context={"message": "test"},
            prefer_local=False
        )
        print(f"✅ Router works (would select: {provider})")
        results.append(("Model routing", True))
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Model routing", False))
    
    # Test 7: Check debug views
    print("\n[Test 7] Testing debug views import...")
    try:
        from api import debug_views
        print("✅ Debug views imported")
        results.append(("Debug views", True))
    except Exception as e:
        print(f"❌ Failed: {e}")
        results.append(("Debug views", False))
    
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
        print("\n🎉 All tests passed in Docker!")
        print("\nThe orchestrator refactoring is working correctly in Docker.")
        return 0
    else:
        print("\n⚠️  Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(test_orchestrator_in_docker())

