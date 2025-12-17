"""Code reading and search API endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pathlib import Path

from caption_ai.code_reader import code_reader

router = APIRouter()


@router.get("/api/code/files")
async def list_code_files(directory: str | None = None, max_depth: int = 5) -> JSONResponse:
    """List code files in the project."""
    try:
        if directory:
            dir_path = Path(directory)
        else:
            dir_path = None
        
        files = code_reader.list_code_files(directory=dir_path, max_depth=max_depth)
        return JSONResponse({"files": files, "count": len(files)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/code/read")
async def read_code_file(file_path: str, max_lines: int = 1000) -> JSONResponse:
    """Read a code file."""
    try:
        file_data = code_reader.read_file(file_path, max_lines=max_lines)
        if file_data:
            return JSONResponse(file_data)
        else:
            return JSONResponse({"error": "File not found or cannot be read"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/code/search")
async def search_code(query: str, max_results: int = 10) -> JSONResponse:
    """Search for text in code files."""
    try:
        results = code_reader.search_in_files(query, max_results=max_results)
        return JSONResponse({"results": results, "count": len(results)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

