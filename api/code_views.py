"""
Code Indexing and Revision System for ARES

Provides:
1. Code indexing - scan and index all code files
2. Code context - provide code context to AI in chat
3. Code revision - allow AI to revise its own code
4. Code memory - track code changes and extract memories
"""

import json
import os
import hashlib
import difflib
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import CodeSnapshot, CodeChange, CodeMemory
from .utils import _get_setting
from .auth import require_auth


# File extensions to index
CODE_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.css', '.html', '.md', 
    '.json', '.xml', '.yaml', '.yml', '.toml', '.sh', '.bash',
    '.sql', '.go', '.rs', '.java', '.cpp', '.c', '.h', '.hpp',
    '.vue', '.svelte', '.php', '.rb', '.swift', '.kt', '.dart'
}

# Directories to ignore
IGNORE_DIRS = {
    'node_modules', '__pycache__', '.git', '.venv', 'venv', 'env',
    'dist', 'build', '.next', '.nuxt', 'target', 'bin', 'obj',
    'staticfiles', 'migrations', '.pytest_cache', 'chromadb',
    'data', 'logs', '.idea', '.vscode'
}

# Files to ignore
IGNORE_FILES = {
    '.gitignore', '.env', '.env.local', 'package-lock.json',
    'yarn.lock', 'poetry.lock', 'uv.lock'
}

# File patterns to ignore (for security - sensitive files)
IGNORE_PATTERNS = [
    r'\.env$',           # .env
    r'\.env\..*',        # .env.local, .env.production, etc.
    r'.*\.env$',         # any-file.env
    r'.*\.env\..*',      # any-file.env.local
    r'\.envrc$',         # direnv config
    r'\.secrets$',       # secrets files
    r'.*secret.*',       # any file with "secret" in name
    r'.*key.*',          # any file with "key" in name (case insensitive)
    r'.*password.*',     # any file with "password" in name
    r'.*credential.*',   # any file with "credential" in name
    r'.*token.*',        # any file with "token" in name
]


def get_code_context_summary() -> str:
    """
    Get a summary of code context for injection into system prompts.
    Returns a string summary.
    """
    try:
        # Get recent code changes
        recent_changes = CodeChange.objects.order_by('-created_at')[:20]
        
        # Get code statistics
        total_files = CodeSnapshot.objects.values('file_path').distinct().count()
        total_snapshots = CodeSnapshot.objects.count()
        
        # Get files by language
        languages = {}
        for snapshot in CodeSnapshot.objects.values('language', 'file_path').distinct():
            lang = snapshot['language']
            if lang not in languages:
                languages[lang] = 0
            languages[lang] += 1
        
        # Get recent AI revisions
        ai_revisions = CodeChange.objects.filter(
            source=CodeChange.SOURCE_AI,
            change_type=CodeChange.CHANGE_TYPE_AI_REVISION
        ).order_by('-created_at')[:10]
        
        summary = f"""Codebase Context:
- Total files indexed: {total_files}
- Languages: {', '.join(languages.keys()) if languages else 'None'}
- Recent changes: {len(recent_changes)} files modified
- Recent AI revisions: {len(ai_revisions)} files revised by AI

You have access to the full codebase. You can:
1. Ask about specific files or code patterns
2. Request code revisions (use /api/v1/code/revise endpoint)
3. Search for code using /api/v1/code/search
4. View file contents using /api/v1/code/file

When revising code, provide:
- file_path: relative path from workspace root
- new_content: complete new file content
- reason: why you're making this change
- session_id: current session ID
- model: model name you're using"""
        
        return summary
    except Exception as e:
        return f"Codebase context unavailable: {str(e)}"


def _get_workspace_root() -> Path:
    """Get the workspace root directory."""
    # Try to get from settings, fallback to current directory
    workspace = getattr(settings, 'WORKSPACE_ROOT', None)
    if workspace:
        return Path(workspace)
    
    # Default to parent of 'api' directory
    current_file = Path(__file__)
    api_dir = current_file.parent
    return api_dir.parent


def _should_index_file(file_path: Path) -> bool:
    """
    Check if a file should be indexed.
    
    SECURITY: Explicitly excludes all .env files and sensitive files
    to prevent AI from accessing secrets, API keys, passwords, etc.
    """
    # Check extension
    if file_path.suffix not in CODE_EXTENSIONS:
        return False
    
    # Check if in ignored directory
    for part in file_path.parts:
        if part in IGNORE_DIRS:
            return False
    
    # Check if file is in ignore list
    if file_path.name in IGNORE_FILES:
        return False
    
    # SECURITY: Check against ignore patterns (prevents .env and sensitive files)
    file_name = file_path.name.lower()
    file_path_str = str(file_path).lower()
    
    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, file_name) or re.search(pattern, file_path_str):
            return False
    
    return True


def _detect_language(file_path: Path) -> str:
    """Detect programming language from file extension."""
    ext = file_path.suffix.lower()
    lang_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.css': 'css',
        '.html': 'html',
        '.md': 'markdown',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.sh': 'bash',
        '.bash': 'bash',
        '.sql': 'sql',
        '.go': 'go',
        '.rs': 'rust',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.vue': 'vue',
        '.svelte': 'svelte',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.dart': 'dart',
    }
    return lang_map.get(ext, 'text')


def _calculate_hash(content: str) -> str:
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def _calculate_diff_stats(old_content: str, new_content: str) -> Tuple[int, int, int]:
    """Calculate diff statistics."""
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
    
    added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    changed = min(added, removed)  # Lines that were changed (both added and removed)
    
    return added, removed, changed


@csrf_exempt
@require_http_methods(["POST"])
def index_codebase(request):
    """
    Index all code files in the workspace.
    
    Scans the workspace and creates/updates code snapshots.
    """
    try:
        workspace_root = _get_workspace_root()
        
        if not workspace_root.exists():
            return JsonResponse({
                'error': f'Workspace root not found: {workspace_root}'
            }, status=404)
        
        indexed_count = 0
        updated_count = 0
        created_count = 0
        errors = []
        
        # Walk through all files
        for file_path in workspace_root.rglob('*'):
            if not file_path.is_file():
                continue
            
            if not _should_index_file(file_path):
                continue
            
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Calculate hash
                content_hash = _calculate_hash(content)
                
                # Get relative path
                rel_path = str(file_path.relative_to(workspace_root))
                
                # Check if snapshot exists with this hash
                existing = CodeSnapshot.objects.filter(
                    file_path=rel_path,
                    sha256_hash=content_hash
                ).first()
                
                if existing:
                    # Already indexed with this content
                    continue
                
                # Check for previous snapshot
                previous = CodeSnapshot.objects.filter(
                    file_path=rel_path
                ).order_by('-indexed_at').first()
                
                # Create new snapshot
                snapshot = CodeSnapshot.objects.create(
                    file_path=rel_path,
                    file_name=file_path.name,
                    file_extension=file_path.suffix,
                    content=content,
                    line_count=len(content.splitlines()),
                    language=_detect_language(file_path),
                    sha256_hash=content_hash,
                    last_modified=timezone.datetime.fromtimestamp(
                        file_path.stat().st_mtime,
                        tz=timezone.get_current_timezone()
                    ) if file_path.exists() else None,
                )
                
                # Create change record if previous snapshot exists
                if previous:
                    added, removed, changed = _calculate_diff_stats(previous.content, content)
                    
                    CodeChange.objects.create(
                        file_path=rel_path,
                        change_type=CodeChange.CHANGE_TYPE_MODIFIED,
                        source=CodeChange.SOURCE_SYSTEM,
                        old_snapshot=previous,
                        new_snapshot=snapshot,
                        lines_added=added,
                        lines_removed=removed,
                        lines_changed=changed,
                    )
                    updated_count += 1
                else:
                    CodeChange.objects.create(
                        file_path=rel_path,
                        change_type=CodeChange.CHANGE_TYPE_CREATED,
                        source=CodeChange.SOURCE_SYSTEM,
                        new_snapshot=snapshot,
                    )
                    created_count += 1
                
                indexed_count += 1
                
            except Exception as e:
                errors.append(f"Error indexing {file_path}: {str(e)}")
        
        # Optionally extract code memories after indexing
        # Only if significant number of files were indexed
        if indexed_count > 10:
            try:
                mem_count, mem_errors = extract_code_memories()
                if mem_errors:
                    errors.extend(mem_errors[:5])  # Add memory extraction errors
            except Exception as e:
                # Don't fail indexing if memory extraction fails
                print(f"[WARNING] Code memory extraction failed: {e}")
        
        return JsonResponse({
            'success': True,
            'indexed': indexed_count,
            'created': created_count,
            'updated': updated_count,
            'errors': errors[:10],  # Limit errors
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def list_code_files(request):
    """
    List all code files in the workspace.
    
    Returns a list of all code files (excluding .env and sensitive files).
    """
    try:
        workspace_root = _get_workspace_root()
        
        if not workspace_root.exists():
            return JsonResponse({
                'error': f'Workspace root not found: {workspace_root}'
            }, status=404)
        
        files = []
        
        # Walk through all files
        for file_path in workspace_root.rglob('*'):
            if not file_path.is_file():
                continue
            
            if not _should_index_file(file_path):
                continue
            
            # Get relative path
            rel_path = str(file_path.relative_to(workspace_root))
            
            files.append({
                'path': rel_path,
                'name': file_path.name,
                'extension': file_path.suffix,
                'language': _detect_language(file_path),
            })
        
        # Sort files by path
        files.sort(key=lambda x: x['path'])
        
        return JsonResponse({
            'files': files,
            'count': len(files),
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_code_context(request):
    """
    Get code context for AI chat.
    
    Returns a summary of the codebase structure and recent changes.
    """
    try:
        # Get recent code changes
        recent_changes = CodeChange.objects.order_by('-created_at')[:20]
        
        # Get code statistics
        total_files = CodeSnapshot.objects.values('file_path').distinct().count()
        total_snapshots = CodeSnapshot.objects.count()
        
        # Get files by language
        languages = {}
        for snapshot in CodeSnapshot.objects.values('language', 'file_path').distinct():
            lang = snapshot['language']
            if lang not in languages:
                languages[lang] = 0
            languages[lang] += 1
        
        # Get recent AI revisions
        ai_revisions = CodeChange.objects.filter(
            source=CodeChange.SOURCE_AI,
            change_type=CodeChange.CHANGE_TYPE_AI_REVISION
        ).order_by('-created_at')[:10]
        
        # Build context summary
        context = {
            'total_files': total_files,
            'total_snapshots': total_snapshots,
            'languages': languages,
            'recent_changes': [
                {
                    'file_path': change.file_path,
                    'change_type': change.change_type,
                    'source': change.source,
                    'created_at': change.created_at.isoformat(),
                    'diff_summary': change.diff_summary,
                }
                for change in recent_changes
            ],
            'recent_ai_revisions': [
                {
                    'file_path': rev.file_path,
                    'reason': rev.change_reason,
                    'model': rev.model_used,
                    'created_at': rev.created_at.isoformat(),
                }
                for rev in ai_revisions
            ],
        }
        
        return JsonResponse(context)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def search_code(request):
    """
    Search code files by content or path.
    
    SECURITY: Excludes .env and sensitive files from search results.
    """
    try:
        query = request.GET.get('query', '').strip()
        if not query:
            return JsonResponse({'error': 'Query is required'}, status=400)
        
        language = request.GET.get('language', '')
        limit = int(request.GET.get('limit', 50))
        
        # Get latest snapshot for each file
        snapshots = CodeSnapshot.objects.all()
        
        if language:
            snapshots = snapshots.filter(language=language)
        
        # Search in file path or content
        results = []
        query_lower = query.lower()
        
        for snapshot in snapshots.order_by('-indexed_at'):
            # SECURITY: Skip sensitive files
            if _is_sensitive_file(snapshot.file_path):
                continue
            
            # Check if query matches path or content
            if query_lower in snapshot.file_path.lower() or query_lower in snapshot.content.lower():
                # Get line numbers where query appears
                lines = snapshot.content.splitlines()
                matching_lines = [
                    i + 1 for i, line in enumerate(lines)
                    if query_lower in line.lower()
                ][:5]  # Limit to first 5 matches
                
                results.append({
                    'file_path': snapshot.file_path,
                    'file_name': snapshot.file_name,
                    'language': snapshot.language,
                    'line_count': snapshot.line_count,
                    'matching_lines': matching_lines,
                    'indexed_at': snapshot.indexed_at.isoformat(),
                })
                
                if len(results) >= limit:
                    break
        
        return JsonResponse({
            'results': results,
            'count': len(results),
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def _is_sensitive_file(file_path: str) -> bool:
    """
    Check if a file path is sensitive and should not be accessible.
    
    SECURITY: Prevents access to .env files, secrets, credentials, etc.
    """
    file_path_lower = file_path.lower()
    
    # Check against ignore patterns
    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, file_path_lower):
            return True
    
    # Check if filename is in ignore list
    file_name = Path(file_path).name
    if file_name in IGNORE_FILES:
        return True
    
    return False


@require_http_methods(["GET"])
def get_file_content(request):
    """
    Get content of a specific file (from snapshot if available, otherwise from filesystem).
    
    SECURITY: Blocks access to .env and other sensitive files.
    """
    try:
        file_path = request.GET.get('file_path', '').strip()
        if not file_path:
            return JsonResponse({'error': 'file_path is required'}, status=400)
        
        # SECURITY: Block access to sensitive files
        if _is_sensitive_file(file_path):
            return JsonResponse({
                'error': 'Access denied: sensitive files are not accessible'
            }, status=403)
        
        # Try to get from snapshot first
        snapshot = CodeSnapshot.objects.filter(
            file_path=file_path
        ).order_by('-indexed_at').first()
        
        if snapshot:
            return JsonResponse({
                'file_path': snapshot.file_path,
                'file_name': snapshot.file_name,
                'language': snapshot.language,
                'content': snapshot.content,
                'line_count': snapshot.line_count,
                'indexed_at': snapshot.indexed_at.isoformat(),
            })
        
        # Fallback to reading from filesystem
        workspace_root = _get_workspace_root()
        full_path = workspace_root / file_path
        
        if not full_path.exists():
            return JsonResponse({
                'error': f'File not found: {file_path}'
            }, status=404)
        
        # SECURITY: Double-check file should be accessible
        if not _should_index_file(full_path):
            return JsonResponse({
                'error': 'Access denied: sensitive files are not accessible'
            }, status=403)
        
        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except UnicodeDecodeError:
            return JsonResponse({
                'error': f'File is not a text file: {file_path}'
            }, status=400)
        
        language = _detect_language(full_path)
        line_count = len(content.splitlines())
        
        return JsonResponse({
            'file_path': file_path,
            'file_name': full_path.name,
            'language': language,
            'content': content,
            'line_count': line_count,
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_auth  # SECURITY: Requires authentication and admin role
@require_http_methods(["POST"])
def revise_code(request):
    """
    Allow AI to revise code.

    SECURITY: Requires admin authentication. Blocks revision of .env and sensitive files.

    Accepts:
    - file_path: Path to file to revise
    - new_content: New content for the file
    - reason: Why the code was revised
    - session_id: Chat session that triggered the revision
    - model: Model used for revision
    """
    try:
        data = json.loads(request.body)
        file_path = data.get('file_path', '').strip()
        new_content = data.get('new_content', '')
        reason = data.get('reason', '')
        session_id = data.get('session_id', '')
        model = data.get('model', '')
        
        if not file_path:
            return JsonResponse({
                'error': 'file_path is required'
            }, status=400)
        
        if not new_content:
            return JsonResponse({
                'error': 'new_content is required'
            }, status=400)
        
        # SECURITY: Block revision of sensitive files
        if _is_sensitive_file(file_path):
            return JsonResponse({
                'error': 'Access denied: sensitive files cannot be revised'
            }, status=403)
        
        workspace_root = _get_workspace_root()
        full_path = workspace_root / file_path
        
        if not full_path.exists():
            return JsonResponse({
                'error': f'File not found: {file_path}'
            }, status=404)
        
        # Get current content
        with open(full_path, 'r', encoding='utf-8') as f:
            old_content = f.read()
        
        # Get previous snapshot
        previous_snapshot = CodeSnapshot.objects.filter(
            file_path=file_path
        ).order_by('-indexed_at').first()
        
        # Calculate diff stats
        added, removed, changed = _calculate_diff_stats(old_content, new_content)
        
        # Create new snapshot
        content_hash = _calculate_hash(new_content)
        new_snapshot = CodeSnapshot.objects.create(
            file_path=file_path,
            file_name=Path(file_path).name,
            file_extension=Path(file_path).suffix,
            content=new_content,
            line_count=len(new_content.splitlines()),
            language=_detect_language(Path(file_path)),
            sha256_hash=content_hash,
            last_modified=timezone.now(),
        )
        
        # Generate diff summary using AI if available
        diff_summary = ""
        try:
            from ares_core.llm_router import llm_router
            if llm_router.openrouter_available:
                try:
                    diff_prompt = f"""Summarize the changes made to this code file in 1-2 sentences.

Old content:
{old_content[:2000]}

New content:
{new_content[:2000]}

Reason: {reason}

Provide a concise summary of what changed."""
                    
                    response = llm_router.chat(
                        messages=[{"role": "user", "content": diff_prompt}],
                        temperature=0.3,
                        max_tokens=200,
                    )
                    diff_summary = response.content
                except Exception as e:
                    print(f"Failed to generate diff summary: {e}")
        except ImportError:
            pass
        
        # Create change record
        code_change = CodeChange.objects.create(
            file_path=file_path,
            change_type=CodeChange.CHANGE_TYPE_AI_REVISION,
            source=CodeChange.SOURCE_AI,
            old_snapshot=previous_snapshot,
            new_snapshot=new_snapshot,
            diff_summary=diff_summary,
            change_reason=reason,
            model_used=model,
            session_id=session_id,
            lines_added=added,
            lines_removed=removed,
            lines_changed=changed,
        )
        
        # Write new content to file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return JsonResponse({
            'success': True,
            'file_path': file_path,
            'change_id': code_change.id,
            'lines_added': added,
            'lines_removed': removed,
            'lines_changed': changed,
            'diff_summary': diff_summary,
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def extract_code_memories() -> Tuple[int, List[str]]:
    """
    Extract memories about the codebase structure and patterns.
    
    Uses AI to analyze the codebase and extract insights that can be
    used to provide better context in future conversations.
    
    Returns:
        (count, errors) - number of memories extracted and list of errors
    """
    try:
        from ares_core.llm_router import llm_router
        
        if not llm_router.openrouter_available:
            return 0, ["OpenRouter not available for code memory extraction"]
        
        # Get code statistics
        total_files = CodeSnapshot.objects.values('file_path').distinct().count()
        languages = {}
        for snapshot in CodeSnapshot.objects.values('language', 'file_path').distinct():
            lang = snapshot['language']
            if lang not in languages:
                languages[lang] = 0
            languages[lang] += 1
        
        # Get recent changes
        recent_changes = CodeChange.objects.order_by('-created_at')[:50]
        change_summary = "\n".join([
            f"- {c.file_path}: {c.change_type} ({c.source})"
            for c in recent_changes[:20]
        ])
        
        # Get file structure (sample of files)
        sample_files = CodeSnapshot.objects.values('file_path', 'language').distinct()[:100]
        file_structure = "\n".join([
            f"- {f['file_path']} ({f['language']})"
            for f in sample_files
        ])
        
        # Create extraction prompt
        extraction_prompt = f"""Analyze this codebase and extract important memories about its structure, patterns, and architecture.

Codebase Statistics:
- Total files: {total_files}
- Languages: {', '.join(languages.keys()) if languages else 'None'}

Recent Changes:
{change_summary}

Sample File Structure:
{file_structure}

Extract memories in these categories:
1. **Architecture**: Overall system architecture, design patterns, major components
2. **Patterns**: Common coding patterns, conventions, best practices used
3. **Dependencies**: Key libraries, frameworks, external dependencies
4. **Features**: Major features, capabilities, functionality
5. **Structure**: Directory structure, organization, file naming conventions
6. **Improvements**: Areas for improvement, technical debt, optimization opportunities

Return your analysis as a JSON object with this structure:
{{
    "memories": [
        {{
            "category": "architecture|patterns|dependencies|features|structure|improvements",
            "memory_key": "unique_key_for_this_memory",
            "memory_value": "detailed description of the memory",
            "related_files": ["file1.py", "file2.js"],
            "importance": 1-10,
            "confidence": 0.0-1.0
        }}
    ]
}}

Be specific and actionable. Only extract memories with importance >= 5."""
        
        # Call AI for extraction
        response = llm_router.chat(
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.3,
            max_tokens=4000,
        )
        
        # Parse response
        try:
            # Try to extract JSON from response
            text = response.content.strip()
            if text.startswith("```"):
                # Remove markdown code blocks
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
            
            data = json.loads(text)
            memories_data = data.get("memories", [])
        except json.JSONDecodeError as e:
            return 0, [f"Failed to parse AI response: {e}"]
        
        # Store memories
        extracted_count = 0
        errors = []
        
        with transaction.atomic():
            for mem_data in memories_data:
                try:
                    category = mem_data.get("category", "general")
                    memory_key = mem_data.get("memory_key", "")
                    memory_value = mem_data.get("memory_value", "")
                    related_files = mem_data.get("related_files", [])
                    importance = mem_data.get("importance", 5)
                    confidence = mem_data.get("confidence", 0.5)
                    
                    if not memory_key or not memory_value:
                        continue
                    
                    # Update or create memory
                    CodeMemory.objects.update_or_create(
                        category=category,
                        memory_key=memory_key,
                        defaults={
                            "memory_value": memory_value,
                            "related_files": related_files,
                            "importance": importance,
                            "confidence": confidence,
                            "last_verified": timezone.now(),
                        }
                    )
                    extracted_count += 1
                except Exception as e:
                    errors.append(f"Failed to store memory: {e}")
        
        return extracted_count, errors
    
    except Exception as e:
        return 0, [f"Unexpected error: {str(e)}"]


@csrf_exempt
@require_http_methods(["POST"])
def extract_code_memories_endpoint(request):
    """
    Trigger code memory extraction.
    """
    try:
        count, errors = extract_code_memories()
        
        return JsonResponse({
            'success': True,
            'extracted': count,
            'errors': errors,
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_code_memories(request):
    """
    Get extracted code memories.
    """
    try:
        category = request.GET.get('category', '')
        limit = int(request.GET.get('limit', 50))
        
        memories = CodeMemory.objects.all()
        
        if category:
            memories = memories.filter(category=category)
        
        memories = memories.order_by('-importance', '-extracted_at')[:limit]
        
        return JsonResponse({
            'memories': [
                {
                    'id': mem.id,
                    'category': mem.category,
                    'memory_key': mem.memory_key,
                    'memory_value': mem.memory_value,
                    'related_files': mem.related_files,
                    'importance': mem.importance,
                    'confidence': mem.confidence,
                    'extracted_at': mem.extracted_at.isoformat(),
                }
                for mem in memories
            ],
            'count': len(memories),
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

