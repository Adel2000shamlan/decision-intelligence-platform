from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "app" / "frontend"


def test_v107_frontend_shell_exists():
    assert (FRONTEND / "index.html").is_file()


def test_v107_pwa_manifest_exists():
    assert (FRONTEND / "manifest.webmanifest").is_file()


def test_v107_service_worker_exists():
    assert (FRONTEND / "service-worker.js").is_file()


def test_v107_frontend_contains_mobile_shell():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert 'id="app"' in html
