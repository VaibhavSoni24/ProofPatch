"""Bounded repository structure inspection and context collection."""

from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel

from app.sandbox.limits import MAX_FILES_IN_REPOSITORY

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
}


class RepositoryInspection(BaseModel):
    """Summarized file tree and test configuration."""

    total_files: int
    source_files: List[str]
    test_files: List[str]
    manifest_files: List[str]
    context_files_content: Dict[str, str] = {}


def inspect_repository(
    repo_dir: Path,
    max_files: int = MAX_FILES_IN_REPOSITORY,
    max_context_chars: int = 40000,
) -> RepositoryInspection:
    """Inspect repository files safely within bounds."""
    source_files: List[str] = []
    test_files: List[str] = []
    manifest_files: List[str] = []
    context_contents: Dict[str, str] = {}

    total_chars = 0

    for file_path in repo_dir.rglob("*"):
        if not file_path.is_file():
            continue

        # Skip ignored directories
        parts = file_path.parts
        if any(ignored in parts for ignored in IGNORED_DIRECTORIES):
            continue

        rel_path = str(file_path.relative_to(repo_dir)).replace("\\", "/")

        if file_path.name in ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile"):
            manifest_files.append(rel_path)
        elif "test" in file_path.name.lower() and file_path.suffix == ".py":
            test_files.append(rel_path)
        elif file_path.suffix == ".py":
            source_files.append(rel_path)

        # Collect bounded context snippet for key files
        if len(context_contents) < 15 and total_chars < max_context_chars:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                if len(content) < 10000:
                    context_contents[rel_path] = content
                    total_chars += len(content)
            except Exception:
                pass

        if len(source_files) + len(test_files) >= max_files:
            break

    total_count = len(source_files) + len(test_files) + len(manifest_files)

    return RepositoryInspection(
        total_files=total_count,
        source_files=source_files,
        test_files=test_files,
        manifest_files=manifest_files,
        context_files_content=context_contents,
    )
