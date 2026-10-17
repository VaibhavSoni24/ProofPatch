"""Tests for production static asset serving, SPA history fallback, and traversal prevention."""

from app.core.config import get_settings

settings = get_settings()


def test_production_root_serves_index_html(client, tmp_path, monkeypatch):
    """When frontend distribution exists, GET / serves index.html."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_text(
        "<!DOCTYPE html><html><body><h1>ProofPatch App</h1></body></html>", encoding="utf-8"
    )

    monkeypatch.setattr(settings, "frontend_dist_dir", str(dist_dir))
    monkeypatch.setattr(settings, "serve_frontend", True)

    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "ProofPatch App" in response.text


def test_dev_mode_root_serves_json_when_no_dist(client, monkeypatch):
    """When frontend distribution is absent or disabled, GET / returns JSON service metadata."""
    monkeypatch.setattr(settings, "serve_frontend", False)

    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "ProofPatch"
    assert data["health_url"] == "/api/health"
    assert "tagline" in data


def test_valid_static_asset_served(client, tmp_path, monkeypatch):
    """Valid static assets in assets/ or root are served with correct content."""
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)

    index_html = dist_dir / "index.html"
    index_html.write_text("<html>index</html>", encoding="utf-8")

    js_file = assets_dir / "bundle.js"
    js_file.write_text("console.log('ProofPatch bundle');", encoding="utf-8")

    favicon = dist_dir / "favicon.svg"
    favicon.write_text("<svg>icon</svg>", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_dir", str(dist_dir))
    monkeypatch.setattr(settings, "serve_frontend", True)

    js_res = client.get("/assets/bundle.js")
    assert js_res.status_code == 200
    assert "ProofPatch bundle" in js_res.text

    fav_res = client.get("/favicon.svg")
    assert fav_res.status_code == 200
    assert "<svg>icon</svg>" in fav_res.text


def test_frontend_fallback_navigation(client, tmp_path, monkeypatch):
    """SPA client-side routes return index.html for browser history navigation."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_text(
        "<!DOCTYPE html><html><body><h1>SPA Shell</h1></body></html>", encoding="utf-8"
    )

    monkeypatch.setattr(settings, "frontend_dist_dir", str(dist_dir))
    monkeypatch.setattr(settings, "serve_frontend", True)

    # Route with ID
    res1 = client.get("/runs/demo_12345")
    assert res1.status_code == 200
    assert "SPA Shell" in res1.text
    assert "text/html" in res1.headers.get("content-type", "")

    # Top-level route
    res2 = client.get("/settings")
    assert res2.status_code == 200
    assert "SPA Shell" in res2.text


def test_api_health_remains_functional(client, tmp_path, monkeypatch):
    """API health route remains functional and is never intercepted by SPA fallback."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_text("<html>index</html>", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_dir", str(dist_dir))
    monkeypatch.setattr(settings, "serve_frontend", True)

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "ProofPatch"


def test_static_path_traversal_prevented(client, tmp_path, monkeypatch):
    """Path traversal requests are strictly forbidden and return 403."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_text("<html>index</html>", encoding="utf-8")

    # Host secret file outside dist_dir
    secret_file = tmp_path / "secret.env"
    secret_file.write_text("SUPER_SECRET_KEY=12345", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_dir", str(dist_dir))
    monkeypatch.setattr(settings, "serve_frontend", True)

    # Attempt directory traversal
    res = client.get("/assets/../../secret.env")
    assert res.status_code in (403, 404)
    assert "SUPER_SECRET_KEY" not in res.text


def test_missing_asset_returns_404_not_html(client, tmp_path, monkeypatch):
    """Missing asset with extension returns 404 rather than index.html to avoid MIME errors."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_text("<html>index</html>", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_dir", str(dist_dir))
    monkeypatch.setattr(settings, "serve_frontend", True)

    response = client.get("/assets/missing_file.js")
    assert response.status_code == 404
    assert "<html>index</html>" not in response.text


def test_unknown_api_route_returns_404_json_not_html(client, tmp_path, monkeypatch):
    """Unmatched /api/* routes return 404 JSON, never index.html."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_text("<html>index</html>", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_dir", str(dist_dir))
    monkeypatch.setattr(settings, "serve_frontend", True)

    response = client.get("/api/nonexistent_route")
    assert response.status_code == 404
    assert "<html>index</html>" not in response.text
