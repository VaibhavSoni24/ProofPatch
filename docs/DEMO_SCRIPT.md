# ProofPatch 2-Minute Demonstration Script

This script provides a concise, high-impact demonstration of ProofPatch for hackathon evaluators, showcasing the core value proposition: **verifiable evidence over ungrounded generation**.

---

## Act 1: The Problem (0:00 – 0:25)

**Visual**: ProofPatch Dashboard open in browser (`http://localhost:5173`). Clean dark-mode interface with global banner: `LOCAL DEMO MODE — zero external AI inference API calls, zero credit spend`.

> **Narrator**:
> "AI coding assistants can generate code in seconds, but a generated patch is not proof that a bug was fixed. Developers waste hours manually verifying whether an AI-proposed patch breaks tests, misses boundary conditions, or introduces regressions.
>
> Welcome to **ProofPatch — AI repairs you can verify**. Instead of an ungrounded chat interface, ProofPatch turns bug fixing into an observable, auditable engineering pipeline."

---

## Act 2: Triggering the Deterministic Demo (0:25 – 0:45)

**Visual**: Click the **Run Demo Repair** button in the top navbar.

> **Narrator**:
> "We'll click 'Run Demo Repair'. Notice this entire demonstration runs locally on an ordinary laptop with zero external API credits or cloud GPUs required.
>
> ProofPatch immediately spins up an isolated disposable workspace containing a real SaaS billing service with reported Issue #104: an off-by-one boundary defect where a 6-seat growth order incorrectly calculates at standard starter rates."

---

## Act 3: Observable Reproduction & Diagnosis (0:45 – 1:15)

**Visual**: The Run Details screen opens automatically. Click on the **Bug Reproduction** tab, then the **Diagnosis** tab.

> **Narrator**:
> "First, Stage 2: Bug Reproduction. ProofPatch doesn't just assume the bug exists. It executes `pytest tests -v` in the clean workspace. Look at the terminal output: `test_growth_tier_boundary_six_seats` failed with Exit Code 1. We now have ground-truth proof of the defect.
>
> Next, the Diagnosis stage isolates line 34 in `src/billing.py`: `if seats > 6 and seats <= 20:`. When seat count is exactly 6, the expression evaluates to False, causing an accidental fallback to Starter pricing."

---

## Act 4: Surgical Patch & Verification Pass (1:15 – 1:45)

**Visual**: Switch to the **Surgical Patch (Diff)** tab, then the **Test Comparison** tab, and finally **Independent Verification**.

> **Narrator**:
> "In Stage 5, ProofPatch synthesizes a minimal unified diff. Notice our patch safety engine validates that the diff contains no path traversals, touches only permitted source files, and stays well within byte caps.
>
> Look at the Test Comparison tab:
> In Phase 1, baseline tests failed with exit code 1.
> In Phase 2, after surgical patching, all 7 regression tests pass with Exit Code 0.
>
> But we don't stop there. Stage 9 is **Independent Verification**. A deterministic auditor checks that the diff is well-formed, only permitted files changed, the baseline defect was reproduced, regression tests passed, original repository was untouched, and all secrets were redacted."

---

## Act 5: Evidence Export & Production Readiness (1:45 – 2:00)

**Visual**: Switch to the **Audit Report Export** tab, click **Download Markdown**, then open the **Settings** view.

> **Narrator**:
> "ProofPatch produces a complete, cryptographically auditable Evidence Report available as downloadable Markdown and JSON artifacts.
>
> In Settings, you can see our production integrations: an OpenAI-compatible adapter for Nebius Token Factory ready to drive eligible NVIDIA open-source models, and an autonomous Tavily research adapter.
>
> ProofPatch: AI repairs you can verify. Built for the Nebius x NVIDIA Hackathon. Thank you!"
