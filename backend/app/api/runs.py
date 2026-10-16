"""Run management API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    InvalidStateTransitionError,
    RunNotFoundError,
)
from app.db.session import get_db
from app.schemas.evidence import EvidenceReportResponse
from app.schemas.runs import (
    PatchResponse,
    RunCancelResponse,
    RunCreateRequest,
    RunDetailResponse,
    RunSummaryResponse,
    StageEventResponse,
)
from app.services.demo import execute_demo_run
from app.services.runs import (
    cancel_run,
    get_run_details,
    get_run_evidence,
    get_run_patch,
    list_runs,
)

router = APIRouter(prefix="/runs", tags=["Runs"])
settings = get_settings()


@router.get("", response_model=List[RunSummaryResponse])
def get_all_runs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve chronologically ordered list of recent bug repair runs."""
    return list_runs(db, limit=limit, offset=offset)


@router.post("/demo", response_model=RunDetailResponse, status_code=status.HTTP_201_CREATED)
def trigger_demo_run(db: Session = Depends(get_db)):
    """Execute the deterministic, zero-credential local demo workflow."""
    run = execute_demo_run(db)
    return get_run_details(db, run.id)


@router.post("", response_model=RunDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_run(request: RunCreateRequest, db: Session = Depends(get_db)):
    """Initiate a repair run (validating safety, mode, and explicit user consent)."""
    # Demo request or bundled repository
    if (
        request.mode == "demo"
        or request.repository_url.startswith("bundled:")
        or not request.repository_url
    ):
        run = execute_demo_run(db)
        return get_run_details(db, run.id)

    # Live Mode validation safeguards
    if request.mode == "live":
        if not request.confirm_live_execution:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Live execution requires explicit user confirmation (confirm_live_execution=true) to prevent unexpected credit consumption.",
            )

        if not settings.is_nebius_configured:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nebius Token Factory is not configured. Please supply NEBIUS_API_KEY and an eligible NEBIUS_MODEL in your environment.",
            )

        # External repository check
        if not settings.allow_external_repositories:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="External repository execution is disabled by default in safety configuration (ALLOW_EXTERNAL_REPOSITORIES=false).",
            )

        # For live runs with external repos, the orchestrator handles live execution
        from app.agents.orchestrator import execute_live_run

        run = await execute_live_run(db, request)
        return get_run_details(db, run.id)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown execution mode '{request.mode}'. Supported modes: 'demo', 'live'.",
    )


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Retrieve execution details, output logs, and stages for a specific run."""
    try:
        return get_run_details(db, run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get("/{run_id}/events", response_model=List[StageEventResponse])
def get_run_events(run_id: str, db: Session = Depends(get_db)):
    """Retrieve timestamped stage events recorded during the run."""
    run_details = get_run(run_id, db)
    return run_details.events


@router.get("/{run_id}/patch", response_model=PatchResponse)
def get_patch(run_id: str, db: Session = Depends(get_db)):
    """Retrieve unified diff and modified files generated for this run."""
    try:
        return get_run_patch(db, run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get("/{run_id}/evidence", response_model=EvidenceReportResponse)
def get_evidence(run_id: str, db: Session = Depends(get_db)):
    """Retrieve downloadable evidence report and audit trail."""
    try:
        return get_run_evidence(db, run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.post("/{run_id}/cancel", response_model=RunCancelResponse)
def cancel_active_run(run_id: str, db: Session = Depends(get_db)):
    """Cancel an active run."""
    try:
        return cancel_run(db, run_id)
    except (RunNotFoundError, InvalidStateTransitionError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
