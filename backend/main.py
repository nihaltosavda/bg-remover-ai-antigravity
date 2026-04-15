"""
main.py — FastAPI server for the AI Background Remover App.

Endpoints:
  POST /api/remove-bg               — Remove background, return transparent PNG
  POST /api/replace-bg              — Remove background, fill with solid colour
  GET  /api/health                  — Health check
  GET  /                            — Serve frontend index.html
"""

import io
import logging
import os
import sys
import time
from pathlib import Path

# Ensure the backend package directory is always on sys.path so that
# `from utils import ...` resolves correctly however uvicorn is launched.
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from utils import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    ALLOWED_MIME_TYPES,
    remove_background,
    replace_background_color,
    validate_file_size,
    validate_mime_type,
    validate_image_bytes,
)

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# App bootstrap
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Background Remover",
    description="Remove image backgrounds instantly with U2Net AI.",
    version="1.0.0",
)

# Allow the frontend (served from a separate dev server or same origin) to call
# the API.  In production, tighten this to your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

async def read_and_validate(file: UploadFile) -> bytes:
    """Read upload, run all validations, return raw bytes."""
    # Content-type check
    content_type = file.content_type or ""
    try:
        validate_mime_type(content_type)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))

    # Read bytes
    raw = await file.read()

    # Size check
    try:
        validate_file_size(raw)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    # Integrity check
    try:
        validate_image_bytes(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return raw


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    """Serve the single-page frontend."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(index_path))


@app.get("/api/health")
async def health():
    """Simple health-check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/remove-bg")
async def api_remove_bg(file: UploadFile = File(...)):
    """
    Accept an image upload and return a transparent-background PNG.

    - **file**: Image file (JPG / PNG / WebP, max 5 MB)
    """
    logger.info("remove-bg request | filename=%s | ct=%s", file.filename, file.content_type)
    t0 = time.perf_counter()

    raw = await read_and_validate(file)

    try:
        result_bytes = remove_background(raw)
    except RuntimeError as exc:
        logger.error("Processing error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    elapsed = time.perf_counter() - t0
    logger.info(
        "remove-bg done | input=%d B | output=%d B | %.2fs",
        len(raw), len(result_bytes), elapsed,
    )

    filename = Path(file.filename or "result").stem + "_nobg.png"
    return Response(
        content=result_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/replace-bg")
async def api_replace_bg(
    file: UploadFile = File(...),
    color: str = Form(default="#ffffff"),
):
    """
    Remove background and fill with a solid hex colour.

    - **file**: Image file (JPG / PNG / WebP, max 5 MB)
    - **color**: Hex colour string, e.g. `#ff0000`
    """
    logger.info(
        "replace-bg request | filename=%s | color=%s", file.filename, color
    )
    t0 = time.perf_counter()

    raw = await read_and_validate(file)

    # Validate hex colour
    stripped = color.lstrip("#")
    if len(stripped) not in (3, 6) or not all(
        c in "0123456789abcdefABCDEF" for c in stripped
    ):
        raise HTTPException(status_code=422, detail=f"Invalid hex color: {color!r}")

    try:
        result_bytes = replace_background_color(raw, color)
    except RuntimeError as exc:
        logger.error("Processing error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    elapsed = time.perf_counter() - t0
    logger.info("replace-bg done | %.2fs", elapsed)

    filename = Path(file.filename or "result").stem + "_colorbg.png"
    return Response(
        content=result_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
