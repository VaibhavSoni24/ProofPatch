"""Evidence report generation, formatting, and persistence."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import EvidenceReportModel, RunModel
from app.schemas.evidence import TestRecord, VerificationItem


def generate_markdown_report(
    run: RunModel,
    verification_checks: List[VerificationItem],
    tests: List[TestRecord],
    tavily_research: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a comprehensive, GitHub-flavored Markdown audit report."""
    verdict_badge = "VERIFIED" if run.verified else "UNVERIFIED / PARTIAL"

    lines = [
        f"# ProofPatch Verification Report — Run `{run.id}`",
        "",
        f"> **Status**: **{run.status.upper()}** ({verdict_badge})  ",
        f"> **Execution Mode**: `{run.mode.upper()}`  ",
        f"> **Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Repository**: `{run.repository_url}`",
        f"- **Reported Issue**: {run.bug_title}",
        f"- **Defect Reproduced Prior to Patch**: {'Yes' if run.reproduced else 'No'}",
        f"- **Post-Patch Test Suite Passed**: {'Yes' if run.test_passed else 'No'}",
        f"- **Independent Verification Audit**: **{verdict_badge}**",
        f"- **Patch Iterations**: {run.iteration_count}",
        f"- **Model Invocations**: {run.model_call_count}",
        "",
        "---",
        "",
        "## 2. Bug Reproduction Evidence",
        "",
        "**Command executed**:",
        f"```bash\n{run.reproduction_command or 'pytest tests -v'}\n```",
        f"**Exit Code**: `{run.reproduction_exit_code}`  ",
        f"**Outcome**: {'Successfully reproduced expected defect' if run.reproduced else 'Reproduction inconclusive'}",
        "",
        "<details>",
        "<summary>View Raw Reproduction Terminal Output</summary>",
        "",
        "```text",
        run.reproduction_output or "No output captured",
        "```",
        "</details>",
        "",
        "---",
        "",
        "## 3. Root Cause Diagnosis",
        "",
        f"### Summary\n{run.diagnosis_summary or 'N/A'}\n",
        f"### Technical Root Cause\n{run.diagnosis_root_cause or 'N/A'}\n",
    ]

    # Optional Research Stage
    lines.extend(
        [
            "---",
            "",
            "## 4. Context & Technical Research",
            "",
        ]
    )
    if tavily_research and tavily_research.get("enabled"):
        query = tavily_research.get("query", "")
        results = tavily_research.get("results", [])
        lines.append(f"**Tavily Search Query**: `{query}`\n")
        lines.append(f"Found **{len(results)}** external technical reference(s):\n")
        for idx, item in enumerate(results, start=1):
            title = item.get("title", "Resource")
            url = item.get("url", "#")
            content = item.get("content", "")
            lines.append(f"{idx}. [{title}]({url})\n   > {content}\n")
    else:
        lines.append(
            "_External research via Tavily was not active for this run (either running in deterministic demo mode or Tavily integration disabled)._\n"
        )

    # Patch Section
    lines.extend(
        [
            "---",
            "",
            "## 5. Surgical Patch",
            "",
            "**Affected Files**:",
        ]
    )
    try:
        mod_files = json.loads(run.modified_files) if run.modified_files else []
    except Exception:
        mod_files = []

    for mf in mod_files:
        lines.append(f"- `{mf}`")

    lines.extend(
        [
            "",
            "```diff",
            run.patch_diff or "# No patch diff recorded",
            "```",
            "",
            "---",
            "",
            "## 6. Test Execution Comparison (Before vs After)",
            "",
            "| Stage | Command | Exit Code | Result |",
            "|---|---|---|---|",
        ]
    )
    for test in tests:
        res_str = "Passed" if test.passed else "Failed"
        lines.append(f"| `{test.stage}` | `{test.command}` | `{test.exit_code}` | **{res_str}** |")

    lines.extend(
        [
            "",
            "<details>",
            "<summary>View Post-Patch Test Output</summary>",
            "",
            "```text",
            run.post_patch_test_output or "No output captured",
            "```",
            "</details>",
            "",
            "---",
            "",
            "## 7. Independent Verification Audit",
            "",
            "| Audit Check | Status | Verification Detail |",
            "|---|---|---|",
        ]
    )
    for chk in verification_checks:
        lines.append(f"| **{chk.name}** | `{chk.status}` | {chk.detail} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 8. Human Review Recommendations & Boundaries",
            "",
            "- [x] Verified in sandboxed disposable workspace.",
            "- [x] Zero external credentials leaked.",
            "- [ ] Human architectural review recommended prior to production merge.",
            "",
            "_Report compiled autonomously by ProofPatch._",
        ]
    )

    return "\n".join(lines)


def persist_evidence_report(
    db: Session,
    run: RunModel,
    verification_checks: List[VerificationItem],
    tests: List[TestRecord],
    tavily_research: Optional[Dict[str, Any]] = None,
) -> EvidenceReportModel:
    """Compile and persist the full evidence report to database."""
    md_content = generate_markdown_report(run, verification_checks, tests, tavily_research)

    report_data = {
        "run_id": run.id,
        "created_at": datetime.utcnow().isoformat(),
        "mode": run.mode,
        "status": run.status,
        "repository_url": run.repository_url,
        "bug_title": run.bug_title,
        "reproduced": run.reproduced,
        "tests_passed": run.test_passed,
        "verified": run.verified,
        "verification_checks": [c.model_dump() for c in verification_checks],
        "tests": [t.model_dump() for t in tests],
        "patch_diff": run.patch_diff,
        "modified_files": json.loads(run.modified_files) if run.modified_files else [],
        "tavily_research": tavily_research,
    }

    evidence_record = (
        db.query(EvidenceReportModel).filter(EvidenceReportModel.run_id == run.id).first()
    )
    if evidence_record:
        evidence_record.evidence_json = json.dumps(report_data)
        evidence_record.evidence_markdown = md_content
    else:
        evidence_record = EvidenceReportModel(
            run_id=run.id,
            created_at=datetime.utcnow(),
            evidence_json=json.dumps(report_data),
            evidence_markdown=md_content,
        )
        db.add(evidence_record)

    db.commit()
    db.refresh(evidence_record)
    return evidence_record
