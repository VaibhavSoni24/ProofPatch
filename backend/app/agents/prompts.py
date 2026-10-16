"""Strict system and user prompt definitions for model-driven diagnosis and patching."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class DiagnosisResult(BaseModel):
    """Structured output expected from diagnosis model."""

    problem_summary: str
    likely_root_cause: str
    relevant_files: List[str]
    proposed_minimal_fix: str
    potential_side_effects: str


DIAGNOSIS_SYSTEM_PROMPT = """You are ProofPatch, an expert autonomous debugging and verification agent.
Your task is to analyze a software defect report, inspect repository code and failing test outputs, and identify the root cause.
You must respond with a strict, valid JSON object containing:
{
  "problem_summary": "Concise explanation of the bug",
  "likely_root_cause": "Detailed technical analysis of the exact failure mechanism and line(s)",
  "relevant_files": ["list", "of", "affected", "relative/paths.py"],
  "proposed_minimal_fix": "Explanation of the minimal surgical code correction",
  "potential_side_effects": "Any potential regressions or risks"
}
Do NOT include markdown formatting or extra text outside the JSON object.
"""

PATCH_SYSTEM_PROMPT = """You are ProofPatch, an autonomous code repair agent.
Your task is to generate a minimal, surgical unified diff that resolves the diagnosed defect.

RULES:
1. Output ONLY a valid unified diff starting with '--- a/<path>' and '+++ b/<path>'.
2. Provide valid hunk headers: @@ -start,count +start,count @@.
3. Keep changes minimal and focused strictly on fixing the bug.
4. Do NOT include markdown code blocks, conversational text, explanations, or quotes.
5. Target only permitted source files. Never touch .git, .env, or configuration outside the scope.
"""

REPAIR_SYSTEM_PROMPT = """You are ProofPatch. A previously applied patch did not pass all regression tests.
Analyze the test failure output and previous diff, then generate a revised, corrected unified diff.
Output ONLY the unified diff with no commentary.
"""


def build_diagnosis_user_prompt(
    bug_title: str,
    bug_description: str,
    reproduction_output: str,
    context_files: Dict[str, str],
    research_context: Optional[str] = None,
) -> str:
    """Construct structured context for diagnosis."""
    files_str = "\n\n".join(
        f"--- File: {path} ---\n{content[:4000]}" for path, content in context_files.items()
    )

    research_section = (
        f"\n\n### External Technical Research Context:\n{research_context}\n"
        if research_context
        else ""
    )

    return f"""### Reported Issue:
Title: {bug_title}
Description: {bug_description}

### Baseline Test Output (Reproduced Defect):
```text
{reproduction_output[:6000]}
```
{research_section}
### Repository Files:
{files_str}

Analyze the problem and return the requested JSON object."""


def build_patch_user_prompt(
    diagnosis: DiagnosisResult,
    context_files: Dict[str, str],
) -> str:
    """Construct prompt requesting unified diff patch."""
    files_str = "\n\n".join(
        f"--- File: {path} ---\n{content[:4000]}"
        for path, content in context_files.items()
        if path in diagnosis.relevant_files or not diagnosis.relevant_files
    )

    return f"""### Diagnosed Problem:
{diagnosis.problem_summary}

### Root Cause:
{diagnosis.likely_root_cause}

### Proposed Fix:
{diagnosis.proposed_minimal_fix}

### Source Files to Patch:
{files_str}

Generate the minimal unified diff to fix this bug."""
