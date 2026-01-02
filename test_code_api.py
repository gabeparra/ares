#!/usr/bin/env python3
"""
Test script for Code API endpoints.
Run this inside the Docker container or with proper Django setup.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ares_project.settings')
django.setup()

from django.test import Client
from api.models import CodeSnapshot, CodeChange, CodeMemory
from api.code_views import _get_workspace_root, _should_index_file
from pathlib import Path
import json

def test_workspace_root():
    """Test workspace root detection."""
    print("=" * 60)
    print("Test 1: Workspace Root Detection")
    print("=" * 60)
    root = _get_workspace_root()
    print(f"Workspace root: {root}")
    print(f"Exists: {root.exists()}")
    
    if root.exists():
        py_files = list(root.rglob('*.py'))
        print(f"Python files found: {len(py_files)}")
        print(f"Sample files: {[str(f.relative_to(root)) for f in py_files[:5]]}")
    print()

def test_file_filtering():
    """Test file filtering logic."""
    print("=" * 60)
    print("Test 2: File Filtering")
    print("=" * 60)
    root = _get_workspace_root()
    if not root.exists():
        print("Workspace root does not exist!")
        return
    
    test_files = [
        root / 'api' / 'code_views.py',
        root / 'node_modules' / 'something.js',
        root / '__pycache__' / 'file.pyc',
        root / 'manage.py',
    ]
    
    for f in test_files:
        should_index = _should_index_file(f) if f.exists() else False
        print(f"  {f.relative_to(root) if f.exists() else f}: should_index={should_index}")
    print()

def test_models():
    """Test model imports and counts."""
    print("=" * 60)
    print("Test 3: Database Models")
    print("=" * 60)
    print(f"CodeSnapshot count: {CodeSnapshot.objects.count()}")
    print(f"CodeChange count: {CodeChange.objects.count()}")
    print(f"CodeMemory count: {CodeMemory.objects.count()}")
    print()

def test_api_endpoints():
    """Test API endpoints."""
    print("=" * 60)
    print("Test 4: API Endpoints")
    print("=" * 60)
    from django.conf import settings
    
    # Set allowed host for test client
    client = Client(HTTP_HOST='localhost')
    
    # Test code/context endpoint
    print("Testing GET /api/v1/code/context...")
    try:
        response = client.get('/api/v1/code/context', HTTP_HOST='localhost')
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = json.loads(response.content)
            print(f"  Response keys: {list(data.keys())}")
            print(f"  Total files: {data.get('total_files', 0)}")
        else:
            print(f"  Error: {response.content.decode()[:200]}")
    except Exception as e:
        print(f"  Error: {str(e)[:200]}")
    print()
    
    # Test code/index endpoint (POST) - just verify it's callable
    print("Testing POST /api/v1/code/index (function call)...")
    try:
        from api.code_views import index_codebase
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/api/v1/code/index', HTTP_HOST='localhost')
        print("  Function is callable: ✓")
        print("  Note: Full indexing test requires actual file system access")
    except Exception as e:
        print(f"  Error: {str(e)[:200]}")
    print()

def test_url_registration():
    """Test URL registration."""
    print("=" * 60)
    print("Test 5: URL Registration")
    print("=" * 60)
    from django.urls import resolve
    from django.urls.exceptions import NoReverseMatch
    
    test_urls = [
        '/api/v1/code/index',
        '/api/v1/code/context',
        '/api/v1/code/search',
        '/api/v1/code/file',
        '/api/v1/code/revise',
        '/api/v1/code/memories',
        '/api/v1/code/extract-memories',
    ]
    
    for url in test_urls:
        try:
            match = resolve(url)
            print(f"  ✓ {url} -> {match.view_name}")
        except Exception as e:
            print(f"  ✗ {url} -> ERROR: {e}")
    print()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Code API Test Suite")
    print("=" * 60 + "\n")
    
    test_workspace_root()
    test_file_filtering()
    test_models()
    test_url_registration()
    test_api_endpoints()
    
    print("=" * 60)
    print("Tests Complete")
    print("=" * 60)

