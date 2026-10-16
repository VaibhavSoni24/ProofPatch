"""Database models for runs, stage events, and evidence reports."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class RunModel(Base):
    """Database representation of an autonomous bug repair run."""

    __tablename__ = "runs"

    id = Column(String(64), primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    mode = Column(String(16), default="demo", nullable=False)  # "demo" or "live"
    status = Column(
        String(32), default="queued", nullable=False
    )  # queued, running, passed, failed, partial, cancelled

    repository_url = Column(String(512), nullable=False)
    commit_hash = Column(String(64), nullable=True)
    bug_title = Column(String(256), nullable=False)
    bug_description = Column(Text, nullable=False)

    # Stage 3: Bug reproduction
    reproduction_command = Column(String(512), nullable=True)
    reproduction_exit_code = Column(Integer, nullable=True)
    reproduction_output = Column(Text, nullable=True)
    reproduced = Column(Boolean, default=False, nullable=False)

    # Stage 4: Diagnosis
    diagnosis_summary = Column(Text, nullable=True)
    diagnosis_root_cause = Column(Text, nullable=True)

    # Stage 6: Patch
    patch_diff = Column(Text, nullable=True)
    modified_files = Column(Text, nullable=True)  # JSON-encoded array

    # Stage 7: Test execution
    pre_patch_test_output = Column(Text, nullable=True)
    pre_patch_exit_code = Column(Integer, nullable=True)
    post_patch_test_output = Column(Text, nullable=True)
    post_patch_exit_code = Column(Integer, nullable=True)
    test_passed = Column(Boolean, default=False, nullable=False)

    # Stage 9: Verification
    verified = Column(Boolean, default=False, nullable=False)

    # Metrics
    iteration_count = Column(Integer, default=0, nullable=False)
    model_call_count = Column(Integer, default=0, nullable=False)
    tavily_searches_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    events = relationship(
        "StageEventModel",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="StageEventModel.id",
    )
    evidence = relationship(
        "EvidenceReportModel", back_populates="run", uselist=False, cascade="all, delete-orphan"
    )


class StageEventModel(Base):
    """Auditable timestamped events recorded during run execution."""

    __tablename__ = "stage_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    stage = Column(
        String(32), nullable=False
    )  # inspect, reproduce, diagnose, research, patch, test, iterate, verify, report
    status = Column(String(32), nullable=False)  # started, completed, failed, skipped
    message = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)

    run = relationship("RunModel", back_populates="events")


class EvidenceReportModel(Base):
    """Persisted evidence report containing full verifiable execution data."""

    __tablename__ = "evidence_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        String(64),
        ForeignKey("runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    evidence_json = Column(Text, nullable=False)
    evidence_markdown = Column(Text, nullable=False)

    run = relationship("RunModel", back_populates="evidence")
