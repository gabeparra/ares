# Development helper script for Windows

param(
    [Parameter(Position=0)]
    [ValidateSet("run", "lint", "test", "format", "install")]
    [string]$Command = "run"
)

switch ($Command) {
    "run" {
        python -m caption_ai
    }
    "lint" {
        ruff check .
        ruff format --check .
    }
    "test" {
        pytest
    }
    "format" {
        ruff format .
    }
    "install" {
        uv sync
    }
    default {
        Write-Host "Unknown command: $Command"
        Write-Host "Available: run, lint, test, format, install"
    }
}

