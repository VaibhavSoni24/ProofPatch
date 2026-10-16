"""Git repository validation, acquisition, and isolation."""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from app.core.errors import SecurityViolationError
from app.core.logging import logger

RE_GITHUB_REPO = re.compile(r"^https://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)$")


def validate_repository_url(url: str) -> Tuple[str, str]:
    """Validate public GitHub repository URL and reject unsafe schemes/credentials.

    Returns:
        (owner, repo_name)
    Raises:
        SecurityViolationError if URL is invalid or unsafe.
    """
    if not url or not url.strip():
        raise SecurityViolationError("Repository URL is empty")

    cleaned = url.strip().rstrip("/")
    # Strip optional .git suffix for validation
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    parsed = urlparse(cleaned)
    if parsed.scheme != "https":
        raise SecurityViolationError(
            f"Unsupported URL scheme: {parsed.scheme}. Only HTTPS is permitted."
        )

    if parsed.username or parsed.password:
        raise SecurityViolationError(
            "Embedded credentials in repository URL are strictly prohibited."
        )

    if parsed.netloc.lower() != "github.com":
        raise SecurityViolationError(
            f"Unsupported repository host: '{parsed.netloc}'. ProofPatch currently supports public github.com repositories."
        )

    match = RE_GITHUB_REPO.match(cleaned)
    if not match:
        raise SecurityViolationError(
            f"Invalid GitHub repository URL pattern: '{url}'. Expected format: https://github.com/owner/repository"
        )

    owner, repo_name = match.groups()
    return owner, repo_name


def clone_public_repository(repo_url: str, target_dir: Path, timeout_seconds: int = 45) -> str:
    """Perform a shallow clone of a validated public GitHub repository.

    Returns:
        Checked-out commit hash string.
    """
    validate_repository_url(repo_url)

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    git_bin = shutil.which("git") or "git"
    cmd = [git_bin, "clone", "--depth", "1", repo_url, str(target_dir)]

    logger.info("Cloning public repository %s to %s", repo_url, target_dir.name)
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if res.returncode != 0:
            raise SecurityViolationError(f"Git clone failed: {res.stderr[:200]}")

        # Extract HEAD commit hash
        rev_cmd = [git_bin, "-C", str(target_dir), "rev-parse", "HEAD"]
        rev_res = subprocess.run(rev_cmd, capture_output=True, text=True, timeout=5)
        commit_hash = rev_res.stdout.strip() if rev_res.returncode == 0 else "unknown"

        return commit_hash

    except subprocess.TimeoutExpired:
        raise SecurityViolationError(f"Git clone timed out after {timeout_seconds} seconds.")
