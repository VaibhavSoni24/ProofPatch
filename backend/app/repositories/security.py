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
            f"Symbolic links are strictly prohibited: '{file_path.name}' is a symlink."
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


def safe_hash_file(
    file_path: Path,
    trusted_root: Optional[Path] = None,
    max_bytes: Optional[int] = None,
    chunk_size: int = 65536,
) -> Tuple[str, int]:
    """Safely stream SHA-256 hash calculation using O_NOFOLLOW without loading entire file into memory.

    Returns:
        (sha256_hex_digest, total_bytes_read)
    """
    if trusted_root is not None:
        validate_path_containment(file_path, trusted_root)

    try:
        lstat_info = os.lstat(file_path)
    except Exception as exc:
        raise SecurityViolationError(f"Cannot stat '{file_path.name}': {exc}")

    if stat.S_ISLNK(lstat_info.st_mode):
        raise SecurityViolationError(
            f"Symbolic links are strictly prohibited: '{file_path.name}' is a symlink."
        )
    if not stat.S_ISREG(lstat_info.st_mode):
        raise SecurityViolationError(f"Non-regular file cannot be hashed: '{file_path.name}'.")

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

        hasher = hashlib.sha256()
        total_read = 0
        with os.fdopen(fd, "rb", closefd=True) as stream:
            fd = None
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                total_read += len(chunk)
                if max_bytes is not None and total_read > max_bytes:
                    raise SecurityViolationError(
                        f"File '{file_path.name}' bytes ({total_read}) exceeds limit ({max_bytes} bytes)."
                    )
                hasher.update(chunk)

        return hasher.hexdigest(), total_read
    except Exception as exc:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if isinstance(exc, SecurityViolationError):
            raise
        raise SecurityViolationError(f"Failed to read file '{file_path.name}': {exc}")


def compute_repository_manifest(
    repo_dir: Path,
    trusted_root: Optional[Path] = None,
    max_files: Optional[int] = None,
    max_file_size_bytes: Optional[int] = None,
    max_total_bytes: Optional[int] = None,
) -> Dict[str, str]:
    """Deterministically compute SHA-256 hashes of all project files in repo_dir.

    Fails closed immediately on:
    - Non-existent or non-directory repo_dir
    - Path containment violations against trusted_root or repo_dir
    - Any symbolic link (file or directory) in the repository tree
    - Any unreadable, non-regular, or inaccessible file
    - File size, count, or cumulative total byte limits

    Returns:
        Mapping of sorted relative POSIX paths to SHA-256 hex digests.
    Raises:
        SecurityViolationError if any file or directory violates security, containment, or limits.
    """
    if not repo_dir.exists() or not repo_dir.is_dir():
        raise SecurityViolationError(
            f"Repository directory does not exist or is not a directory: {repo_dir}"
        )

    resolved_repo = repo_dir.resolve()
    if trusted_root is not None:
        resolved_root = trusted_root.resolve()
        if not resolved_repo.is_relative_to(resolved_root):
            raise SecurityViolationError(
                f"Repository path '{repo_dir}' lies outside trusted workspace root."
            )

    from app.sandbox.limits import (
        MAX_FILE_SIZE_BYTES,
        MAX_FILES_IN_REPOSITORY,
        MAX_REPOSITORY_TRANSFER_BYTES,
    )

    limit_files = max_files if max_files is not None else MAX_FILES_IN_REPOSITORY
    limit_file_size = (
        max_file_size_bytes if max_file_size_bytes is not None else MAX_FILE_SIZE_BYTES
    )
    limit_total_size = (
        max_total_bytes if max_total_bytes is not None else MAX_REPOSITORY_TRANSFER_BYTES
    )

    manifest: Dict[str, str] = {}
    cumulative_bytes = 0

    for root, dirnames, filenames in os.walk(repo_dir, followlinks=False):
        safe_dirs = []
        for d in sorted(dirnames):
            if d.lower() in IGNORED_DIRECTORIES:
                continue
            d_path = Path(root) / d
            try:
                if d_path.is_symlink():
                    raise SecurityViolationError(
                        f"Symbolic link directory '{d}' is strictly prohibited in repository manifest."
                    )
                if not d_path.resolve().is_relative_to(resolved_repo):
                    raise SecurityViolationError(
                        f"Directory traversal via '{d}' escapes repository root."
                    )
            except (OSError, PermissionError) as exc:
                raise SecurityViolationError(
                    f"Failed to inspect directory '{d}' during manifest generation: {exc}"
                )
            safe_dirs.append(d)
        dirnames[:] = safe_dirs

        for f in sorted(filenames):
            f_path = Path(root) / f
            try:
                if f_path.is_symlink():
                    raise SecurityViolationError(
                        f"Symbolic link '{f}' is strictly prohibited in repository manifest."
                    )
            except (OSError, PermissionError) as exc:
                raise SecurityViolationError(f"Failed to check symlink status for '{f}': {exc}")

            try:
                rel_path = f_path.relative_to(repo_dir).as_posix()
            except ValueError as val_err:
                raise SecurityViolationError(
                    f"Failed to compute relative path for '{f}': {val_err}"
                )

            try:
                resolved_file = f_path.resolve()
                if not resolved_file.is_relative_to(resolved_repo):
                    raise SecurityViolationError(
                        f"Path containment violation: '{rel_path}' resolves outside repository root."
                    )
            except Exception as exc:
                if isinstance(exc, SecurityViolationError):
                    raise
                raise SecurityViolationError(f"Failed to resolve '{rel_path}': {exc}")

            if len(manifest) >= limit_files:
                raise SecurityViolationError(
                    f"Repository file count exceeds maximum allowed limit ({limit_files})."
                )

            file_hash, file_bytes = safe_hash_file(
                f_path, trusted_root=repo_dir, max_bytes=limit_file_size
            )
            cumulative_bytes += file_bytes
            if cumulative_bytes > limit_total_size:
                raise SecurityViolationError(
                    f"Repository cumulative size ({cumulative_bytes} bytes) exceeds limit ({limit_total_size} bytes)."
                )

            manifest[rel_path] = file_hash

    return dict(sorted(manifest.items()))


def safe_isolate_repository(
    source_dir: Path,
    target_dir: Path,
    trusted_workspace_root: Optional[Path] = None,
    trusted_source_root: Optional[Path] = None,
    max_files: Optional[int] = None,
    max_file_size_bytes: Optional[int] = None,
    max_total_bytes: Optional[int] = None,
) -> None:
    """Safely isolate an untrusted repository checkout into a disposable workspace without following symlinks.

    Fails closed immediately on:
    - Non-existent or invalid source directory
    - Path containment violations against trusted roots
    - Source and target path collision
    - Any symbolic link (file or directory) in the repository tree
    - Any non-regular, unreadable, or unresolvable file
    - File size, count, or cumulative total byte limits
    """
    import shutil

    if not source_dir.exists() or not source_dir.is_dir():
        raise SecurityViolationError(
            f"Source repository directory does not exist or is not a directory: {source_dir}"
        )

    resolved_source = source_dir.resolve()
    resolved_target = target_dir.resolve()

    if trusted_workspace_root is not None:
        resolved_root = trusted_workspace_root.resolve()
        if not resolved_target.is_relative_to(resolved_root):
            raise SecurityViolationError(
                f"Target workspace '{target_dir}' lies outside trusted workspace root."
            )
        if resolved_target == resolved_root:
            raise SecurityViolationError(
                "Target workspace directory cannot be equal to the workspace root directory."
            )

    effective_source_root = trusted_source_root or trusted_workspace_root
    if effective_source_root is not None:
        resolved_src_root = effective_source_root.resolve()
        if not resolved_source.is_relative_to(resolved_src_root):
            raise SecurityViolationError(
                f"Source directory '{source_dir}' lies outside trusted workspace root."
            )

    if resolved_source == resolved_target:
        raise SecurityViolationError("Source and target workspace directories must be distinct.")

    # 1. Fully audit the source repository manifest upfront (fails closed on any symlink or unreadable file)
    compute_repository_manifest(
        source_dir,
        trusted_root=trusted_source_root,
        max_files=max_files,
        max_file_size_bytes=max_file_size_bytes,
        max_total_bytes=max_total_bytes,
    )

    # 2. Safely clean existing target workspace
    if target_dir.exists():
        shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    # 3. Perform safe file-by-file copy without following symlinks
    try:
        for root, dirnames, filenames in os.walk(source_dir, followlinks=False):
            safe_dirs = []
            for d in sorted(dirnames):
                if d.lower() in IGNORED_DIRECTORIES:
                    continue
                d_path = Path(root) / d
                if d_path.is_symlink():
                    raise SecurityViolationError(
                        f"Symbolic link directory '{d}' is strictly prohibited during isolation."
                    )
                safe_dirs.append(d)
            dirnames[:] = safe_dirs

            rel_root = Path(root).relative_to(source_dir)
            dest_root = target_dir / rel_root
            dest_root.mkdir(parents=True, exist_ok=True)

            for f in sorted(filenames):
                src_file = Path(root) / f
                if src_file.is_symlink():
                    raise SecurityViolationError(
                        f"Symbolic link '{f}' is strictly prohibited during isolation."
                    )
                dest_file = dest_root / f
                data = safe_read_file_bytes(
                    src_file, trusted_root=source_dir, max_bytes=max_file_size_bytes
                )
                dest_file.write_bytes(data)
    except Exception:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        raise


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
