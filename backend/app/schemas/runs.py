"""Run schemas for API requests, summaries, and details."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RunCreateRequest(BaseModel):
    """Payload to initiate a new repair run."""

    repository_url: str = Field(
        ..., description="Repository URL (or 'bundled:examples/buggy-python-service' for demo)"
    )
    bug_title: str = Field(..., min_length=3, max_length=256)
    bug_description: str = Field(..., min_length=10)
    reproduction_instructions: Optional[str] = None
    mode: Optional[str] = Field("demo", description="'demo' or 'live'")
    confirm_live_execution: Optional[bool] = Field(
        False, description="Explicit consent to spend API credits if in live mode"
    )


class StageEventResponse(BaseModel):
    """Chronological event logged during run stages."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    timestamp: datetime
    stage: str
    status: str
    message: str
    metadata_json: Optional[str] = None


class RunSummaryResponse(BaseModel):
    """Compact summary of a run for listing in dashboard/history."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    mode: str
    status: str
    repository_url: str
    bug_title: str
    reproduced: bool
    test_passed: bool
    verified: bool
    iteration_count: int


class RunDetailResponse(RunSummaryResponse):
    """Complete detail of a run including execution outputs and stages."""

    bug_description: str
    commit_hash: Optional[str] = None

    # Stage outputs
    reproduction_command: Optional[str] = None
    reproduction_exit_code: Optional[int] = None
    reproduction_output: Optional[str] = None

    diagnosis_summary: Optional[str] = None
    diagnosis_root_cause: Optional[str] = None

    patch_diff: Optional[str] = None
    modified_files: List[str] = []

    pre_patch_test_output: Optional[str] = None
    pre_patch_exit_code: Optional[int] = None
    post_patch_test_output: Optional[str] = None
    post_patch_exit_code: Optional[int] = None

    model_call_count: int = 0
    tavily_searches_count: int = 0
    error_message: Optional[str] = None

    events: List[StageEventResponse] = []


class PatchResponse(BaseModel):
    """Isolated view of the generated/applied patch."""

    run_id: str
    patch_diff: Optional[str] = None
    modified_files: List[str] = []
    applied: bool = False


class RunCancelResponse(BaseModel):
    """Response returned upon run cancellation."""

    run_id: str
    status: str
    message: str
