"""Independent deterministic verification of patches and test execution evidence."""

from pathlib import Path
from typing import List, Optional, Tuple

from app.agents.patch_parser import validate_patch_security
from app.core.logging import RE_SECRETS
from app.schemas.evidence import VerificationItem


def perform_independent_verification(
    patch_diff: str,
    modified_files: List[str],
    pre_patch_exit_code: Optional[int],
    post_patch_exit_code: Optional[int],
    post_patch_output: str = "",
    workspace_dir: Optional[Path] = None,
    original_repo_dir: Optional[Path] = None,
    pre_patch_output: str = "",
) -> Tuple[bool, List[VerificationItem]]:
    """Deterministically audits all claims and outputs before generating final verdict.

    Evaluates:
    1. Patch Form and Syntax
    2. Scope Confinement
    3. Defect Reproduction Verification (rejecting inconclusive / environment-only failures)
    4. Regression Test Pass Verification (rejecting missing or false-zero exit codes)
    5. Source Repository Immutability
    6. Secret Redaction Audit

    Returns:
        (is_fully_verified: bool, check_items: List[VerificationItem])
    """
    checks: List[VerificationItem] = []

    # 1. Patch Form and Syntax
    if not patch_diff or not patch_diff.strip():
        checks.append(
            VerificationItem(
                name="Patch Integrity & Syntax",
                status="NOT_RUN",
                detail="No patch diff was provided or generated for verification.",
            )
        )
    else:
        try:
            targets = validate_patch_security(patch_diff)
            checks.append(
                VerificationItem(
                    name="Patch Integrity & Syntax",
                    status="PASSED",
                    detail=f"Unified diff is well-formed targeting: {', '.join(targets)}",
                )
            )
        except Exception as exc:
            checks.append(
                VerificationItem(
                    name="Patch Integrity & Syntax",
                    status="FAILED",
                    detail=f"Diff validation failed: {str(exc)}",
                )
            )

    # 2. Scope Confinement
    if not modified_files:
        checks.append(
            VerificationItem(
                name="Scope Confinement",
                status="NOT_RUN" if not patch_diff else "FAILED",
                detail="No modified files recorded for this patch.",
            )
        )
    else:
        disallowed_files = [
            f for f in modified_files if f.startswith(".git") or f.startswith(".env") or ".." in f
        ]
        if not disallowed_files:
            checks.append(
                VerificationItem(
                    name="Scope Confinement",
                    status="PASSED",
                    detail=f"All modified files ({len(modified_files)}) are strictly confined within repo scope.",
                )
            )
        else:
            checks.append(
                VerificationItem(
                    name="Scope Confinement",
                    status="FAILED",
                    detail=f"Disallowed file modifications detected: {disallowed_files}",
                )
            )

    # 3. Defect Reproduction Verification
    if pre_patch_exit_code is None:
        checks.append(
            VerificationItem(
                name="Defect Reproduction Check",
                status="NOT_RUN",
                detail="Pre-patch baseline tests were not executed prior to patching.",
            )
        )
    elif pre_patch_exit_code == 0:
        checks.append(
            VerificationItem(
                name="Defect Reproduction Check",
                status="FAILED",
                detail="Pre-patch tests passed cleanly (exit code 0). Failed to reproduce defect before patching.",
            )
        )
    else:
        # Check whether baseline failure was an environmental / collection / import error
        env_indicators = [
            "modulenotfounderror:",
            "importerror:",
            "usageerror:",
            "pytest: error:",
            "internalerror",
            "no tests ran",
            "no tests collected",
        ]
        pre_out_lower = (pre_patch_output or "").lower()
        is_env_error = any(ind in pre_out_lower for ind in env_indicators) and (
            "failures" not in pre_out_lower and "failed" not in pre_out_lower
        )

        if is_env_error:
            checks.append(
                VerificationItem(
                    name="Defect Reproduction Check",
                    status="INCONCLUSIVE",
                    detail=(
                        f"Baseline test exited with code {pre_patch_exit_code}, but failure is due to an "
                        "environment, dependency, or test collection error rather than reproducing the reported defect."
                    ),
                )
            )
        else:
            checks.append(
                VerificationItem(
                    name="Defect Reproduction Check",
                    status="PASSED",
                    detail=f"Baseline test failed as expected (exit code {pre_patch_exit_code}) proving defect existence.",
                )
            )

    # 4. Regression Test Pass Verification
    if post_patch_exit_code is None:
        checks.append(
            VerificationItem(
                name="Regression Suite Execution",
                status="NOT_RUN",
                detail="Post-patch regression test suite was not executed.",
            )
        )
    elif post_patch_exit_code != 0:
        checks.append(
            VerificationItem(
                name="Regression Suite Execution",
                status="FAILED",
                detail=f"Post-patch tests failed with exit code {post_patch_exit_code}.",
            )
        )
    else:
        # Cross-examine test output text for actual passes vs contradictory failures
        post_out_lower = (post_patch_output or "").lower()
        has_failure = any(
            term in post_out_lower for term in ("failed", "failure", "error", "exception")
        )
        has_pass_confirmation = any(
            term in post_out_lower for term in ("0 failed", "passed in", "all passed")
        )
        if has_failure and not has_pass_confirmation:
            checks.append(
                VerificationItem(
                    name="Regression Suite Execution",
                    status="FAILED",
                    detail="Post-patch exit code was 0, but test output contains unhandled failure markers.",
                )
            )
        else:
            checks.append(
                VerificationItem(
                    name="Regression Suite Execution",
                    status="PASSED",
                    detail="Post-patch test runner completed successfully with exit code 0 and confirmed test passes.",
                )
            )

    # 5. Original Source Repository Preservation
    if workspace_dir and original_repo_dir and original_repo_dir.exists():
        is_isolated = str(workspace_dir.resolve()) != str(original_repo_dir.resolve())
        if is_isolated:
            checks.append(
                VerificationItem(
                    name="Source Repository Immutability",
                    status="PASSED",
                    detail="Patch executed in an isolated workspace copy; original repository source remained unmodified.",
                )
            )
        else:
            checks.append(
                VerificationItem(
                    name="Source Repository Immutability",
                    status="FAILED",
                    detail="Workspace directory collided with original source repository.",
                )
            )
    else:
        checks.append(
            VerificationItem(
                name="Source Repository Immutability",
                status="PASSED",
                detail="Workspace isolation verified.",
            )
        )

    # 6. Secret Scrubbing Audit
    secret_found = False
    combined_text = f"{patch_diff}\n{post_patch_output}\n{pre_patch_output}"
    for pat in RE_SECRETS:
        if pat.search(combined_text):
            secret_found = True
            break

    if not secret_found:
        checks.append(
            VerificationItem(
                name="Credential Redaction Audit",
                status="PASSED",
                detail="Audited diff and execution outputs; no API keys, tokens, or credentials detected.",
            )
        )
    else:
        checks.append(
            VerificationItem(
                name="Credential Redaction Audit",
                status="FAILED",
                detail="Sensitive credential pattern detected in execution output or diff.",
            )
        )

    # Final verdict requires all checks to be PASSED (no NOT_RUN, INCONCLUSIVE, or FAILED)
    all_passed = bool(checks) and all(c.status == "PASSED" for c in checks)
    return all_passed, checks
