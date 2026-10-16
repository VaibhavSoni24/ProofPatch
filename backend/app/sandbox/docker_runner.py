"""Docker isolation sandbox for untrusted external repositories."""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.errors import DockerNotAvailableError
from app.core.logging import logger
from app.sandbox.limits import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    MAX_OUTPUT_CHARACTERS,
    sanitize_test_args,
)


def is_docker_available() -> bool:
    """Check if the Docker binary is on PATH and daemon is responding."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False
    try:
        res = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return res.returncode == 0
    except Exception:
        return False


def run_tests_in_docker(
    workspace_dir: Path,
    test_args: Optional[List[str]] = None,
    image: str = "python:3.11-slim",
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> Tuple[int, str]:
    """Execute tests inside an isolated, non-networked Docker container.

    Enforces:
    - --network none
    - --memory=512m
    - --cpus=1.0
    - --pids-limit=64
    - read/write volume strictly mounted to workspace
    """
    if not is_docker_available():
        raise DockerNotAvailableError()

    sanitized_args = sanitize_test_args(test_args or ["tests", "-v"])
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--memory",
        "512m",
        "--cpus",
        "1.0",
        "--pids-limit",
        "64",
        "-v",
        f"{workspace_dir.resolve()}:/workspace",
        "-w",
        "/workspace",
        image,
        "pytest",
    ] + sanitized_args

    logger.info("Executing tests inside Docker container: %s", " ".join(cmd))
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = f"{res.stdout}\n{res.stderr}".strip()
        if len(output) > MAX_OUTPUT_CHARACTERS:
            output = output[:MAX_OUTPUT_CHARACTERS] + "\n... [TRUNCATED]"
        return res.returncode, output
    except subprocess.TimeoutExpired:
        return 124, f"Container execution timed out after {timeout_seconds}s."
    except Exception as exc:
        return 1, f"Docker execution error: {str(exc)}"
