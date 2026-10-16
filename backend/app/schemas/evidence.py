"""Evidence and verification schemas."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


class VerificationItem(BaseModel):
    """Specific independent verification check."""

    name: str
    status: Literal["PASSED", "FAILED", "NOT_RUN", "INCONCLUSIVE"]
    detail: str


class TestRecord(BaseModel):
    """Record of an actual test command execution."""

    stage: Literal["pre_patch", "post_patch", "reproduction"]
    command: str
    exit_code: int
    passed: bool
    output_summary: str


class EvidenceReportResponse(BaseModel):
    """Full verifiable audit report schema."""

    model_config = ConfigDict(from_attributes=True)

    run_id: str
    created_at: datetime
    mode: str
    status: str
    repository_url: str
    bug_title: str
    reproduced: bool
    tests_passed: bool
    verified: bool

    verification_checks: List[VerificationItem] = []
    tests: List[TestRecord] = []
    patch_diff: Optional[str] = None
    modified_files: List[str] = []
    tavily_research: Optional[Dict[str, Any]] = None

    markdown_report: str
