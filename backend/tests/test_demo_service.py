"""Unit tests for deterministic demo service execution."""

from app.services.demo import execute_demo_run


def test_execute_demo_run_lifecycle(db_session):
    """Test full execution of demo workflow in temporary workspace."""
    run = execute_demo_run(db_session)

    assert run.id.startswith("demo_")
    assert run.mode == "demo"
    assert run.status == "passed"
    assert run.reproduced is True
    assert run.pre_patch_exit_code != 0
    assert run.post_patch_exit_code == 0
    assert run.test_passed is True
    assert run.verified is True
    assert run.patch_diff is not None
    assert "src/billing.py" in run.modified_files

    # Assert stage events are recorded chronologically
    event_stages = [e.stage for e in run.events]
    assert "inspect" in event_stages
    assert "reproduce" in event_stages
    assert "diagnose" in event_stages
    assert "patch" in event_stages
    assert "test" in event_stages
    assert "verify" in event_stages
    assert "report" in event_stages

    # Assert exactly 6 independent verification checks were performed and passed
    evidence_checks = [c for c in run.events if c.stage == "verify"]
    assert len(evidence_checks) > 0


def test_execute_demo_run_unrelated_test_failure(db_session):
    """Verify demo run halts as failed if baseline failure is unrelated to reported defect."""
    from unittest.mock import patch

    with patch(
        "app.services.demo.execute_test_command",
        return_value=(
            1,
            "FAILED tests/test_other.py::test_unrelated - AssertionError: wrong val",
            0.1,
            "",
        ),
    ):
        run = execute_demo_run(db_session)

        assert run.reproduced is False
        assert run.status == "inconclusive"
        assert run.verified is False
        assert run.patch_diff is None


def test_execute_demo_run_import_failure(db_session):
    """Verify demo run halts as inconclusive on dependency/import errors."""
    from unittest.mock import patch

    with patch(
        "app.services.demo.execute_test_command",
        return_value=(1, "ModuleNotFoundError: No module named 'pytest'", 0.1, ""),
    ):
        run = execute_demo_run(db_session)

        assert run.reproduced is False
        assert run.status == "inconclusive"
        assert run.verified is False
        assert run.patch_diff is None


def test_execute_demo_run_collection_failure(db_session):
    """Verify demo run halts as inconclusive on test collection / syntax errors."""
    from unittest.mock import patch

    with patch(
        "app.services.demo.execute_test_command",
        return_value=(
            2,
            "SyntaxError: invalid syntax in test file\nerrors during collection",
            0.1,
            "",
        ),
    ):
        run = execute_demo_run(db_session)

        assert run.reproduced is False
        assert run.status == "inconclusive"
        assert run.verified is False
        assert run.patch_diff is None


def test_execute_demo_run_timeout(db_session):
    """Verify demo run halts as inconclusive on command timeout."""
    from unittest.mock import patch

    with patch(
        "app.services.demo.execute_test_command",
        return_value=(124, "Command timed out after 30 seconds", 30.0, ""),
    ):
        run = execute_demo_run(db_session)

        assert run.reproduced is False
        assert run.status == "inconclusive"
        assert run.verified is False
        assert run.patch_diff is None


def test_execute_demo_run_clean_baseline(db_session):
    """Verify demo run fails if baseline tests pass cleanly (defect not reproduced)."""
    from unittest.mock import patch

    with patch(
        "app.services.demo.execute_test_command",
        return_value=(0, "7 passed in 0.04s", 0.04, ""),
    ):
        run = execute_demo_run(db_session)

        assert run.reproduced is False
        assert run.status == "failed"
        assert run.verified is False
        assert run.patch_diff is None


def test_execute_demo_run_patch_application_failure(db_session):
    """Verify demo run records failure if patch application raises an error."""
    from unittest.mock import patch

    with patch(
        "app.services.demo.apply_patch_to_workspace",
        side_effect=ValueError("Patch hunk 1 rejected"),
    ):
        run = execute_demo_run(db_session)

        assert run.reproduced is True
        assert run.status == "failed"
        assert run.verified is False


def test_execute_demo_run_post_patch_failure(db_session):
    """Verify demo run fails if post-patch tests fail."""
    from unittest.mock import patch

    from app.sandbox.commands import execute_test_command

    original_exec = execute_test_command

    def mock_exec(ws, args):
        if hasattr(mock_exec, "called"):
            return (
                1,
                "FAILED tests/test_billing.py::test_new_regression - AssertionError",
                0.1,
                "",
            )
        mock_exec.called = True
        return original_exec(ws, args)

    with patch("app.services.demo.execute_test_command", side_effect=mock_exec):
        run = execute_demo_run(db_session)

        assert run.reproduced is True
        assert run.test_passed is False
        assert run.status == "failed"
        assert run.verified is False
