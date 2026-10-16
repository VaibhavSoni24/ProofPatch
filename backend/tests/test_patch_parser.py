"""Unit tests for patch parser, security checks, and applier."""

import pytest

from app.agents.patch_parser import (
    apply_patch_to_workspace,
    extract_diff_targets,
    validate_patch_security,
)
from app.core.errors import PatchApplicationError, SecurityViolationError


def test_extract_diff_targets():
    """Verify target file extraction from unified diff headers."""
    diff = """--- a/src/math.py
+++ b/src/math.py
@@ -1,3 +1,3 @@
-def add(a, b): return a - b
+def add(a, b): return a + b
"""
    targets = extract_diff_targets(diff)
    assert targets == ["src/math.py"]


def test_reject_empty_patch():
    """Verify empty patch is rejected."""
    with pytest.raises(PatchApplicationError):
        validate_patch_security("")


def test_reject_oversized_patch():
    """Verify patch exceeding max_bytes limit is rejected."""
    oversized = "--- a/f.py\n+++ b/f.py\n" + ("+" * 200)
    with pytest.raises(SecurityViolationError):
        validate_patch_security(oversized, max_bytes=100)


def test_reject_path_traversal():
    """Verify relative traversal sequences are strictly rejected."""
    diff = """--- a/../../secret.txt
+++ b/../../secret.txt
@@ -1 +1 @@
-old
+new
"""
    with pytest.raises(SecurityViolationError):
        validate_patch_security(diff)


def test_reject_prohibited_files():
    """Verify attempts to modify .env or .git are rejected."""
    diff = """--- a/.env
+++ b/.env
@@ -1 +1 @@
-APP_NAME=Old
+APP_NAME=New
"""
    with pytest.raises(SecurityViolationError):
        validate_patch_security(diff)


def test_apply_patch_cleanly(tmp_path):
    """Test applying a valid diff to a real file on disk."""
    code_file = tmp_path / "hello.py"
    code_file.write_text("def hello():\n    return 'bad'\n", encoding="utf-8")

    diff = """--- a/hello.py
+++ b/hello.py
@@ -1,2 +1,2 @@
 def hello():
-    return 'bad'
+    return 'good'
"""
    modified = apply_patch_to_workspace(tmp_path, diff)
    assert modified == ["hello.py"]
    assert code_file.read_text(encoding="utf-8") == "def hello():\n    return 'good'\n"
