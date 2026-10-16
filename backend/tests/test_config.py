"""Unit tests for configuration loading and security metadata."""

from app.core.config import Settings


def test_default_demo_mode_active():
    """Verify default mode is demo and credentials are blank."""
    settings = Settings(proofpatch_mode="demo")
    assert settings.is_demo_mode is True
    assert settings.is_nebius_configured is False
    assert settings.is_tavily_configured is False


def test_nebius_configuration_detection():
    """Verify Nebius is recognized only when both key and model are present."""
    s1 = Settings(nebius_api_key="key", nebius_model="")
    assert s1.is_nebius_configured is False

    s2 = Settings(nebius_api_key="", nebius_model="nvidia/nemotron-4-340b-instruct")
    assert s2.is_nebius_configured is False

    s3 = Settings(nebius_api_key="real-key", nebius_model="nvidia/nemotron-4-340b-instruct")
    assert s3.is_nebius_configured is True

    s4 = Settings(nebius_api_key="real-key", nebius_model="openai/gpt-4")
    assert s4.is_nebius_configured is False


def test_tavily_configuration_detection():
    """Verify Tavily requires both enabled flag and API key."""
    s1 = Settings(tavily_api_key="key", tavily_enabled=False)
    assert s1.is_tavily_configured is False

    s2 = Settings(tavily_api_key="", tavily_enabled=True)
    assert s2.is_tavily_configured is False

    s3 = Settings(tavily_api_key="tvly-secret", tavily_enabled=True)
    assert s3.is_tavily_configured is True


def test_config_status_api_redaction(client):
    """Verify config-status endpoint never returns raw API keys."""
    response = client.get("/api/config-status")
    assert response.status_code == 200
    data = response.json()

    assert "nebius_api_key" not in data
    assert "tavily_api_key" not in data
    assert "mode" in data
    assert "nebius_configured" in data
    assert "tavily_configured" in data
