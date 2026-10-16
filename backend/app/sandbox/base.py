"""Abstract execution backend interface for isolated test and sandbox execution."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ExecutionResult(BaseModel):
    """Normalized output from sandbox test command execution."""

    exit_code: Optional[int] = None
    output: str
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    backend_name: str
    metadata: Dict[str, Any] = {}


class BaseExecutionBackend(ABC):
    """Base interface for all test execution backends."""

    backend_name: str = "base"

    @abstractmethod
    async def execute_tests(
        self,
        workspace_dir: Path,
        test_args: Optional[List[str]] = None,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        """Execute test suite in isolated environment and return execution results."""
        raise NotImplementedError

    async def transfer_workspace(self, workspace_dir: Path) -> None:
        """Transfer repository files into the isolated sandbox environment."""
        pass

    async def apply_patch(self, patch_diff: str, workspace_dir: Path) -> List[str]:
        """Apply patch inside the sandbox environment and return modified files."""
        from app.agents.patch_parser import apply_patch_to_workspace

        return apply_patch_to_workspace(workspace_dir, patch_diff)

    async def cleanup(self) -> None:
        """Release any remote or local resources associated with this session."""
        pass
