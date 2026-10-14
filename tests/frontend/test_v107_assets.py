from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "app" / "frontend"


def test_v107_frontend_assets_exist():
    expected = (
        "index.html",
        "manifest.webmanifest",
        "service-worker.js",
        "app.js",
        "styles.css",
    )

    for filename in expected:
        assert (FRONTEND / filename).is_file(), filename


def test_v107_index_references_required_assets():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")

    assert 'href="/api/v1/frontend/manifest.webmanifest"' in html
    assert 'href="/api/v1/frontend/styles.css"' in html
    assert 'src="/api/v1/frontend/app.js"' in html


def test_v107_manifest_is_valid_json():
    import json

    manifest = json.loads(
        (FRONTEND / "manifest.webmanifest").read_text(encoding="utf-8")
    )

    assert manifest["name"] == "Decision Intelligence Platform"
    assert manifest["short_name"] == "DIP"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/api/v1/frontend/"


def test_v107_service_worker_contains_cache_strategy():
    worker = (FRONTEND / "service-worker.js").read_text(encoding="utf-8")

    assert "CACHE_NAME" in worker
    assert "self.addEventListener" in worker
    assert '"install"' in worker
    assert '"activate"' in worker
    assert '"fetch"' in worker


def test_v107_app_contains_mobile_modules():
    app = (FRONTEND / "app.js").read_text(encoding="utf-8")

    for module in (
        "organizations",
        "projects",
        "decisions",
        "risks",
        "execution",
        "kpis",
        "assistant",
    ):
        assert f'data-module="{module}"' in app
