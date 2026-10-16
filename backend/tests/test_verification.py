"""Unit tests for independent verification engine."""

from app.agents.verification import perform_independent_verification


def test_verification_all_pass(tmp_path):
    """Test verification passes when exit codes and diffs are valid."""
    patch_diff = """--- a/src/service.py
+++ b/src/service.py
@@ -1 +1 @@
-bad
+good
"""
    is_verified, checks = perform_independent_verification(
        patch_diff=patch_diff,
        modified_files=["src/service.py"],
        pre_patch_exit_code=1,
        post_patch_exit_code=0,
        post_patch_output="================== 5 passed in 0.12s ==================",
        workspace_dir=tmp_path / "workspace",
        original_repo_dir=tmp_path / "original",
    )
    assert is_verified is True
    assert all(c.status == "PASSED" for c in checks)


def test_verification_fails_if_baseline_test_passed(tmp_path):
    """Verify check fails if pre-patch exit code is 0 (defect not reproduced)."""
    patch_diff = """--- a/src/service.py
+++ b/src/service.py
@@ -1 +1 @@
-bad
+good
"""
    is_verified, checks = perform_independent_verification(
        patch_diff=patch_diff,
        modified_files=["src/service.py"],
        pre_patch_exit_code=0,  # Bug was not reproduced!
        post_patch_exit_code=0,
        post_patch_output="================== 5 passed ==================",
        workspace_dir=tmp_path / "workspace",
    )
    assert is_verified is False
    repro_check = next(c for c in checks if c.name == "Defect Reproduction Check")
    assert repro_check.status == "FAILED"


def test_verification_fails_if_secret_detected(tmp_path):
    """Verify check fails if secret token pattern is found in output."""
    patch_diff = """--- a/src/service.py
+++ b/src/service.py
@@ -1 +1 @@
-bad
+good
"""
    is_verified, checks = perform_independent_verification(
        patch_diff=patch_diff,
        modified_files=["src/service.py"],
        pre_patch_exit_code=1,
        post_patch_exit_code=0,
        post_patch_output="Test passed with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
        workspace_dir=tmp_path / "workspace",
    )
    assert is_verified is False
    sec_check = next(c for c in checks if c.name == "Credential Redaction Audit")
    assert sec_check.status == "FAILED"
