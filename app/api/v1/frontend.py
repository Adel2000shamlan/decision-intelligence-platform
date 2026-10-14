from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

router = APIRouter(prefix="/frontend", tags=["frontend"])

router.mount(
    "/assets",
    StaticFiles(directory=FRONTEND_DIR),
    name="frontend-assets",
)


@router.get("/", include_in_schema=False)
def frontend_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/index.html", include_in_schema=False)
def frontend_index_file():
    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/manifest.webmanifest", include_in_schema=False)
def frontend_manifest():
    return FileResponse(
        FRONTEND_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
    )


@router.get("/app.js", include_in_schema=False)
def frontend_app():
    return FileResponse(
        FRONTEND_DIR / "app.js",
        media_type="text/javascript",
    )


@router.get("/styles.css", include_in_schema=False)
def frontend_styles():
    return FileResponse(
        FRONTEND_DIR / "styles.css",
        media_type="text/css",
    )


@router.get("/service-worker.js", include_in_schema=False)
def frontend_service_worker():
    return FileResponse(
        FRONTEND_DIR / "service-worker.js",
        media_type="text/javascript",
    )
