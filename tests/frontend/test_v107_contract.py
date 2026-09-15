from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "app" / "frontend"



def test_v107_service_worker_registered_once_in_index():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    app = (FRONTEND / "app.js").read_text(encoding="utf-8")

    assert html.count("navigator.serviceWorker.register") == 1
    assert "navigator.serviceWorker.register" not in app
