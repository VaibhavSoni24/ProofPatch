"""Unit and integration tests for Run management endpoints."""


def test_health_check(client):
    """Verify health endpoint works cleanly without external calls."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "ProofPatch"
    assert data["mode"] == "demo"


def test_empty_runs_list(client):
    """Verify listing runs initially returns an empty list."""
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_trigger_demo_run(client):
    """Test triggering deterministic demo via API."""
    response = client.post("/api/runs/demo")
    assert response.status_code == 201
    data = response.json()

    assert data["mode"] == "demo"
    assert data["status"] == "passed"
    assert data["reproduced"] is True
    assert data["test_passed"] is True
    assert data["verified"] is True
    assert "src/billing.py" in data["modified_files"]
    assert len(data["events"]) >= 5

    run_id = data["id"]

    # Verify retrieval
    get_res = client.get(f"/api/runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == run_id

    # Verify patch endpoint
    patch_res = client.get(f"/api/runs/{run_id}/patch")
    assert patch_res.status_code == 200
    assert "src/billing.py" in patch_res.json()["modified_files"]

    # Verify evidence endpoint
    evidence_res = client.get(f"/api/runs/{run_id}/evidence")
    assert evidence_res.status_code == 200
    ev_data = evidence_res.json()
    assert ev_data["verified"] is True
    assert len(ev_data["verification_checks"]) >= 5
    assert "ProofPatch Verification Report" in ev_data["markdown_report"]


def test_unknown_run_returns_404(client):
    """Verify 404 response for non-existent run ID."""
    response = client.get("/api/runs/non-existent-run-id")
    assert response.status_code == 404
    body = response.json()
    msg = body.get("detail") or body.get("error") or ""
    assert "not found" in msg.lower()


def test_live_run_safeguards_missing_consent(client):
    """Verify live run is rejected when user confirmation is false."""
    payload = {
        "repository_url": "https://github.com/example/repo",
        "bug_title": "Fix something",
        "bug_description": "A long enough description of the defect to pass validation.",
        "mode": "live",
        "confirm_live_execution": False,
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 400
    assert "explicit user confirmation" in response.json()["detail"].lower()
