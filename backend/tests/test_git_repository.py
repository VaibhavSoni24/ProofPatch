"""Unit tests for GitHub repository validation and security."""

import pytest

from app.core.errors import SecurityViolationError
from app.repositories.git import validate_repository_url


def test_valid_github_url():
    """Verify standard public GitHub URLs are accepted."""
    owner, repo = validate_repository_url("https://github.com/VaibhavSoni24/ProofPatch")
    assert owner == "VaibhavSoni24"
    assert repo == "ProofPatch"


def test_valid_github_url_with_dot_git():
    """Verify .git suffix is trimmed cleanly."""
    owner, repo = validate_repository_url("https://github.com/psf/requests.git")
    assert owner == "psf"
    assert repo == "requests"


def test_reject_insecure_http_scheme():
    """Verify HTTP scheme is rejected."""
    with pytest.raises(SecurityViolationError) as exc:
        validate_repository_url("http://github.com/owner/repo")
    assert "scheme" in str(exc.value).lower()


def test_reject_embedded_credentials():
    """Verify URLs containing embedded credentials are strictly rejected."""
    with pytest.raises(SecurityViolationError) as exc:
        validate_repository_url("https://user:password@github.com/owner/repo")
    assert "credentials" in str(exc.value).lower()


def test_reject_unsupported_host():
    """Verify non-github hosts are rejected."""
    with pytest.raises(SecurityViolationError) as exc:
        validate_repository_url("https://gitlab.com/owner/repo")
    assert "host" in str(exc.value).lower()


def test_reject_empty_or_malformed_url():
    """Verify empty or non-URL string is rejected."""
    with pytest.raises(SecurityViolationError):
        validate_repository_url("")

    with pytest.raises(SecurityViolationError):
        validate_repository_url("not a url at all")
