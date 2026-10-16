"""Integration test for orchestrator with mocked providers and isolated local workspace."""

import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator import execute_live_run
from app.core.errors import ProviderError
from app.providers.base import ProviderResponse, SearchResponse, SearchResultItem
from app.sandbox.local_runner import LocalExecutionBackend
from app.schemas.runs import RunCreateRequest


@pytest.mark.asyncio
async def test_orchestrator_live_workflow_mocked(db_session, tmp_path):
    """Test full multi-stage async orchestrator flow with mocked AI and search providers."""
    project_root = Path(__file__).resolve().parent.parent.parent
    bundled_source = project_root / "examples" / "buggy-python-service"

    # Async Mock for Nebius provider
    mock_nebius = AsyncMock()

    # 1. Diagnosis response
    diag_json = json.dumps(
        {
            "problem_summary": "6-seat boundary excludes customer from Growth tier.",
            "likely_root_cause": "Line 34 has 'seats > 6' instead of 'seats >= 6'.",
            "relevant_files": ["src/billing.py"],
            "proposed_minimal_fix": "Change > 6 to >= 6.",
            "potential_side_effects": "None",
        }
    )
    # 2. Patch response
    patch_diff = """--- a/src/billing.py
+++ b/src/billing.py
@@ -28,5 +28,5 @@
     # DEFECT: Boundary check for Growth tier uses > 6 instead of >= 6.
     # When seats == 6, this condition is False and it falls through to the Starter tier ($20/seat, 0% discount).
-    if seats > 6 and seats <= 20:
+    if seats >= 6 and seats <= 20:
         tier_name = "Growth"
         unit_price = 18.00
"""
    mock_nebius.generate_completion.side_effect = [
        ProviderResponse(content=diag_json, model="nvidia/nemotron-4-340b-instruct"),
        ProviderResponse(content=patch_diff, model="nvidia/nemotron-4-340b-instruct"),
    ]

    # Async Mock for Tavily provider
    mock_tavily = AsyncMock()
    mock_tavily.search.return_value = SearchResponse(
        enabled=True,
        query="Bug query",
        results=[
            SearchResultItem(
                title="Python Tiers",
                url="https://example.com/docs",
                content="Boundary check guidance",
            )
        ],
    )

    request = RunCreateRequest(
        repository_url="https://github.com/VaibhavSoni24/ProofPatch",
        bug_title="Boundary defect on 6 seats",
        bug_description="A customer purchasing 6 seats gets charged standard starter rate instead of growth.",
        mode="live",
        confirm_live_execution=True,
    )

    def mock_clone(url, target_dir):
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(bundled_source, target_dir)
        return "abc123commit"

    with patch("app.agents.orchestrator.clone_public_repository", side_effect=mock_clone):
        # Use LocalExecutionBackend configured for test isolation
        test_backend = LocalExecutionBackend(allow_untrusted=True)

        run = await execute_live_run(
            db=db_session,
            request=request,
            nebius_provider=mock_nebius,
            tavily_provider=mock_tavily,
            execution_backend=test_backend,
        )

        assert run.status == "passed"
        assert run.reproduced is True
        assert run.test_passed is True
        assert run.verified is True
        assert run.commit_hash == "abc123commit"
        assert run.model_call_count == 2
        assert mock_nebius.generate_completion.call_count == 2


@pytest.mark.asyncio
async def test_orchestrator_stops_if_reproduction_inconclusive(db_session, tmp_path):
    """Test workflow safely stops as 'inconclusive' without model calls if baseline tests pass."""
    mock_nebius = AsyncMock()
    mock_tavily = AsyncMock()
    mock_backend = AsyncMock()

    # Simulate baseline tests passing cleanly (exit code 0)
    mock_res = AsyncMock(exit_code=0, output="All tests passed cleanly")
    mock_backend.execute_tests.return_value = mock_res
    mock_backend.backend_name = "mock_sandbox"

    request = RunCreateRequest(
        repository_url="https://github.com/VaibhavSoni24/ProofPatch",
        bug_title="Phantom defect",
        bug_description="Bug that doesn't actually reproduce.",
        mode="live",
        confirm_live_execution=True,
    )

    with patch("app.agents.orchestrator.clone_public_repository", return_value="def456"):
        with patch("app.agents.orchestrator.inspect_repository") as mock_inspect:
            mock_inspect.return_value = AsyncMock(source_files=[], test_files=[], total_files=0)

            run = await execute_live_run(
                db=db_session,
                request=request,
                nebius_provider=mock_nebius,
                tavily_provider=mock_tavily,
                execution_backend=mock_backend,
            )

            assert run.status == "inconclusive"
            assert run.reproduced is False
            # Verify no model calls were made when reproduction failed!
            assert run.model_call_count == 0
            assert mock_nebius.generate_completion.call_count == 0


@pytest.mark.asyncio
async def test_orchestrator_handles_provider_error_gracefully(db_session, tmp_path):
    """Test orchestrator handles Nebius provider failures gracefully and transitions to failed state."""
    mock_nebius = AsyncMock()
    mock_nebius.generate_completion.side_effect = ProviderError(
        provider="Nebius",
        message="Authentication failed: invalid NEBIUS_API_KEY",
        status_code=401,
    )
    mock_tavily = AsyncMock()
    mock_backend = AsyncMock()
    mock_backend.backend_name = "mock_sandbox"

    # Baseline tests fail (defect reproduced)
    mock_backend.execute_tests.return_value = AsyncMock(
        exit_code=1, output="AssertionError: Defect"
    )

    request = RunCreateRequest(
        repository_url="https://github.com/VaibhavSoni24/ProofPatch",
        bug_title="Defect with failed AI auth",
        bug_description="Authentication failure test",
        mode="live",
        confirm_live_execution=True,
    )

    with patch("app.agents.orchestrator.clone_public_repository", return_value="ghi789"):
        with patch("app.agents.orchestrator.inspect_repository") as mock_inspect:
            mock_inspect.return_value = MagicMock(
                source_files=[], test_files=[], total_files=0, context_files_content={}
            )

            run = await execute_live_run(
                db=db_session,
                request=request,
                nebius_provider=mock_nebius,
                tavily_provider=mock_tavily,
                execution_backend=mock_backend,
            )

            assert run.status == "failed"
            assert "Authentication failed" in (run.error_message or "")
