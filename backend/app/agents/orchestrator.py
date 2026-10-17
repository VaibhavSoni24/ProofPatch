"""Autonomous repair loop orchestrator executing live multi-stage repair workflow."""

import asyncio
import json
import shutil
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.patch_parser import validate_patch_security
from app.agents.prompts import (
    DIAGNOSIS_SYSTEM_PROMPT,
    PATCH_SYSTEM_PROMPT,
    REPAIR_SYSTEM_PROMPT,
    DiagnosisResult,
    build_diagnosis_user_prompt,
    build_patch_user_prompt,
)
from app.agents.verification import (
    classify_baseline_reproduction,
    perform_independent_verification,
)
from app.core.config import get_settings
from app.core.logging import logger
from app.db.models import RunModel
from app.providers.nebius import NebiusTokenFactoryProvider
from app.providers.tavily import TavilySearchProvider
from app.repositories.git import clone_public_repository, validate_repository_url
from app.repositories.inspection import inspect_repository
from app.repositories.security import compute_repository_manifest
from app.sandbox.base import BaseExecutionBackend
from app.sandbox.factory import get_execution_backend
from app.schemas.evidence import TestRecord
from app.schemas.runs import RunCreateRequest
from app.services.demo import log_stage_event
from app.services.evidence import persist_evidence_report

settings = get_settings()


def strip_markdown_fences(text: str) -> str:
    """Strip ```diff or ```json code fences if returned by model."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return cleaned


async def execute_live_run(
    db: Session,
    request: RunCreateRequest,
    existing_run_id: Optional[str] = None,
    nebius_provider: Optional[NebiusTokenFactoryProvider] = None,
    tavily_provider: Optional[TavilySearchProvider] = None,
    execution_backend: Optional[BaseExecutionBackend] = None,
) -> RunModel:
    """Execute the full autonomous repair workflow for an external repository."""
    run_id = existing_run_id or f"run_{uuid.uuid4().hex[:8]}"
    workspace_root = settings.get_workspace_dir()
    workspace_path = workspace_root / run_id
    pristine_path = workspace_root / f"pristine_{run_id}"

    nebius = nebius_provider or NebiusTokenFactoryProvider()
    tavily = tavily_provider or TavilySearchProvider()
    sandbox = execution_backend or get_execution_backend(mode="live")

    # 1. Initialize Run in DB
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        run = RunModel(
            id=run_id,
            mode="live",
            status="running",
            repository_url=request.repository_url,
            bug_title=request.bug_title,
            bug_description=request.bug_description,
            iteration_count=0,
            model_call_count=0,
            tavily_searches_count=0,
        )
        db.add(run)
        db.commit()

    try:
        # Stage 1: Repository Acquisition
        log_stage_event(
            db,
            run_id,
            "inspect",
            "started",
            f"Validating and cloning public repository: {request.repository_url}...",
        )
        validate_repository_url(request.repository_url)
        commit_hash = await asyncio.to_thread(
            clone_public_repository, request.repository_url, pristine_path
        )
        run.commit_hash = commit_hash
        db.commit()

        # Isolate run execution in a dedicated workspace copy
        if not pristine_path.exists():
            pristine_path.mkdir(parents=True, exist_ok=True)

        # Establish deterministic pristine repository baseline manifest before repair
        baseline_manifest = await asyncio.to_thread(compute_repository_manifest, pristine_path)

        if workspace_path.exists():
            shutil.rmtree(workspace_path)
        shutil.copytree(pristine_path, workspace_path, symlinks=False)

        # Stage 2: Inspection
        inspection = await asyncio.to_thread(inspect_repository, workspace_path)
        log_stage_event(
            db,
            run_id,
            "inspect",
            "completed",
            f"Cloned commit {commit_hash[:8]}. Found {len(inspection.source_files)} source and {len(inspection.test_files)} test files.",
            {"total_files": inspection.total_files},
        )

        # Stage 3: Bug Reproduction (Executed inside isolated sandbox)
        log_stage_event(
            db,
            run_id,
            "reproduce",
            "started",
            f"Executing baseline test suite inside isolated sandbox ({sandbox.backend_name})...",
        )
        repro_cmd = "pytest tests -v"
        repro_res = await sandbox.execute_tests(
            workspace_dir=workspace_path, timeout_seconds=settings.sandbox_timeout_seconds
        )

        run.reproduction_command = repro_cmd
        run.reproduction_exit_code = repro_res.exit_code
        run.reproduction_output = repro_res.output
        run.pre_patch_test_output = repro_res.output
        run.pre_patch_exit_code = repro_res.exit_code
        repro_status, repro_reason = classify_baseline_reproduction(
            exit_code=repro_res.exit_code,
            output=repro_res.output,
            bug_title=request.bug_title,
            bug_description=request.bug_description,
            reproduction_instructions=getattr(request, "reproduction_instructions", ""),
            timed_out=repro_res.timed_out,
        )

        run.reproduced = repro_status == "PASSED"
        db.commit()

        if repro_status != "PASSED":
            log_stage_event(
                db,
                run_id,
                "reproduce",
                "failed",
                f"Reproduction halted ({repro_status}): {repro_reason}",
                {"exit_code": repro_res.exit_code, "status": repro_status},
            )
            run.status = "inconclusive" if repro_status == "INCONCLUSIVE" else "failed"
            db.commit()

            # Perform independent verification audit reflecting the failure/inconclusiveness
            is_verified, checks = perform_independent_verification(
                patch_diff="",
                modified_files=[],
                pre_patch_exit_code=run.pre_patch_exit_code,
                post_patch_exit_code=None,
                pre_patch_output=run.pre_patch_test_output or "",
                post_patch_output="",
                workspace_dir=workspace_path,
                original_repo_dir=pristine_path if pristine_path.exists() else None,
                baseline_manifest=baseline_manifest if pristine_path.exists() else None,
                bug_title=request.bug_title,
                bug_description=request.bug_description,
                reproduction_instructions=getattr(request, "reproduction_instructions", ""),
                timed_out=repro_res.timed_out,
            )
            run.verified = False
            db.commit()

            test_records = [
                TestRecord(
                    stage="pre_patch",
                    command=repro_cmd,
                    exit_code=run.pre_patch_exit_code,
                    passed=(run.pre_patch_exit_code == 0)
                    if run.pre_patch_exit_code is not None
                    else None,
                    test_status=repro_status,
                    output_summary=repro_reason,
                ),
                TestRecord(
                    stage="post_patch",
                    command=repro_cmd,
                    exit_code=None,
                    passed=None,
                    test_status="NOT_RUN",
                    output_summary="Post-patch regression test skipped because baseline reproduction was not established.",
                ),
            ]
            persist_evidence_report(
                db=db,
                run=run,
                verification_checks=checks,
                tests=test_records,
                tavily_research=None,
            )
            log_stage_event(
                db,
                run_id,
                "report",
                "completed",
                f"Evidence report compiled reflecting baseline reproduction outcome ({repro_status}).",
            )
            return run

        log_stage_event(
            db,
            run_id,
            "reproduce",
            "completed",
            f"Defect reproduced! {repro_reason}",
            {"exit_code": repro_res.exit_code, "status": repro_status},
        )

        # Stage 4: Optional Research via Tavily
        tavily_data = None
        if settings.is_tavily_configured:
            log_stage_event(
                db,
                run_id,
                "research",
                "started",
                f"Executing Tavily research search for: '{request.bug_title}'...",
            )
            search_res = await tavily.search(request.bug_title, max_results=3)
            run.tavily_searches_count += 1
            db.commit()

            if search_res.results:
                tavily_data = {
                    "enabled": True,
                    "query": request.bug_title,
                    "results": [r.model_dump() for r in search_res.results],
                }
                log_stage_event(
                    db,
                    run_id,
                    "research",
                    "completed",
                    f"Retrieved {len(search_res.results)} external reference(s) from Tavily.",
                    {"results_count": len(search_res.results)},
                )
            else:
                log_stage_event(
                    db,
                    run_id,
                    "research",
                    "completed",
                    "Tavily search completed with zero additional references.",
                )
        else:
            log_stage_event(
                db,
                run_id,
                "research",
                "skipped",
                "External research skipped: Tavily is not configured or disabled.",
            )

        # Stage 5: Model-driven Diagnosis via Nebius Token Factory
        log_stage_event(
            db,
            run_id,
            "diagnose",
            "started",
            f"Querying Nebius model '{settings.nebius_model}' for root cause diagnosis...",
        )
        research_context = ""
        if tavily_data and tavily_data.get("results"):
            research_context = "\n".join(
                f"- {r['title']}: {r['content'][:300]} ({r['url']})" for r in tavily_data["results"]
            )

        diag_prompt = build_diagnosis_user_prompt(
            bug_title=request.bug_title,
            bug_description=request.bug_description,
            reproduction_output=run.reproduction_output or "",
            context_files=inspection.context_files_content,
            research_context=research_context,
        )

        diag_res = await nebius.generate_completion(
            messages=[
                {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
                {"role": "user", "content": diag_prompt},
            ],
            temperature=0.1,
        )
        run.model_call_count += 1
        db.commit()

        # Parse Diagnosis JSON
        cleaned_diag = strip_markdown_fences(diag_res.content)
        try:
            diag_obj = json.loads(cleaned_diag)
            diagnosis = DiagnosisResult(**diag_obj)
        except Exception:
            diagnosis = DiagnosisResult(
                problem_summary=request.bug_title,
                likely_root_cause=cleaned_diag[:500],
                relevant_files=inspection.source_files[:2],
                proposed_minimal_fix="Apply surgical correction based on failure trace.",
                potential_side_effects="Unknown",
            )

        run.diagnosis_summary = diagnosis.problem_summary
        run.diagnosis_root_cause = diagnosis.likely_root_cause
        db.commit()

        log_stage_event(
            db,
            run_id,
            "diagnose",
            "completed",
            f"Diagnosis completed: {diagnosis.problem_summary[:100]}...",
        )

        # Stage 6: Patch Generation via Nebius
        log_stage_event(
            db,
            run_id,
            "patch",
            "started",
            f"Requesting minimal unified diff from Nebius model '{settings.nebius_model}'...",
        )
        patch_prompt = build_patch_user_prompt(
            diagnosis=diagnosis,
            context_files=inspection.context_files_content,
        )

        patch_res = await nebius.generate_completion(
            messages=[
                {"role": "system", "content": PATCH_SYSTEM_PROMPT},
                {"role": "user", "content": patch_prompt},
            ],
            temperature=0.1,
        )
        run.model_call_count += 1
        db.commit()

        patch_diff = strip_markdown_fences(patch_res.content)
        validate_patch_security(patch_diff)
        modified = await sandbox.apply_patch(patch_diff, workspace_path)

        run.patch_diff = patch_diff
        run.modified_files = json.dumps(modified)
        run.iteration_count = 1
        db.commit()

        log_stage_event(
            db,
            run_id,
            "patch",
            "completed",
            f"Unified diff applied cleanly to {len(modified)} file(s): {', '.join(modified)}.",
            {"modified_files": modified},
        )

        # Stage 7 & 8: Bounded Repair Loop
        current_iteration = 1
        max_iterations = settings.max_patch_iterations

        while current_iteration <= max_iterations:
            log_stage_event(
                db,
                run_id,
                "test",
                "started",
                f"Executing regression tests inside sandbox ({sandbox.backend_name}, Iteration {current_iteration}/{max_iterations})...",
            )
            post_res = await sandbox.execute_tests(
                workspace_dir=workspace_path, timeout_seconds=settings.sandbox_timeout_seconds
            )
            run.post_patch_test_output = post_res.output
            run.post_patch_exit_code = post_res.exit_code
            run.test_passed = post_res.exit_code == 0
            db.commit()

            if run.test_passed:
                log_stage_event(
                    db,
                    run_id,
                    "test",
                    "completed",
                    f"Regression test suite PASSED on iteration {current_iteration} (exit code 0)!",
                )
                break
            else:
                log_stage_event(
                    db,
                    run_id,
                    "test",
                    "failed",
                    f"Iteration {current_iteration} failed with exit code {post_res.exit_code}.",
                )
                if current_iteration >= max_iterations:
                    break

                # Attempt repair iteration if model call limit allows
                if run.model_call_count >= settings.max_model_calls_per_run:
                    log_stage_event(
                        db,
                        run_id,
                        "iterate",
                        "skipped",
                        f"Stopping repair loop: reached max model calls limit ({settings.max_model_calls_per_run}).",
                    )
                    break

                current_iteration += 1
                run.iteration_count = current_iteration
                log_stage_event(
                    db,
                    run_id,
                    "iterate",
                    "started",
                    f"Initiating repair iteration {current_iteration}: prompting model with test failure trace...",
                )

                repair_prompt = f"""### Failed Patch:
```diff
{run.patch_diff}
```

### Pytest Failure Trace:
```text
{post_res.output[:4000]}
```

Generate a revised, corrected unified diff to fix this error."""

                repair_res = await nebius.generate_completion(
                    messages=[
                        {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
                        {"role": "user", "content": repair_prompt},
                    ],
                    temperature=0.1,
                )
                run.model_call_count += 1
                db.commit()

                revised_diff = strip_markdown_fences(repair_res.content)
                validate_patch_security(revised_diff)
                modified = await sandbox.apply_patch(revised_diff, workspace_path)
                run.patch_diff = revised_diff
                run.modified_files = json.dumps(modified)
                db.commit()

        # Stage 9: Independent Verification
        log_stage_event(
            db,
            run_id,
            "verify",
            "started",
            "Executing independent verification audit against actual execution outputs...",
        )
        is_verified, checks = perform_independent_verification(
            patch_diff=run.patch_diff or "",
            modified_files=json.loads(run.modified_files) if run.modified_files else [],
            pre_patch_exit_code=run.pre_patch_exit_code,
            post_patch_exit_code=run.post_patch_exit_code,
            pre_patch_output=run.pre_patch_test_output or "",
            post_patch_output=run.post_patch_test_output or "",
            workspace_dir=workspace_path,
            original_repo_dir=pristine_path if pristine_path.exists() else None,
            baseline_manifest=baseline_manifest if pristine_path.exists() else None,
            bug_title=request.bug_title,
            bug_description=request.bug_description,
            reproduction_instructions=getattr(request, "reproduction_instructions", ""),
            timed_out=repro_res.timed_out,
        )

        run.verified = is_verified
        run.status = "passed" if (run.test_passed and is_verified) else "failed"
        db.commit()

        log_stage_event(
            db,
            run_id,
            "verify",
            "completed",
            f"Verification audit concluded with verdict: {'VERIFIED' if is_verified else 'FAILED'}.",
            {"checks": [c.model_dump() for c in checks]},
        )

        # Stage 10: Persistent Evidence Report
        log_stage_event(
            db, run_id, "report", "started", "Compiling final auditable evidence report..."
        )
        test_records = [
            TestRecord(
                stage="pre_patch",
                command="pytest tests -v",
                exit_code=run.pre_patch_exit_code,
                passed=(run.pre_patch_exit_code == 0)
                if run.pre_patch_exit_code is not None
                else None,
                test_status="FAILED"
                if run.pre_patch_exit_code not in (0, None)
                else ("PASSED" if run.pre_patch_exit_code == 0 else "NOT_RUN"),
                output_summary="Baseline test failure reproducing reported defect.",
            ),
            TestRecord(
                stage="post_patch",
                command="pytest tests -v",
                exit_code=run.post_patch_exit_code,
                passed=run.test_passed if run.post_patch_exit_code is not None else None,
                test_status="PASSED"
                if run.test_passed
                else ("FAILED" if run.post_patch_exit_code is not None else "NOT_RUN"),
                output_summary="Post-patch regression test outcome.",
            ),
        ]
        persist_evidence_report(
            db=db,
            run=run,
            verification_checks=checks,
            tests=test_records,
            tavily_research=tavily_data,
        )
        log_stage_event(
            db,
            run_id,
            "report",
            "completed",
            f"Evidence report compiled and persisted for run {run_id}.",
        )

        return run

    except Exception as exc:
        logger.error("Live repair run failed: %s", exc, exc_info=True)
        run.status = "failed"
        run.error_message = str(exc)
        db.commit()
        log_stage_event(
            db,
            run_id,
            "error",
            "failed",
            f"Live repair terminated prematurely: {str(exc)}",
        )
        return run

    finally:
        # Guarantee sandbox cleanup
        try:
            await sandbox.cleanup()
        except Exception as cleanup_exc:
            logger.warning("Error during sandbox cleanup: %s", cleanup_exc)

        # Cleanup pristine baseline directory
        if pristine_path.exists():
            try:
                shutil.rmtree(pristine_path, ignore_errors=True)
            except Exception as rmtree_err:
                logger.debug("Error cleaning up pristine path %s: %s", pristine_path, rmtree_err)
