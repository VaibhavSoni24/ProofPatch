"""Docker isolation execution backend for bounded local container execution."""

import asyncio
from pathlib import Path
from typing import List, Optional

from app.core.errors import DockerNotAvailableError
from app.sandbox.base import BaseExecutionBackend, ExecutionResult
from app.sandbox.docker_runner import is_docker_available, run_tests_in_docker


class DockerExecutionBackend(BaseExecutionBackend):
    """Local Docker sandbox backend for executing untrusted repository test suites."""

    backend_name: str = "docker"

    def __init__(self, image: str = "python:3.11-slim"):
        self.image = image

    async def execute_tests(
        self,
        workspace_dir: Path,
        test_args: Optional[List[str]] = None,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        if not is_docker_available():
            raise DockerNotAvailableError(
                "Docker daemon is not running or unavailable. Live repository execution requires Docker "
                "or a configured Token Factory sandbox to safely isolate third-party code."
            )

        # Offload Docker CLI execution to worker thread
        exit_code, output = await asyncio.to_thread(
            run_tests_in_docker,
            workspace_dir=workspace_dir,
            test_args=test_args,
            image=self.image,
            timeout_seconds=timeout_seconds,
        )

        return ExecutionResult(
            exit_code=exit_code,
            output=output,
            stdout=output,
            stderr="",
            timed_out=(exit_code == 124),
            backend_name=self.backend_name,
            metadata={"image": self.image, "isolation": "docker_network_none"},
        )
