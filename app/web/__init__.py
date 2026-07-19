"""app/web — the web front-end (Jinja2 + HTMX) · ADR-0006

Boundary: this package imports only app.pipeline (the seam), app.schemas (the contract)
and app.config (display-only model name) — never checker/postcheck directly.
"""

from app.web.routes import router

__all__ = ["router"]
