"""app/web/routes.py — two routes on top of the brain's single seam (spec §1.7)

  GET  /          — submit form (full page, screen 1)
  POST /check-ui  — run_check → render the dossier partial (screen 2); HTMX swaps it into #content

The templates only loop over CheckResult fields — grouping/sorting happens here so the
templates stay logic-free. Rendering order mirrors the schema: evidence before verdicts.
"""

import asyncio
import base64
import datetime
import logging
import pathlib
import time

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.templating import Jinja2Templates

from app.config import DEFAULT_MODEL, LLMConfig
from app.pipeline import run_check

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

# cache-buster: browsers hold stale CSS/JS across restarts — version assets by newest static-file mtime
_STATIC_DIR = pathlib.Path(__file__).parent / "static"
ASSET_V = str(int(max(p.stat().st_mtime for p in _STATIC_DIR.iterdir() if p.is_file())))

_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def _checked_at() -> str:
    now = datetime.datetime.now()
    return f"{now.day} {_THAI_MONTHS[now.month - 1]} {now.year} · {now:%H:%M}"


def _model_name() -> str:
    try:
        return LLMConfig.from_env().model
    except RuntimeError:  # no API key (e.g. tests with a mocked brain) — display-only, never block the report
        return DEFAULT_MODEL


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"asset_v": ASSET_V})


@router.post("/check-ui")
async def check_ui(request: Request, file: UploadFile = File(...), text: str | None = Form(None)):
    data = await file.read()
    mime = file.content_type or "image/jpeg"
    started = time.perf_counter()
    try:
        result, flags = await asyncio.to_thread(run_check, data, mime, text)
    except Exception:
        logger.exception("check failed")
        return templates.TemplateResponse(request, "_error.html")

    fails = sorted(
        (f for f in result.findings if f.status == "fail"),
        key=lambda f: _SEVERITY_RANK.get(f.severity, len(_SEVERITY_RANK)),
    )
    context = {
        "result": result,
        "flags": flags,
        "fails": fails,
        "reviews": [f for f in result.findings if f.status == "review"],
        "passes": [f for f in result.findings if f.status == "pass"],
        "filename": file.filename or "ad",
        "has_caption": bool(text),
        "checked_at": _checked_at(),
        "elapsed_s": round(time.perf_counter() - started),
        "model": _model_name(),
        "img_data_uri": f"data:{mime};base64,{base64.b64encode(data).decode()}",
    }
    return templates.TemplateResponse(request, "_report.html", context)
