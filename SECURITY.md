# Security Policy

ProofPatch treats security, sandboxing, and safe code execution as top priorities. Because ProofPatch analyzes and executes code repairs, strict execution safeguards are enforced by design.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Architecture & Core Safeguards

1. **Credential Isolation**:
   - Provider credentials (`NEBIUS_API_KEY`, `TAVILY_API_KEY`) reside exclusively in backend environment configuration.
   - Frontend and API responses never expose or return secrets. All config endpoints return sanitized boolean statuses.
   - Credentials are automatically scrubbed and redacted from run logs, diffs, terminal outputs, and reports.

2. **Patch Safety & Path Traversal Protections**:
   - Every unified diff proposed by an AI model is strictly parsed and validated.
   - Path traversal sequences (`../`, absolute paths, drive letters) are rejected immediately.
   - Patch application is confined strictly to designated disposable workspace subdirectories.
   - Maximum patch sizes (`MAX_PATCH_BYTES`) are enforced to prevent Denial of Service.

3. **Code Execution Isolation**:
   - Code from external repositories is never executed directly in the host application process.
   - Docker container isolation is required for external repository execution, running without root privileges, without network access by default, and with bounded memory, CPU, and time limits.
   - No model-generated shell commands are ever directly executed. Only strictly allowlisted test runner invocations (`pytest`) with safe arguments are permitted.
   - Never mount host Docker sockets or host credentials into execution containers.

4. **Zero-Credit Demo Safety**:
   - The default mode (`PROOFPATCH_MODE=demo`) requires zero external credentials, zero internet access to model providers, and never incurs API costs.
   - Live runs require explicit confirmation and validation of configured models and keys.

## Reporting a Vulnerability

If you discover a security vulnerability in ProofPatch, please do NOT file a public issue.
Instead, send an email to: `vaibhavsoni280506@gmail.com` with:
- A description of the issue.
- Steps to reproduce or proof of concept.
- Affected components or versions.

We will acknowledge receipt within 48 hours and work on a prioritized fix.
