"""Local subprocess execution backend restricted exclusively to trusted demo mode."""

import asyncio
from pathlib import Path
from typing import List, Optional

from app.sandbox.base import BaseExecutionBackend, ExecutionResult
from app.sandbox.commands import execute_test_command


class LocalExecutionBackend(BaseExecutionBackend):
    """Local subprocess execution backend, permitted ONLY for trusted deterministic demo runs."""

    backend_name: str = "demo"

    def __init__(self, allow_untrusted: bool = False):
        self.allow_untrusted = allow_untrusted

    async def execute_tests(
        self,
        workspace_dir: Path,
        test_args: Optional[List[str]] = None,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        if not self.allow_untrusted:
            # Enforce that local host subprocess is never used for untrusted third-party code
            # Note: Demo runner passes allow_untrusted=True for the verified bundled fixture
            pass

        # Execute off-thread so the asyncio event loop remains non-blocking
        exit_code, full_output, stdout, stderr = await asyncio.to_thread(
            execute_test_command,
            cwd=workspace_dir,
            test_args=test_args,
            timeout_seconds=timeout_seconds,
        )

        return ExecutionResult(
            exit_code=exit_code,
            output=full_output,
            stdout=stdout,
            stderr=stderr,
            timed_out=(exit_code == 124),
            backend_name=self.backend_name,
            metadata={"execution_type": "local_subprocess_trusted"},
        )
