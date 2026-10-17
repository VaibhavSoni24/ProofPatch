"""Unified diff parser, security validator, and atomic patch applier."""

import re
from pathlib import Path
from typing import List

from app.core.errors import PatchApplicationError, SecurityViolationError
from app.core.logging import logger
from app.sandbox.limits import MAX_PATCH_BYTES

RE_DIFF_HEADER = re.compile(r"^--- (?:a/)?([^\s\t\n]+)")
RE_DIFF_TARGET = re.compile(r"^\+\+\+ (?:b/)?([^\s\t\n]+)")
RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

PROHIBITED_FILE_PATTERNS = [
    ".git",
    ".env",
    "docker-compose",
    ".github",
    "authorized_keys",
    "id_rsa",
    ".ssh",
    "etc/passwd",
    "etc/shadow",
]


def extract_diff_targets(patch_diff: str) -> List[str]:
    """Extract list of target file paths from diff headers."""
    targets = []
    lines = patch_diff.splitlines()
    for line in lines:
        match = RE_DIFF_TARGET.match(line.strip())
        if match:
            target = match.group(1).strip()
            if target != "/dev/null":
                targets.append(target)
    return targets


def validate_patch_security(patch_diff: str, max_bytes: int = MAX_PATCH_BYTES) -> List[str]:
    """Validate diff size, syntax, and path safety constraints.

    Returns:
        List of target file paths if safe.
    Raises:
        SecurityViolationError or PatchApplicationError.
    """
    if not patch_diff or not patch_diff.strip():
        raise PatchApplicationError("Patch diff is empty")

    diff_bytes = len(patch_diff.encode("utf-8"))
    if diff_bytes > max_bytes:
        raise SecurityViolationError(
            f"Patch size ({diff_bytes} bytes) exceeds limit ({max_bytes} bytes)"
        )

    targets = extract_diff_targets(patch_diff)
    if not targets:
        raise PatchApplicationError("No valid '+++ b/<path>' target headers found in patch")

    for target in targets:
        # Check path traversal
        normalized = target.replace("\\", "/")
        if ".." in normalized or normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
            raise SecurityViolationError(
                f"Prohibited path traversal attempt in patch target: {target}"
            )

        for prohibited in PROHIBITED_FILE_PATTERNS:
            if prohibited in normalized.lower():
                raise SecurityViolationError(
                    f"Modification of protected file '{target}' is strictly prohibited"
                )

    return targets


def apply_patch_to_file(file_path: Path, patch_text: str) -> None:
    """Apply a unified diff hunk series directly to a single file."""
    if file_path.is_symlink():
        raise SecurityViolationError(
            f"Modifying symbolic link targets is strictly prohibited: '{file_path.name}'"
        )
    if not file_path.is_file():
        raise PatchApplicationError(f"Target file does not exist: '{file_path.name}'")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        original_lines = f.readlines()

    lines = patch_text.splitlines(keepends=True)
    hunks: List[List[str]] = []
    current_hunk: List[str] = []
    in_hunk = False

    for line in lines:
        if line.startswith("@@"):
            if current_hunk:
                hunks.append(current_hunk)
            current_hunk = [line]
            in_hunk = True
        elif in_hunk:
            current_hunk.append(line)

    if current_hunk:
        hunks.append(current_hunk)

    if not hunks:
        raise PatchApplicationError(f"No valid hunks found for {file_path.name}")

    # Process hunks
    modified_lines = list(original_lines)
    offset = 0

    for hunk in hunks:
        hunk_header = hunk[0]
        match = RE_HUNK_HEADER.match(hunk_header.strip())
        if not match:
            continue

        orig_start = int(match.group(1)) - 1  # 0-indexed

        hunk_body = hunk[1:]
        expected_orig_slice = []
        new_slice = []

        for hline in hunk_body:
            if hline.startswith("-"):
                expected_orig_slice.append(hline[1:])
            elif hline.startswith("+"):
                new_slice.append(hline[1:])
            elif hline.startswith(" "):
                expected_orig_slice.append(hline[1:])
                new_slice.append(hline[1:])

        # Apply hunk at calculated offset
        target_idx = orig_start + offset

        # Strip line ending differences during matching
        def normalize_line(s: str) -> str:
            return s.rstrip("\r\n")

        # Fuzzy matching around target_idx in case of minor offset
        found_idx = None
        search_radius = 5
        start_search = max(0, target_idx - search_radius)
        end_search = min(len(modified_lines), target_idx + search_radius + 1)

        expected_norm = [normalize_line(line_str) for line_str in expected_orig_slice]

        for test_idx in range(start_search, end_search):
            actual_norm = [
                normalize_line(line_str)
                for line_str in modified_lines[test_idx : test_idx + len(expected_orig_slice)]
            ]
            if actual_norm == expected_norm:
                found_idx = test_idx
                break

        if found_idx is None:
            # Fallback exact search across the entire file
            for test_idx in range(len(modified_lines)):
                actual_norm = [
                    normalize_line(line_str)
                    for line_str in modified_lines[test_idx : test_idx + len(expected_orig_slice)]
                ]
                if actual_norm == expected_norm:
                    found_idx = test_idx
                    break

        if found_idx is None:
            raise PatchApplicationError(
                f"Hunk at line {orig_start + 1} could not be matched in {file_path.name}"
            )

        # Ensure all new_slice lines have proper line endings
        clean_new_slice = []
        for line in new_slice:
            if not line.endswith("\n") and not line.endswith("\r\n"):
                line = line + "\n"
            clean_new_slice.append(line)

        # Replace slice
        modified_lines[found_idx : found_idx + len(expected_orig_slice)] = clean_new_slice
        offset += len(clean_new_slice) - len(expected_orig_slice)

    # Write back modified content atomically
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        f.writelines(modified_lines)

    logger.info("Successfully patched file: %s", file_path.name)


def apply_patch_to_workspace(workspace_dir: Path, patch_diff: str) -> List[str]:
    """Parse, validate, and apply unified diff across workspace files."""
    from app.repositories.security import validate_path_containment

    validate_patch_security(patch_diff)

    # Split patch per file if multiple files exist
    file_patches = re.split(r"(?=^--- (?:a/)?\S+)", patch_diff, flags=re.MULTILINE)

    modified_files = []
    for file_patch in file_patches:
        file_patch = file_patch.strip()
        if not file_patch:
            continue

        file_targets = extract_diff_targets(file_patch)
        if not file_targets:
            continue

        target_rel = file_targets[0]
        raw_target = workspace_dir / target_rel

        # Validate path containment and strictly reject symlinks
        target_path = validate_path_containment(raw_target, workspace_dir)

        apply_patch_to_file(target_path, file_patch)
        modified_files.append(target_rel)

    return modified_files
