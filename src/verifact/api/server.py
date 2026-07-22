"""FastAPI application: REST API + bundled web UI."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .. import __version__, pipeline
from ..config import get_settings
from ..extract import FetchError
from ..models import CredibilityReport

app = FastAPI(
    title="VeriFact API",
    version=__version__,
    description="Open-source credibility engine for news, web content and social media.",
    license_info={"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if not _WEB_DIR.exists():  # running from a source checkout
    _WEB_DIR = Path(__file__).resolve().parents[3] / "web"


class AnalyzeRequest(BaseModel):
    url: str | None = Field(default=None, description="URL of the article/post to verify")
    text: str | None = Field(default=None, description="Raw text to verify instead of a URL")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


@app.get("/api/v1/health")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "llm_configured": s.has_llm,
        "search_configured": s.has_search,
        "factcheck_configured": bool(s.google_factcheck_api_key),
    }


@app.post("/api/v1/analyze", response_model=CredibilityReport)
async def analyze(req: AnalyzeRequest) -> CredibilityReport:
    if bool(req.url) == bool(req.text):
        raise HTTPException(422, "Provide exactly one of 'url' or 'text'.")
    try:
        if req.url:
            return await pipeline.analyze_url(req.url)
        return await pipeline.analyze_text(req.text or "")
    except FetchError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/v1/analyze/image", response_model=CredibilityReport)
async def analyze_image(
    file: UploadFile = File(...), caption: str = Form(default="")
) -> CredibilityReport:
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        return await pipeline.analyze_image(tmp_path, caption)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
