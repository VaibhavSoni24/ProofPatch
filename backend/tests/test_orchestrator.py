"""Integration test for orchestrator with mocked providers and isolated local workspace."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.agents.orchestrator import execute_live_run
from app.providers.base import ProviderResponse, SearchResponse, SearchResultItem
from app.schemas.runs import RunCreateRequest


def test_orchestrator_live_workflow_mocked(db_session, tmp_path):
    """Test full multi-stage orchestrator flow with mocked AI and search providers."""
    # Source project
    project_root = Path(__file__).resolve().parent.parent.parent
    bundled_source = project_root / "examples" / "buggy-python-service"

    # Mock Nebius provider
    mock_nebius = MagicMock()

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

    # Mock Tavily provider
    mock_tavily = MagicMock()
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

    # Patch clone_public_repository to copy bundled_source into workspace
    def mock_clone(url, target_dir):
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(bundled_source, target_dir)
        return "abc123commit"

    with patch("app.agents.orchestrator.clone_public_repository", side_effect=mock_clone):
        run = execute_live_run(
            db=db_session,
            request=request,
            nebius_provider=mock_nebius,
            tavily_provider=mock_tavily,
        )

        assert run.status == "passed"
        assert run.reproduced is True
        assert run.test_passed is True
        assert run.verified is True
        assert run.commit_hash == "abc123commit"
        assert run.model_call_count == 2
        assert mock_nebius.generate_completion.call_count == 2
