from pathlib import Path


DECISION_MODULE = Path(__file__).resolve().parents[1] / "app" / "modules" / "decision"


def _python_sources(path: Path):
    return path.rglob("*.py")


def test_official_domain_and_application_do_not_depend_on_legacy_compatibility():
    for layer in ("domain", "application"):
        for source in _python_sources(DECISION_MODULE / layer):
            text = source.read_text(encoding="utf-8")
            assert "compatibility" not in text
            assert "Legacy" not in text


def test_decision_compatibility_does_not_depend_on_legacy_api_or_store():
    compatibility = DECISION_MODULE / "compatibility"

    for source in _python_sources(compatibility):
        text = source.read_text(encoding="utf-8")
        assert "app.api" not in text
        assert "app.core.store" not in text
