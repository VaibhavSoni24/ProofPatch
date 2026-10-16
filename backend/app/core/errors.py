"""Custom application error hierarchy."""


class ProofPatchError(Exception):
    """Base exception for all ProofPatch errors."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ConfigurationError(ProofPatchError):
    """Raised when application or provider configuration is missing or invalid."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class RunNotFoundError(ProofPatchError):
    """Raised when a requested run ID does not exist."""

    def __init__(self, run_id: str):
        super().__init__(f"Run '{run_id}' not found", status_code=404)


class InvalidStateTransitionError(ProofPatchError):
    """Raised when an illegal run state transition is attempted."""

    def __init__(self, current_state: str, attempted_state: str):
        super().__init__(
            f"Cannot transition run from '{current_state}' to '{attempted_state}'",
            status_code=409,
        )


class SecurityViolationError(ProofPatchError):
    """Raised when a patch or command violates execution security policies."""

    def __init__(self, message: str):
        super().__init__(f"Security violation: {message}", status_code=403)


class PatchApplicationError(ProofPatchError):
    """Raised when applying a unified diff fails."""

    def __init__(self, message: str):
        super().__init__(f"Patch application failed: {message}", status_code=422)


class ProviderError(ProofPatchError):
    """Raised when an external inference or search provider fails."""

    def __init__(self, provider: str, message: str, status_code: int = 502):
        super().__init__(f"Provider '{provider}' error: {message}", status_code=status_code)


class ExecutionTimeoutError(ProofPatchError):
    """Raised when a sandboxed command exceeds its time limit."""

    def __init__(self, command: str, timeout: int):
        super().__init__(
            f"Command '{command}' timed out after {timeout} seconds",
            status_code=504,
        )


class DockerNotAvailableError(ProofPatchError):
    """Raised when Docker sandbox is required but daemon is unreachable."""

    def __init__(self):
        super().__init__(
            "Docker is required for live external repository execution but the Docker daemon is unreachable.",
            status_code=503,
        )
