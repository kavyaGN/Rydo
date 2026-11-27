"""Serve the built React app from the API process (single-URL deployments).

When `FRONTEND_DIST_DIR` points at a Vite build, hashed assets are served from
`/assets` and every other non-API GET falls back to `index.html` so client-side
routes like `/history` work on refresh. API, docs and health paths are never
shadowed: unknown API paths still return a JSON 404.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_RESERVED_PREFIXES = ("api/", "docs", "redoc", "openapi.json", "health", "ready")


def mount_frontend(app: FastAPI, dist_dir: str | None) -> bool:
    if not dist_dir:
        return False
    dist = Path(dist_dir).resolve()
    index = dist / "index.html"
    if not index.is_file():
        return False

    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        if full_path.startswith(_RESERVED_PREFIXES):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (dist / full_path).resolve()
        # Serve real top-level files (favicon, manifest); never escape the dist folder.
        if full_path and candidate.is_file() and dist in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return True
