"""Security controls for repository traversal, path containment, and sensitive file exclusion.

Protects the host environment against symlink directory escapes, unauthorized reads
outside workspace roots, and accidental exfiltration of secrets, keys, or credentials.
"""

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

from app.core.errors import SecurityViolationError
from app.core.logging import RE_SECRETS, logger

# Directories to always skip during repository inspection and transfer
IGNORED_DIRECTORIES: Set[str] = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".aws",
    ".ssh",
    ".config",
}

# Explicitly allowed non-secret configuration templates
ALLOWED_CONFIG_TEMPLATES: Set[str] = {
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
    ".env.test",
    "example.env",
}

# Strict regex patterns for sensitive files that must NEVER be read or transferred
SENSITIVE_FILENAME_PATTERNS: List[re.Pattern] = [
    re.compile(r"^\.env(?:\..+)?$", re.IGNORECASE),
    re.compile(r"^\.netrc$", re.IGNORECASE),
    re.compile(r"^\.git-credentials$", re.IGNORECASE),
    re.compile(r"^id_(?:rsa|dsa|ecdsa|ed25519)(?:\..+)?$", re.IGNORECASE),
    re.compile(r"^authorized_keys$", re.IGNORECASE),
    re.compile(r"^known_hosts$", re.IGNORECASE),
    re.compile(r"^\.npmrc$", re.IGNORECASE),
    re.compile(r"^\.pypirc$", re.IGNORECASE),
    re.compile(r"^.*service_account.*\.json$", re.IGNORECASE),
    re.compile(r"^credentials\.json$", re.IGNORECASE),
    re.compile(r"^client_secret.*\.json$", re.IGNORECASE),
]

# Sensitive certificate and private key extensions
SENSITIVE_EXTENSIONS: Set[str] = {
    ".pem",
    ".key",
    ".pkcs12",
    ".pfx",
    ".p12",
    ".keystore",
    ".jks",
}


@dataclass(frozen=True)
class SafeFileEntry:
    """Validated in-workspace file ready for safe transfer or inspection."""

    path: Path
    rel_path: str
    size_bytes: int


def is_sensitive_file(file_path: Path, rel_path: Optional[str] = None) -> Tuple[bool, str]:
    """Determine whether a file is sensitive or secret-bearing.

    Returns:
        (is_sensitive, reason)
    """
    filename = file_path.name
    lower_name = filename.lower()
    norm_rel = (rel_path or filename).replace("\\", "/").lower()

    # 1. Allowed configuration templates (only allowed if they do not contain real credentials)
    if lower_name in ALLOWED_CONFIG_TEMPLATES:
        try:
            sample_content = file_path.read_text(encoding="utf-8", errors="replace")[:10000]
            for secret_pat in RE_SECRETS:
                if secret_pat.search(sample_content):
                    return True, "Template configuration contains active credential patterns"
            return False, "Permitted configuration template"
        except Exception:
            return True, "Unreadable configuration template"

    # 2. Secret-bearing environment variants (.env, .env.local, .env.production, etc.)
    for pattern in SENSITIVE_FILENAME_PATTERNS:
        if pattern.match(filename):
            return True, f"Matches sensitive file pattern: {pattern.pattern}"

    # 3. Private keys, certificates, and keystores
    suffix = file_path.suffix.lower()
    if suffix in SENSITIVE_EXTENSIONS:
        return True, f"Matches sensitive file extension: {suffix}"

    # 4. Sensitive directory containment (.ssh, .aws in relative path)
    if any(secret_dir in norm_rel.split("/") for secret_dir in (".ssh", ".aws", ".gnupg")):
        return True, "Resides inside sensitive credentials directory"

    return False, "Safe"


def validate_path_containment(candidate: Path, trusted_root: Path) -> Path:
    """Verify that candidate path is contained within trusted_root and has no symlink traversal.

    Returns:
        Resolved safe Path.
    Raises:
        SecurityViolationError if path escapes, contains symlinks, or cannot be verified.
    """
    try:
        resolved_root = trusted_root.resolve()
    except Exception as exc:
        raise SecurityViolationError(f"Failed to resolve trusted root directory: {exc}")

    # Explicitly reject candidate if it is a symlink
    if candidate.is_symlink():
        raise SecurityViolationError(
            f"Symbolic links are strictly prohibited: '{candidate.name}' is a symlink."
        )

    # Check all parent segments between trusted_root and candidate for symlinks
    current = candidate
    while current != trusted_root and current != current.parent:
        if current.is_symlink():
            raise SecurityViolationError(
                f"Path traversal via symlink directory: '{current.name}' is a symlink."
            )
        current = current.parent

    try:
        resolved_candidate = candidate.resolve()
    except Exception as exc:
        raise SecurityViolationError(f"Failed to resolve candidate path '{candidate.name}': {exc}")

    if not resolved_candidate.is_relative_to(resolved_root):
        raise SecurityViolationError(
            f"Path containment violation: '{candidate.name}' resolves outside trusted workspace root."
        )

    return resolved_candidate


def safe_read_file_bytes(
    file_path: Path,
    trusted_root: Optional[Path] = None,
    max_bytes: Optional[int] = None,
) -> bytes:
    """Safely open and read file bytes with defensive symlink, containment, and race checks.

    Where supported (POSIX), uses os.O_NOFOLLOW. On all platforms, checks lstat before open,
    validates the file descriptor with fstat, verifies regular file mode, confirms metadata
    consistency, and enforces byte size limits.
    """
    if trusted_root is not None:
        validate_path_containment(file_path, trusted_root)

    # 1. Pre-open lstat inspection (does not follow symlinks)
    try:
        lstat_info = os.lstat(file_path)
    except Exception as exc:
        raise SecurityViolationError(f"Cannot stat '{file_path.name}': {exc}")

    if stat.S_ISLNK(lstat_info.st_mode):
        raise SecurityViolationError(
            f"Symbolic links are prohibited: '{file_path.name}' is a symlink."
        )
    if not stat.S_ISREG(lstat_info.st_mode):
        raise SecurityViolationError(f"Non-regular file cannot be read: '{file_path.name}'.")

    # 2. Open file with O_NOFOLLOW where available
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    fd = None
    try:
        fd = os.open(file_path, flags)
        fstat_info = os.fstat(fd)

        if not stat.S_ISREG(fstat_info.st_mode):
            raise SecurityViolationError(
                f"Opened descriptor for '{file_path.name}' is not a regular file."
            )

        # Inode / device comparison on systems supporting it (POSIX)
        if hasattr(lstat_info, "st_ino") and hasattr(fstat_info, "st_ino"):
            if lstat_info.st_ino != 0 and fstat_info.st_ino != 0:
                if lstat_info.st_ino != fstat_info.st_ino or lstat_info.st_dev != fstat_info.st_dev:
                    raise SecurityViolationError(
                        f"Filesystem race detected opening '{file_path.name}'."
                    )

        if max_bytes is not None and fstat_info.st_size > max_bytes:
            raise SecurityViolationError(
                f"File '{file_path.name}' ({fstat_info.st_size} bytes) exceeds limit ({max_bytes} bytes)."
            )

        with os.fdopen(fd, "rb", closefd=True) as stream:
            fd = None  # stream now manages the descriptor
            content = stream.read()

        if max_bytes is not None and len(content) > max_bytes:
            raise SecurityViolationError(
                f"File '{file_path.name}' read bytes ({len(content)}) exceeds limit ({max_bytes} bytes)."
            )

        return content
    except Exception as exc:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if isinstance(exc, SecurityViolationError):
            raise
        raise SecurityViolationError(f"Failed to read file '{file_path.name}': {exc}")


def compute_repository_manifest(repo_dir: Path) -> Dict[str, str]:
    """Deterministically compute SHA-256 hashes of all project files in repo_dir.

    Returns:
        Mapping of sorted relative POSIX paths to SHA-256 hex digests.
    """
    if not repo_dir.exists() or not repo_dir.is_dir():
        return {}

    manifest: Dict[str, str] = {}
    for root, dirnames, filenames in os.walk(repo_dir, followlinks=False):
        # Prune ignored and symlinked directories
        safe_dirs = []
        for d in sorted(dirnames):
            if d.lower() in IGNORED_DIRECTORIES:
                continue
            d_path = Path(root) / d
            try:
                if d_path.is_symlink():
                    continue
            except (OSError, PermissionError):
                continue
            safe_dirs.append(d)
        dirnames[:] = safe_dirs

        for f in sorted(filenames):
            f_path = Path(root) / f
            try:
                if f_path.is_symlink():
                    continue
                rel_path = f_path.relative_to(repo_dir).as_posix()
                content = f_path.read_bytes()
                manifest[rel_path] = hashlib.sha256(content).hexdigest()
            except Exception as exc:
                logger.debug("Error computing manifest entry for %s: %s", f, exc)
                continue

    return manifest


def safe_walk_repository(
    workspace_dir: Path,
    max_files: Optional[int] = None,
    max_file_size_bytes: Optional[int] = None,
    max_total_bytes: Optional[int] = None,
    fail_on_limits: bool = False,
    strict_transfer: bool = False,
) -> Generator[SafeFileEntry, None, Dict[str, Any]]:
    """Safely traverse workspace files, rejecting symlinks, sensitive files, and enforcing bounds.

    In strict_transfer mode, any symlink, unreadable file, unresolvable path, or non-regular
    file aborts the transfer by raising SecurityViolationError, ensuring no remote repository
    transfer is silently incomplete.

    Yields:
        SafeFileEntry objects.
    Returns:
        Summary dictionary containing counts and list of excluded sensitive files.
    """
    resolved_root = workspace_dir.resolve()
    total_files = 0
    total_bytes = 0
    excluded_sensitive_files: List[Tuple[str, str]] = []

    for root, dirnames, filenames in os.walk(workspace_dir, followlinks=False):
        root_path = Path(root)

        # Defensive: check if current directory is a symlink
        try:
            if root_path.is_symlink():
                if strict_transfer:
                    raise SecurityViolationError(
                        f"Symbolic link directory '{root_path.name}' is prohibited in strict transfer mode; aborting transfer."
                    )
                logger.warning("Skipping symlinked directory traversal: %s", root_path.name)
                dirnames.clear()
                continue
        except (OSError, PermissionError) as dir_err:
            if strict_transfer:
                raise SecurityViolationError(
                    f"Failed to inspect directory '{root_path.name}' in strict transfer mode: {dir_err}"
                )
            logger.debug("Error inspecting directory %s: %s", root_path, dir_err)
            dirnames.clear()
            continue

        # Prune ignored and symlinked directories
        safe_dirs = []
        for d in dirnames:
            d_path = root_path / d
            if d.lower() in IGNORED_DIRECTORIES:
                continue
            try:
                if d_path.is_symlink():
                    if strict_transfer:
                        raise SecurityViolationError(
                            f"Symbolic link directory '{d}' is prohibited in strict transfer mode; aborting transfer."
                        )
                    logger.warning("Skipping symlinked directory: %s", d)
                    continue
            except (OSError, PermissionError) as sym_dir_err:
                if strict_transfer:
                    raise SecurityViolationError(
                        f"Failed to inspect directory '{d}' in strict transfer mode: {sym_dir_err}"
                    )
                continue
            safe_dirs.append(d)
        dirnames[:] = safe_dirs

        for f in filenames:
            file_path = root_path / f
            try:
                rel_path = file_path.relative_to(workspace_dir).as_posix()
            except ValueError as val_err:
                if strict_transfer:
                    raise SecurityViolationError(
                        f"Failed to compute relative path for '{f}' in strict transfer mode: {val_err}"
                    )
                continue

            # 1. Reject symlinks immediately
            try:
                if file_path.is_symlink():
                    if strict_transfer:
                        raise SecurityViolationError(
                            f"Symbolic link file '{rel_path}' is prohibited in strict transfer mode; aborting transfer."
                        )
                    logger.warning("Skipping symbolic link: %s", rel_path)
                    continue
            except (OSError, PermissionError) as sym_err:
                if strict_transfer:
                    raise SecurityViolationError(
                        f"Failed to check symlink status for '{rel_path}' in strict transfer mode: {sym_err}"
                    )
                logger.debug("Skipping inaccessible file %s: %s", rel_path, sym_err)
                continue

            # 2. Check path containment defensively
            try:
                resolved_file = file_path.resolve()
                if not resolved_file.is_relative_to(resolved_root):
                    raise SecurityViolationError(
                        f"Path containment violation: '{rel_path}' resolves outside workspace root."
                    )
            except Exception as resolve_err:
                if strict_transfer or isinstance(resolve_err, SecurityViolationError):
                    raise SecurityViolationError(
                        f"Path validation failed for '{rel_path}': {resolve_err}"
                    )
                continue

            # 3. Exclude sensitive and secret-bearing files
            is_secret, reason = is_sensitive_file(file_path, rel_path)
            if is_secret:
                excluded_sensitive_files.append((rel_path, reason))
                logger.info("Excluding sensitive repository file [%s]: %s", reason, rel_path)
                continue

            # 4. Check regular file status and bounds
            try:
                stat_result = file_path.stat()
                if not stat.S_ISREG(stat_result.st_mode):
                    if strict_transfer:
                        raise SecurityViolationError(
                            f"Non-regular file '{rel_path}' is prohibited in strict transfer mode; aborting transfer."
                        )
                    logger.debug("Skipping non-regular file: %s", rel_path)
                    continue

                size = stat_result.st_size
            except (OSError, PermissionError) as stat_err:
                if strict_transfer:
                    raise SecurityViolationError(
                        f"Inaccessible repository file '{rel_path}' in strict transfer mode: {stat_err}; aborting transfer."
                    )
                logger.debug("Skipping inaccessible file %s: %s", rel_path, stat_err)
                continue

            # 5. Check per-file size limit
            if max_file_size_bytes is not None and size > max_file_size_bytes:
                if fail_on_limits or strict_transfer:
                    raise SecurityViolationError(
                        f"Repository file '{rel_path}' size ({size} bytes) exceeds maximum "
                        f"allowed per-file limit ({max_file_size_bytes} bytes)."
                    )
                logger.warning("Skipping oversized file: %s (%d bytes)", rel_path, size)
                continue

            # 6. Check cumulative size limit
            if max_total_bytes is not None and (total_bytes + size) > max_total_bytes:
                if fail_on_limits or strict_transfer:
                    raise SecurityViolationError(
                        f"Total repository transfer size ({total_bytes + size} bytes) exceeds "
                        f"cumulative limit ({max_total_bytes} bytes)."
                    )
                logger.warning("Reached cumulative repository byte limit; halting scan.")
                break

            # 7. Check file count limit
            if max_files is not None and (total_files + 1) > max_files:
                if fail_on_limits or strict_transfer:
                    raise SecurityViolationError(
                        f"Repository file count ({total_files + 1}) exceeds maximum "
                        f"allowed file limit ({max_files})."
                    )
                logger.warning("Reached maximum repository file cap; halting scan.")
                break

            total_files += 1
            total_bytes += size
            yield SafeFileEntry(path=file_path, rel_path=rel_path, size_bytes=size)

    return {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "excluded_sensitive_files": excluded_sensitive_files,
        "excluded_sensitive_count": len(excluded_sensitive_files),
    }
