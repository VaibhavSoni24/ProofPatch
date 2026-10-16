"""Run lifecycle and retrieval service."""

import json
from typing import List

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    InvalidStateTransitionError,
    RunNotFoundError,
)
from app.db.models import EvidenceReportModel, RunModel, StageEventModel
from app.schemas.evidence import EvidenceReportResponse
from app.schemas.runs import (
    PatchResponse,
    RunCancelResponse,
    RunDetailResponse,
    RunSummaryResponse,
    StageEventResponse,
)

settings = get_settings()


def list_runs(db: Session, limit: int = 50, offset: int = 0) -> List[RunSummaryResponse]:
    """Retrieve chronologically ordered list of repair runs."""
    records = (
        db.query(RunModel).order_by(RunModel.created_at.desc()).offset(offset).limit(limit).all()
    )
    return [RunSummaryResponse.model_validate(r) for r in records]


def get_run_by_id(db: Session, run_id: str) -> RunModel:
    """Retrieve run record or raise RunNotFoundError."""
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise RunNotFoundError(run_id)
    return run


def get_run_details(db: Session, run_id: str) -> RunDetailResponse:
    """Retrieve comprehensive details of a specific run."""
    run = get_run_by_id(db, run_id)
    events = (
        db.query(StageEventModel)
        .filter(StageEventModel.run_id == run_id)
        .order_by(StageEventModel.id.asc())
        .all()
    )
    event_responses = [StageEventResponse.model_validate(e) for e in events]

    try:
        modified_files = json.loads(run.modified_files) if run.modified_files else []
    except Exception:
        modified_files = []

    return RunDetailResponse(
        id=run.id,
        created_at=run.created_at,
        updated_at=run.updated_at,
        mode=run.mode,
        status=run.status,
        repository_url=run.repository_url,
        commit_hash=run.commit_hash,
        bug_title=run.bug_title,
        bug_description=run.bug_description,
        reproduction_command=run.reproduction_command,
        reproduction_exit_code=run.reproduction_exit_code,
        reproduction_output=run.reproduction_output,
        reproduced=run.reproduced,
        diagnosis_summary=run.diagnosis_summary,
        diagnosis_root_cause=run.diagnosis_root_cause,
        patch_diff=run.patch_diff,
        modified_files=modified_files,
        pre_patch_test_output=run.pre_patch_test_output,
        pre_patch_exit_code=run.pre_patch_exit_code,
        post_patch_test_output=run.post_patch_test_output,
        post_patch_exit_code=run.post_patch_exit_code,
        test_passed=run.test_passed,
        verified=run.verified,
        iteration_count=run.iteration_count,
        model_call_count=run.model_call_count,
        tavily_searches_count=run.tavily_searches_count,
        error_message=run.error_message,
        events=event_responses,
    )


def get_run_patch(db: Session, run_id: str) -> PatchResponse:
    """Retrieve isolated patch and affected files for a run."""
    run = get_run_by_id(db, run_id)
    try:
        modified_files = json.loads(run.modified_files) if run.modified_files else []
    except Exception:
        modified_files = []

    return PatchResponse(
        run_id=run.id,
        patch_diff=run.patch_diff,
        modified_files=modified_files,
        applied=bool(run.patch_diff and run.test_passed),
    )


def get_run_evidence(db: Session, run_id: str) -> EvidenceReportResponse:
    """Retrieve full persisted evidence report for a run."""
    run = get_run_by_id(db, run_id)
    evidence_record = (
        db.query(EvidenceReportModel).filter(EvidenceReportModel.run_id == run_id).first()
    )
    if not evidence_record:
        raise RunNotFoundError(f"Evidence report for run '{run_id}' not yet generated")

    raw_data = json.loads(evidence_record.evidence_json)
    return EvidenceReportResponse(
        run_id=run.id,
        created_at=evidence_record.created_at,
        mode=run.mode,
        status=run.status,
        repository_url=run.repository_url,
        bug_title=run.bug_title,
        reproduced=run.reproduced,
        tests_passed=run.test_passed,
        verified=run.verified,
        verification_checks=raw_data.get("verification_checks", []),
        tests=raw_data.get("tests", []),
        patch_diff=run.patch_diff,
        modified_files=raw_data.get("modified_files", []),
        tavily_research=raw_data.get("tavily_research"),
        markdown_report=evidence_record.evidence_markdown,
    )


def cancel_run(db: Session, run_id: str) -> RunCancelResponse:
    """Cancel an active run."""
    run = get_run_by_id(db, run_id)
    if run.status in ("passed", "failed", "cancelled"):
        raise InvalidStateTransitionError(run.status, "cancelled")

    run.status = "cancelled"
    run.error_message = "Cancelled by user"
    db.commit()

    return RunCancelResponse(
        run_id=run.id,
        status="cancelled",
        message=f"Run '{run_id}' was successfully cancelled.",
    )
