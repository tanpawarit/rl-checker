"""app/pipeline.py — the single seam of the brain (spec §1.7): judge_ad → post_check as a mandatory sequence

Every front-end (main /check, try_check) crosses this seam at one point — preventing a forgotten post_check
call (which would silently drop the anti-hallucination flags) and keeping the front-ends from drifting apart.
"""

from app.catalog import load_catalog
from app.checker import judge_ad
from app.postcheck import post_check
from app.schemas import CheckResult


def run_check(image_bytes: bytes, mime: str = "image/jpeg", text: str | None = None) -> tuple[CheckResult, list[str]]:
    """Check one ad end-to-end: LLM call followed by the anti-hallucination gate, returns (result, flags)"""
    # parse the catalog once here (the single seam) and hand it to both stages — no re-parse, no caching
    catalog = load_catalog()
    result = judge_ad(image_bytes, mime, text, catalog=catalog)
    return result, post_check(result, catalog)
