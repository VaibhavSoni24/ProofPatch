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
