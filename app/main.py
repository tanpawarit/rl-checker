"""app/main.py — endpoints (FastAPI) · spec.md §9 + ADR-0002/0006

  GET  /  ·  POST /check-ui  — web UI (app/web: Jinja2 + HTMX, ADR-0006)
  POST /check   — HTTP contract §1.7: returns a neutral {result: CheckResult, flags}, not tied to any front-end
  GET  /healthz — health probe

No /report, no warm-cache startup (ADR-0001/0002)
"""

import asyncio
import pathlib

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.staticfiles import StaticFiles

from app.pipeline import run_check
from app.web import router as web_router

app = FastAPI(title="Ad Compliance Checker")
app.include_router(web_router)
app.mount(
    "/static",
    StaticFiles(directory=str(pathlib.Path(__file__).parent / "web" / "static")),
    name="static",
)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/check")
async def check(file: UploadFile = File(...), text: str | None = Form(None)) -> dict:
    """Receive an ad image → run_check (LLM + anti-hallucination gate) → return the neutral contract"""
    data = await file.read()
    result, flags = await asyncio.to_thread(run_check, data, file.content_type or "image/jpeg", text)
    return {"result": result.model_dump(), "flags": flags}
