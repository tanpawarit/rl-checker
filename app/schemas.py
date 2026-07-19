"""app/schemas.py — the shared contract (Pydantic models) · spec.md §4

CheckResult / Finding / Saw — every file references this schema:
  checker enforces it as response_schema · postcheck validates against it · the front-end renders it
"""

from typing import Literal

from pydantic import BaseModel


class WarningFound(BaseModel):
    text: str
    location: str  # e.g. "ท้ายภาพ", "caption"
    prominence: str  # "ชัด" | "เล็ก-จาง" | "ไม่พบ"


class RateShown(BaseModel):
    product: str
    rate: str


class Saw(BaseModel):
    """What the AI read from the ad — the evidence, and what localizes a fail"""

    text_verbatim: str  # all readable text, including fine print/caption
    products_mentioned: list[str]
    warnings_found: list[WarningFound]
    rates_shown: list[RateShown]
    visual_notes: str


class Finding(BaseModel):
    """Field order = the order the model generates in (response_schema fixes property order to this)
    → evidence/issue come before status/severity, forcing evidence to be written before the verdict"""

    rule_id: str
    title: str
    evidence: str  # quote text from the ad / cite what is seen in the image
    # [ymin, xmin, ymax, xmax] normalized 0-1000 (Gemini's native detection format) — the image region
    # the evidence points at · None = nothing to point at (caption evidence, absence, whole-image observations)
    box_2d: list[int] | None = None
    issue: str
    # Literal → pydantic rejects out-of-range values on validate and renders as an enum in response_schema
    # also constrains Gemini at the source (prominence in WarningFound is free-form Thai — deliberately unconstrained)
    status: Literal["fail", "review", "pass"]
    severity: Literal["critical", "high", "medium", "low"]
    fix_note: str


class CheckResult(BaseModel):
    saw: Saw
    findings: list[Finding]
    manual_checks: list[str]  # things the AI cannot decide (e.g. font size) → for a human to check
