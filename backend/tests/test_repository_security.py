"""Tests for repository security controls, path containment, symlink rejection, and secret exclusion."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.agents.patch_parser import apply_patch_to_workspace
from app.core.errors import SecurityViolationError
from app.repositories.inspection import inspect_repository
from app.repositories.security import (
    is_sensitive_file,
    safe_walk_repository,
    validate_path_containment,
)


def _can_create_symlinks() -> bool:
    """Check if the current OS/environment permissions permit creating symlinks."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "src.txt"
        src.write_text("test", encoding="utf-8")
        link = Path(td) / "link.txt"
        try:
            link.symlink_to(src)
            return True
        except (OSError, NotImplementedError):
            return False


CAN_SYMLINK = _can_create_symlinks()


def test_symlink_pointing_outside_workspace_rejected(tmp_path):
    """Verify that a symlink pointing to an external file outside the workspace is rejected."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    external_secret = tmp_path / "external_secret.txt"
    external_secret.write_text("SUPER_SECRET_HOST_DATA", encoding="utf-8")

    link_path = ws / "evil_link.txt"
    if CAN_SYMLINK:
        link_path.symlink_to(external_secret)

        with pytest.raises(SecurityViolationError, match="Symbolic links are strictly prohibited"):
            validate_path_containment(link_path, ws)

        # safe_walk_repository skips symlinks without reading
        entries = list(safe_walk_repository(ws, fail_on_limits=True))
        assert len(entries) == 0
    else:
        # Mock is_symlink behavior on platforms where symlinks cannot be created without admin
        with patch.object(Path, "is_symlink", return_value=True):
            with pytest.raises(
                SecurityViolationError, match="Symbolic links are strictly prohibited"
            ):
                validate_path_containment(link_path, ws)


def test_nested_symlink_directory_rejected(tmp_path):
    """Verify that a nested symlink directory attempting path traversal is pruned."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    secret_dir = tmp_path / "secret_folder"
    secret_dir.mkdir()
    (secret_dir / "target.py").write_text("secret_code = True", encoding="utf-8")

    nested_dir = ws / "sub"
    if CAN_SYMLINK:
        nested_dir.symlink_to(secret_dir, target_is_directory=True)
        # safe_walk_repository must not traverse into nested_dir
        entries = list(safe_walk_repository(ws, fail_on_limits=True))
        assert len(entries) == 0
    else:
        with patch.object(Path, "is_symlink", return_value=True):
            with pytest.raises(
                SecurityViolationError, match="Symbolic links are strictly prohibited"
            ):
                validate_path_containment(nested_dir / "target.py", ws)


def test_secret_bearing_file_excluded(tmp_path):
    """Verify that sensitive files (.env, private keys, cloud credentials) are excluded."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / ".env").write_text("DATABASE_PASSWORD=secret", encoding="utf-8")
    (ws / ".env.production").write_text("KEY=prod_val", encoding="utf-8")
    (ws / "id_rsa").write_text("-----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")
    (ws / "cert.key").write_text("PRIVATE_KEY_DATA", encoding="utf-8")
    (ws / "cert.pem").write_text("CERT_DATA", encoding="utf-8")
    (ws / ".git-credentials").write_text("https://user:pass@github.com", encoding="utf-8")
    (ws / "service_account.json").write_text('{"private_key": "xxx"}', encoding="utf-8")

    # None of these files should be returned by safe_walk_repository
    entries = list(safe_walk_repository(ws, fail_on_limits=True))
    assert len(entries) == 0

    # is_sensitive_file checks
    for fname in [".env", ".env.local", "id_ed25519", "cert.pem", "cert.key", ".git-credentials"]:
        is_sec, _ = is_sensitive_file(ws / fname)
        assert is_sec is True


def test_allowed_config_template_transfers(tmp_path):
    """Verify that non-secret configuration templates (.env.example) are permitted."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    tmpl = ws / ".env.example"
    tmpl.write_text("PORT=8000\nDEBUG=false\nDB_HOST=localhost\n", encoding="utf-8")

    is_sec, reason = is_sensitive_file(tmpl)
    assert is_sec is False
    assert "Permitted" in reason

    entries = list(safe_walk_repository(ws, fail_on_limits=True))
    assert len(entries) == 1
    assert entries[0].rel_path == ".env.example"


def test_allowed_config_template_with_secrets_rejected(tmp_path):
    """Verify that configuration templates containing actual live secret patterns are rejected."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    tmpl = ws / ".env.example"
    # Contains a bearer token pattern
    tmpl.write_text(
        "API_KEY=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token\n",
        encoding="utf-8",
    )

    is_sec, reason = is_sensitive_file(tmpl)
    assert is_sec is True
    assert "credential patterns" in reason


def test_normal_in_workspace_file_transfers(tmp_path):
    """Verify that ordinary source code files inside workspace transfer without issue."""
    ws = tmp_path / "workspace"
    (ws / "src").mkdir(parents=True)
    src_file = ws / "src" / "main.py"
    src_file.write_text("print('hello world')", encoding="utf-8")

    entries = list(safe_walk_repository(ws, fail_on_limits=True))
    assert len(entries) == 1
    assert entries[0].rel_path == "src/main.py"
    assert entries[0].size_bytes == len(b"print('hello world')")


def test_unreadable_or_inaccessible_file_handled_defensively(tmp_path):
    """Verify unexpected filesystem stat errors on files are handled defensively."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    normal_file = ws / "ok.py"
    normal_file.write_text("x = 1", encoding="utf-8")

    with patch.object(Path, "stat", side_effect=PermissionError("Access denied")):
        entries = list(safe_walk_repository(ws, fail_on_limits=False))
        # Skips inaccessible file safely
        assert len(entries) == 0


def test_symlink_creation_unavailable_graceful_handling(tmp_path):
    """Verify safe traversal functions seamlessly even if platform cannot create symlinks."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "app.py").write_text("print(1)", encoding="utf-8")

    # Mock is_symlink raising OSError (simulating platforms with restricted symlink syscalls)
    with patch.object(Path, "is_symlink", return_value=False):
        entries = list(safe_walk_repository(ws, fail_on_limits=True))
        assert len(entries) == 1
        assert entries[0].rel_path == "app.py"


def test_patch_application_rejects_symlink_target(tmp_path):
    """Verify patch application rejects modifying files that are symbolic links."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    real_file = tmp_path / "outside.py"
    real_file.write_text("original_content = True\n", encoding="utf-8")

    symlink_file = ws / "target.py"
    diff = """--- a/target.py
+++ b/target.py
@@ -1 +1 @@
-original_content = True
+original_content = False
"""
    if CAN_SYMLINK:
        symlink_file.symlink_to(real_file)
        with pytest.raises(SecurityViolationError, match="Symbolic links are strictly prohibited"):
            apply_patch_to_workspace(ws, diff)
        # External file must NOT be modified
        assert real_file.read_text(encoding="utf-8") == "original_content = True\n"
    else:
        with patch.object(Path, "is_symlink", return_value=True):
            with pytest.raises(
                SecurityViolationError, match="Symbolic links are strictly prohibited"
            ):
                apply_patch_to_workspace(ws, diff)


def test_patch_application_rejects_escape_via_parent_symlink(tmp_path):
    """Verify patch application rejects target paths with symlinks in intermediate directories."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    external_dir = tmp_path / "external_dir"
    external_dir.mkdir()
    (external_dir / "code.py").write_text("x = 1\n", encoding="utf-8")

    sub_link = ws / "sub"
    diff = """--- a/sub/code.py
+++ b/sub/code.py
@@ -1 +1 @@
-x = 1
+x = 2
"""
    if CAN_SYMLINK:
        sub_link.symlink_to(external_dir, target_is_directory=True)
        with pytest.raises(SecurityViolationError, match="Path traversal via symlink directory"):
            apply_patch_to_workspace(ws, diff)
    else:
        with patch.object(Path, "is_symlink", side_effect=lambda: True):
            with pytest.raises(SecurityViolationError):
                apply_patch_to_workspace(ws, diff)


def test_inspect_repository_ignores_symlinks_and_secrets(tmp_path):
    """Verify repository inspection ignores symlinks and secret files."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "main.py").write_text("import os\n", encoding="utf-8")
    (ws / ".env").write_text("SECRET=123\n", encoding="utf-8")

    if CAN_SYMLINK:
        (ws / "link.py").symlink_to(ws / "main.py")

    inspection = inspect_repository(ws)
    assert "main.py" in inspection.source_files
    assert ".env" not in inspection.source_files
    assert ".env" not in inspection.manifest_files
    if CAN_SYMLINK:
        assert "link.py" not in inspection.source_files


def test_strict_transfer_rejects_symlink_file(tmp_path):
    """Verify that safe_walk_repository with strict_transfer=True aborts immediately on symlinks."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "real.py").write_text("x = 1\n", encoding="utf-8")
    link = ws / "sym_link.py"

    if CAN_SYMLINK:
        link.symlink_to(ws / "real.py")
        with pytest.raises(SecurityViolationError, match="Symbolic link file .* is prohibited"):
            list(safe_walk_repository(ws, strict_transfer=True))
    else:
        with patch.object(Path, "is_symlink", return_value=True):
            with pytest.raises(SecurityViolationError, match="Symbolic link"):
                list(safe_walk_repository(ws, strict_transfer=True))


def test_strict_transfer_rejects_symlink_dir(tmp_path):
    """Verify that safe_walk_repository with strict_transfer=True aborts immediately on symlinked directories."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()
    (target_dir / "mod.py").write_text("y = 2\n", encoding="utf-8")
    link_dir = ws / "sym_dir"

    if CAN_SYMLINK:
        link_dir.symlink_to(target_dir, target_is_directory=True)
        with pytest.raises(
            SecurityViolationError, match="Symbolic link directory .* is prohibited"
        ):
            list(safe_walk_repository(ws, strict_transfer=True))
    else:
        with patch.object(Path, "is_symlink", return_value=True):
            with pytest.raises(SecurityViolationError, match="Symbolic link"):
                list(safe_walk_repository(ws, strict_transfer=True))


def test_strict_transfer_rejects_unreadable_file(tmp_path):
    """Verify that safe_walk_repository with strict_transfer=True aborts on unreadable files."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    unreadable = ws / "unreadable.py"
    unreadable.write_text("content\n", encoding="utf-8")

    original_stat = Path.stat

    def mock_stat_err(self, *args, **kwargs):
        if self.name == "unreadable.py":
            raise PermissionError("Access denied by OS")
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", side_effect=mock_stat_err, autospec=True):
        with pytest.raises(
            SecurityViolationError,
            match=r"(Inaccessible repository file|Failed to check symlink status)",
        ):
            list(safe_walk_repository(ws, strict_transfer=True))


def test_safe_read_file_bytes_regular_file(tmp_path):
    """Verify safe_read_file_bytes reads valid file content."""
    from app.repositories.security import safe_read_file_bytes

    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    content = safe_read_file_bytes(f, trusted_root=tmp_path, max_bytes=100)
    assert content == b"hello world"


def test_safe_read_file_bytes_rejects_symlink(tmp_path):
    """Verify safe_read_file_bytes rejects symbolic link."""
    from app.repositories.security import safe_read_file_bytes

    real = tmp_path / "real.txt"
    real.write_text("secret", encoding="utf-8")
    link = tmp_path / "link.txt"

    if CAN_SYMLINK:
        link.symlink_to(real)
        with pytest.raises(SecurityViolationError, match="Symbolic links are prohibited"):
            safe_read_file_bytes(link, trusted_root=tmp_path)
    else:
        with patch("os.lstat") as mock_lstat:
            import stat

            mock_res = type("StatRes", (), {"st_mode": stat.S_IFLNK, "st_size": 10})()
            mock_lstat.return_value = mock_res
            with pytest.raises(SecurityViolationError, match="Symbolic links are prohibited"):
                safe_read_file_bytes(real, trusted_root=tmp_path)


def test_safe_read_file_bytes_exceeds_limit(tmp_path):
    """Verify safe_read_file_bytes rejects files larger than max_bytes."""
    from app.repositories.security import safe_read_file_bytes

    f = tmp_path / "large.txt"
    f.write_text("a" * 500, encoding="utf-8")
    with pytest.raises(SecurityViolationError, match="exceeds limit"):
        safe_read_file_bytes(f, trusted_root=tmp_path, max_bytes=200)


def test_compute_repository_manifest_deterministic(tmp_path):
    """Verify compute_repository_manifest produces consistent SHA-256 digests."""
    from app.repositories.security import compute_repository_manifest

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "b.txt").write_text("content B\n", encoding="utf-8")
    (repo / "a.txt").write_text("content A\n", encoding="utf-8")
    sub = repo / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("content C\n", encoding="utf-8")

    manifest = compute_repository_manifest(repo)
    assert list(manifest.keys()) == ["a.txt", "b.txt", "sub/c.txt"]
    assert len(manifest["a.txt"]) == 64
    assert len(manifest["b.txt"]) == 64
    assert len(manifest["sub/c.txt"]) == 64
