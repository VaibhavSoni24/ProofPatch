"""Unit tests for independent verification engine."""

from app.agents.verification import perform_independent_verification


def test_verification_all_pass(tmp_path):
    """Test verification passes when exit codes and diffs are valid."""
    ws = tmp_path / "workspace"
    orig = tmp_path / "original"
    ws.mkdir(parents=True, exist_ok=True)
    orig.mkdir(parents=True, exist_ok=True)
    (ws / "src").mkdir(parents=True, exist_ok=True)
    (orig / "src").mkdir(parents=True, exist_ok=True)
    (orig / "src" / "service.py").write_text("bad\n", encoding="utf-8")
    (ws / "src" / "service.py").write_text("good\n", encoding="utf-8")

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
        pre_patch_output="FAILED tests/test_service.py::test_service_run - AssertionError\n=== 1 failed, 4 passed ===",
        post_patch_output="================== 5 passed in 0.12s ==================",
        workspace_dir=ws,
        original_repo_dir=orig,
        trusted_workspace_root=tmp_path,
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


def test_verification_inconclusive_on_environmental_error(tmp_path):
    """Verify check marks INCONCLUSIVE if baseline failed due to missing module or collection error."""
    patch_diff = """--- a/src/service.py
+++ b/src/service.py
@@ -1 +1 @@
-bad
+good
"""
    is_verified, checks = perform_independent_verification(
        patch_diff=patch_diff,
        modified_files=["src/service.py"],
        pre_patch_exit_code=2,
        post_patch_exit_code=0,
        pre_patch_output="ModuleNotFoundError: No module named 'nonexistent_package'\nno tests collected",
        post_patch_output="================== 5 passed in 0.10s ==================",
        workspace_dir=tmp_path / "workspace",
    )
    assert is_verified is False
    repro_check = next(c for c in checks if c.name == "Defect Reproduction Check")
    assert repro_check.status == "INCONCLUSIVE"


def test_verification_not_run_when_exit_codes_missing(tmp_path):
    """Verify checks mark NOT_RUN and do not falsely pass when exit codes are None."""
    patch_diff = """--- a/src/service.py
+++ b/src/service.py
@@ -1 +1 @@
-bad
+good
"""
    is_verified, checks = perform_independent_verification(
        patch_diff=patch_diff,
        modified_files=["src/service.py"],
        pre_patch_exit_code=None,
        post_patch_exit_code=None,
        workspace_dir=tmp_path / "workspace",
    )
    assert is_verified is False
    repro_check = next(c for c in checks if c.name == "Defect Reproduction Check")
    assert repro_check.status == "NOT_RUN"
    reg_check = next(c for c in checks if c.name == "Regression Suite Execution")
    assert reg_check.status == "NOT_RUN"


def test_verification_fails_on_contradictory_zero_exit_code(tmp_path):
    """Verify check fails if post-patch exit code is 0 but output contains failure markers."""
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
        pre_patch_output="1 failed, 4 passed",
        post_patch_output="CRITICAL FAILURE in test suite: unhandled error occurred",
        workspace_dir=tmp_path / "workspace",
    )
    assert is_verified is False
    reg_check = next(c for c in checks if c.name == "Regression Suite Execution")
    assert reg_check.status == "FAILED"


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


def test_baseline_classification_successful_reproduction():
    """Verify correlated failing test produces PASSED baseline reproduction."""
    from app.agents.verification import classify_baseline_reproduction

    output = """
FAILED tests/test_billing.py::test_discount_rounding - AssertionError: 99.0 != 100.0
=== 1 failed, 4 passed in 0.20s ===
"""
    status, reason = classify_baseline_reproduction(
        exit_code=1,
        output=output,
        bug_title="Billing discount rounding precision error",
        bug_description="Discount calculation rounds down incorrectly",
    )
    assert status == "PASSED"
    assert "test_discount_rounding" in reason


def test_baseline_classification_unrelated_test_failure():
    """Verify failing test unrelated to reported bug produces INCONCLUSIVE baseline reproduction."""
    from app.agents.verification import classify_baseline_reproduction

    output = """
FAILED tests/test_auth.py::test_jwt_signature - ExpiredSignatureError: token expired
=== 1 failed, 4 passed in 0.15s ===
"""
    status, reason = classify_baseline_reproduction(
        exit_code=1,
        output=output,
        bug_title="Billing discount rounding precision error",
        bug_description="Discount calculation rounds down incorrectly",
    )
    assert status == "INCONCLUSIVE"
    assert "unrelated to reported defect" in reason


def test_baseline_classification_import_error():
    """Verify import failure without test execution produces INCONCLUSIVE baseline reproduction."""
    from app.agents.verification import classify_baseline_reproduction

    output = "ModuleNotFoundError: No module named 'billing_internal'"
    status, reason = classify_baseline_reproduction(
        exit_code=2,
        output=output,
        bug_title="Billing discount error",
    )
    assert status == "INCONCLUSIVE"
    assert "dependency or environment" in reason


def test_baseline_classification_collection_syntax_error():
    """Verify syntax or collection error produces INCONCLUSIVE baseline reproduction."""
    from app.agents.verification import classify_baseline_reproduction

    output = "SyntaxError: invalid syntax in tests/test_billing.py, line 12"
    status, reason = classify_baseline_reproduction(
        exit_code=2,
        output=output,
        bug_title="Billing discount error",
    )
    assert status == "INCONCLUSIVE"
    assert "discovery or test collection" in reason


def test_baseline_classification_timeout():
    """Verify timeout produces INCONCLUSIVE baseline reproduction."""
    from app.agents.verification import classify_baseline_reproduction

    status, reason = classify_baseline_reproduction(
        exit_code=124,
        output="Command timed out after 60s",
        bug_title="Billing discount error",
        timed_out=True,
    )
    assert status == "INCONCLUSIVE"
    assert "timed out" in reason


def test_baseline_classification_missing_results():
    """Verify non-zero exit without failure records produces INCONCLUSIVE baseline reproduction."""
    from app.agents.verification import classify_baseline_reproduction

    status, reason = classify_baseline_reproduction(
        exit_code=137,
        output="Process terminated by SIGKILL",
        bug_title="Billing discount error",
    )
    assert status == "INCONCLUSIVE"
    assert "produced no test failure records" in reason


def test_verification_rejects_unrelated_baseline_failure(tmp_path):
    """Verify full verification audit rejects unrelated baseline failures as unverified."""
    patch_diff = """--- a/src/billing.py
+++ b/src/billing.py
@@ -1 +1 @@
-bad
+good
"""
    is_verified, checks = perform_independent_verification(
        patch_diff=patch_diff,
        modified_files=["src/billing.py"],
        pre_patch_exit_code=1,
        post_patch_exit_code=0,
        pre_patch_output="FAILED tests/test_telemetry.py::test_telemetry_flush\n=== 1 failed ===",
        post_patch_output="================== 5 passed in 0.10s ==================",
        workspace_dir=tmp_path / "workspace",
        bug_title="Billing discount error",
        bug_description="Calculation rounds incorrectly",
    )
    assert is_verified is False
    repro_check = next(c for c in checks if c.name == "Defect Reproduction Check")
    assert repro_check.status == "INCONCLUSIVE"


def test_verification_missing_original_repository_information(tmp_path):
    """Verify missing original repository information marks check NOT_RUN and fails verification."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
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
        pre_patch_output="1 failed, 4 passed",
        post_patch_output="5 passed",
        workspace_dir=ws,
        original_repo_dir=None,  # Missing original repo info!
        trusted_workspace_root=tmp_path,
    )
    assert is_verified is False
    pres_check = next(c for c in checks if c.name == "Source Repository Immutability")
    assert pres_check.status == "NOT_RUN"
    assert "Original repository directory was not provided" in pres_check.detail


def test_verification_workspace_outside_root_fails(tmp_path):
    """Verify workspace located outside configured workspace root fails verification."""
    designated_root = tmp_path / "designated_root"
    designated_root.mkdir()
    outside_ws = tmp_path / "outside_workspace"
    outside_ws.mkdir()
    orig = tmp_path / "original"
    orig.mkdir()

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
        pre_patch_output="1 failed",
        post_patch_output="5 passed",
        workspace_dir=outside_ws,
        original_repo_dir=orig,
        trusted_workspace_root=designated_root,
    )
    assert is_verified is False
    pres_check = next(c for c in checks if c.name == "Source Repository Immutability")
    assert pres_check.status == "FAILED"
    assert "lies outside designated workspace root" in pres_check.detail


def test_verification_correct_isolated_workspace_passes(tmp_path):
    """Verify correct isolated workspace with pristine original source passes audit."""
    ws = tmp_path / "workspace"
    orig = tmp_path / "original"
    (ws / "src").mkdir(parents=True)
    (orig / "src").mkdir(parents=True)
    (orig / "src" / "service.py").write_text("bad\n", encoding="utf-8")
    (ws / "src" / "service.py").write_text("good\n", encoding="utf-8")

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
        pre_patch_output="FAILED tests/test_service.py::test_service_run - AssertionError\n=== 1 failed, 4 passed ===",
        post_patch_output="================== 5 passed in 0.12s ==================",
        workspace_dir=ws,
        original_repo_dir=orig,
        trusted_workspace_root=tmp_path,
    )
    assert is_verified is True
    pres_check = next(c for c in checks if c.name == "Source Repository Immutability")
    assert pres_check.status == "PASSED"
    assert "strictly unmodified" in pres_check.detail


def test_verification_contradictory_preservation_evidence_fails(tmp_path):
    """Verify that if original repo files were modified to match the patch, verification fails."""
    ws = tmp_path / "workspace"
    orig = tmp_path / "original"
    (ws / "src").mkdir(parents=True)
    (orig / "src").mkdir(parents=True)
    # Contradiction: original repo file was mutated to match post-patch file!
    (orig / "src" / "service.py").write_text("good\n", encoding="utf-8")
    (ws / "src" / "service.py").write_text("good\n", encoding="utf-8")

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
        pre_patch_output="1 failed",
        post_patch_output="5 passed",
        workspace_dir=ws,
        original_repo_dir=orig,
        trusted_workspace_root=tmp_path,
    )
    assert is_verified is False
    pres_check = next(c for c in checks if c.name == "Source Repository Immutability")
    assert pres_check.status == "FAILED"
    assert "Contradictory evidence" in pres_check.detail


def test_verification_incomplete_checks_prevent_verified_status(tmp_path):
    """Verify that any non-passed check prevents the final run from being marked verified."""
    ws = tmp_path / "workspace"
    orig = tmp_path / "original"
    ws.mkdir()
    orig.mkdir()

    # Pre-patch exit code missing -> reproduction is NOT_RUN
    is_verified, checks = perform_independent_verification(
        patch_diff="--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n-a\n+b\n",
        modified_files=["f.py"],
        pre_patch_exit_code=None,
        post_patch_exit_code=0,
        workspace_dir=ws,
        original_repo_dir=orig,
        trusted_workspace_root=tmp_path,
    )
    assert is_verified is False
    assert any(c.status != "PASSED" for c in checks)
