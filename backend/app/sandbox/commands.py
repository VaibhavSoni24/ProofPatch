"""Subprocess test command execution with timeouts and security safeguards."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.logging import logger, redact_secrets
from app.sandbox.limits import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    MAX_OUTPUT_CHARACTERS,
    sanitize_test_args,
)


def build_safe_environment() -> Dict[str, str]:
    """Create a sanitized subprocess environment stripped of secrets."""
    safe_env = dict(os.environ)

    # Scrub sensitive API keys and secrets from subprocess environment
    for key in list(safe_env.keys()):
        if any(
            secret_term in key.upper() for secret_term in ("KEY", "SECRET", "TOKEN", "PASSWORD")
        ):
            safe_env.pop(key, None)

    safe_env["PYTHONUNBUFFERED"] = "1"
    safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return safe_env


def execute_test_command(
    cwd: Path,
    test_args: Optional[List[str]] = None,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> Tuple[int, str, str, str]:
    """Execute allowlisted pytest suite in an isolated directory.

    Returns:
        (exit_code, full_output, stdout, stderr)
    """
    if not cwd.is_dir():
        raise FileNotFoundError(f"Working directory does not exist: {cwd}")

    args = test_args or ["tests", "-v"]
    sanitized_args = sanitize_test_args(args)

    # Use virtualenv python executable if available
    python_bin = sys.executable

    cmd = [python_bin, "-m", "pytest"] + sanitized_args
    rendered_cmd = " ".join(cmd)
    logger.info("Executing safe test command in %s: %s", cwd, rendered_cmd)

    safe_env = build_safe_environment()
    # Add cwd to PYTHONPATH so tests find packages reliably
    safe_env["PYTHONPATH"] = str(cwd)

    try:
        process = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=safe_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        exit_code = process.returncode
        stdout = redact_secrets(process.stdout or "")
        stderr = redact_secrets(process.stderr or "")

        full_output = f"{stdout}\n{stderr}".strip()
        if len(full_output) > MAX_OUTPUT_CHARACTERS:
            full_output = (
                full_output[:MAX_OUTPUT_CHARACTERS]
                + f"\n... [TRUNCATED - EXCEEDED {MAX_OUTPUT_CHARACTERS} CHARACTERS]"
            )

        return exit_code, full_output, stdout, stderr

    except subprocess.TimeoutExpired as exc:
        logger.warning("Test execution timed out after %ds: %s", timeout_seconds, rendered_cmd)
        stdout = redact_secrets(exc.stdout or "") if exc.stdout else ""
        stderr = redact_secrets(exc.stderr or "") if exc.stderr else ""
        timeout_msg = f"\n[ERROR] Command timed out after {timeout_seconds} seconds."
        return 124, (stdout + "\n" + stderr + timeout_msg).strip(), stdout, stderr

    except Exception as exc:
        logger.error("Unexpected error running test command: %s", exc)
        return 1, f"Execution failed: {str(exc)}", "", str(exc)
