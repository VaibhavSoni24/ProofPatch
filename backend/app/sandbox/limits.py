"""Sandbox safety limits and configuration constraints."""

from app.core.config import get_settings

settings = get_settings()

# Execution constraints
DEFAULT_COMMAND_TIMEOUT_SECONDS = settings.sandbox_timeout_seconds
MAX_OUTPUT_CHARACTERS = 30000
MAX_PATCH_BYTES = settings.max_patch_bytes
MAX_FILES_IN_REPOSITORY = settings.max_repository_files
MAX_FILE_SIZE_BYTES = settings.max_file_size_bytes
MAX_REPOSITORY_TRANSFER_BYTES = settings.max_repository_transfer_bytes

# Test execution command allowlist
ALLOWED_TEST_BINARIES = ("pytest", "python -m pytest")

# Dangerous command tokens strictly rejected in test arguments
FORBIDDEN_ARGUMENT_PATTERNS = [
    ";",
    "&&",
    "||",
    "|",
    "`",
    "$",
    ">",
    "<",
    "\n",
    "\r",
    "--capture=no",
    "--pdb",
    "--trace",
    "eval(",
    "exec(",
    "__import__",
    "/bin/sh",
    "/bin/bash",
    "cmd.exe",
    "powershell",
]


def sanitize_test_args(args: list[str]) -> list[str]:
    """Validate and sanitize arguments supplied to test runner."""
    cleaned = []
    for arg in args:
        for forbidden in FORBIDDEN_ARGUMENT_PATTERNS:
            if forbidden in arg:
                raise ValueError(f"Forbidden token '{forbidden}' in test argument: {arg}")
        cleaned.append(arg.strip())
    return cleaned
