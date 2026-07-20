"""app/postcheck.py — the anti-hallucination gate, in code · spec.md §7 + ADR-0003

Takes a CheckResult + catalog, runs deterministic checks, and returns a list of flags (never edits the
result, only flags it):
  1) rule_id ∈ catalog
  2) evidence ⊆ saw  (soft — only compares text inside quotation marks "...")
  3) saw ↔ findings  (warnings_found empty but a required-text rule still passes = contradiction)
  4) required_text match (two tiers): the risk warning always + per mentioned product at least one
     verbatim rate_text variant (the Excel lists several acceptable phrasings per product family)
  5) box_2d (when present) must be a sane [ymin, xmin, ymax, xmax] box in 0-1000

All matching shares the single normalize() · no extra deps (no fuzzy matching — rate numbers must be exact)
The Catalog is passed in by run_check (parsed once per check); this file never touches the YAML shape itself
"""

import re
import unicodedata

from app.catalog import Catalog
from app.schemas import CheckResult

_ZW = dict.fromkeys(map(ord, "​‌‍﻿"), None)
_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_QUOTE_RE = re.compile(r'"([^"]+)"|“([^”]+)”')


def normalize(s: str) -> str:
    """Make text comparable despite minor formatting differences — dash/%/Thai digits/zero-width,
    and strip ALL whitespace + quote marks: Thai has no word spacing and the Excel itself is
    inconsistent about spaces ("กู้เท่าที่จำเป็น และ..." vs "กู้เท่าที่จำเป็นและ...") and stray quotes"""
    s = unicodedata.normalize("NFC", s or "")
    s = s.translate(_ZW).translate(_THAI_DIGITS)
    s = s.replace("–", "-").replace("—", "-").replace("−", "-").replace("％", "%")
    s = re.sub(r'["“”\']', "", s)
    s = re.sub(r"\s+", "", s).lower()
    return s


def _quoted_spans(text: str) -> list[str]:
    return [a or b for a, b in _QUOTE_RE.findall(text or "")]


def _matches_product(applies_to: list[str], products_norm: str) -> bool:
    """Matches when all Thai tags (the real product-family markers: จำนำเล่ม/โอนเล่ม) are present —
    code tags (CRL/C2C) are skipped · the 'combined' entry carries a tag no ad states (หลายผลิตภัณฑ์)
    so it never matches by itself; its texts still count as variants through the per-family entries"""
    thai_tags = [normalize(t) for t in applies_to if not t.isascii()]
    return bool(thai_tags) and all(t in products_norm for t in thai_tags)


def _required_candidates(rate_text: str) -> list[str]:
    """Acceptable verbatim variants inside a rate_text block: quoted spans per line, or a whole line
    when it carries a rate (%) — case-label lines (no quotes, no %) are not variants themselves"""
    out: list[str] = []
    for line in (rate_text or "").splitlines():
        spans = _quoted_spans(line)
        if spans:
            out.extend(spans)
        elif "%" in line:
            out.append(line)
    return out


def post_check(result: CheckResult, catalog: Catalog) -> list[str]:
    flags: list[str] = []

    saw_text_n = normalize(result.saw.text_verbatim)
    products_n = normalize(" ".join(result.saw.products_mentioned))
    has_warning = bool(result.saw.warnings_found)

    # 1) rule_id must actually exist in the catalog
    for fnd in result.findings:
        if fnd.rule_id not in catalog.rule_ids:
            flags.append(f"หลอน: rule_id ไม่มีใน catalog — {fnd.rule_id}")

    # 2) evidence ⊆ saw (soft) — only spans inside quotation marks
    for fnd in result.findings:
        for q in _quoted_spans(fnd.evidence):
            qn = normalize(q)
            if qn and qn not in saw_text_n:
                flags.append(f'soft: [{fnd.rule_id}] evidence quote ไม่พบใน saw — "{q}"')

    # 3) saw ↔ findings — no warning found (warnings_found empty) yet a required-text rule still passes
    if not has_warning:
        refs = catalog.required_text_refs
        for fnd in result.findings:
            if fnd.status == "pass" and fnd.rule_id in refs:
                flags.append(
                    f"saw↔findings ขัดกัน: [{fnd.rule_id}] pass แต่ saw ไม่พบคำเตือน (warnings_found ว่าง)"
                )

    # 4) required_text match — the risk warning (always) + per product at least one rate_text variant
    if catalog.baseline and normalize(catalog.baseline) not in saw_text_n:
        flags.append(f'required_text baseline: ไม่พบคำเตือน "{catalog.baseline}" ใน ad')
    for rt in catalog.required_text:
        if not _matches_product(rt.applies_to, products_n):
            continue
        variants = [normalize(c) for c in _required_candidates(rt.rate_text)]
        if variants and not any(v and v in saw_text_n for v in variants):
            flags.append(
                f"required_text per-product: ad อ้างผลิตภัณฑ์ '{rt.key}' "
                f"แต่ข้อความบังคับ (คำเตือน+เรต) ไม่ครบ/ไม่ตรงใน saw → ยืนยัน fail"
            )

    # 5) box_2d (when present) must be a sane box — the UI draws it as-is, a bad one misleads the reader
    for fnd in result.findings:
        b = fnd.box_2d
        if b is not None and not (
            len(b) == 4 and all(0 <= v <= 1000 for v in b) and b[0] < b[2] and b[1] < b[3]
        ):
            flags.append(f"box_2d เพี้ยน: [{fnd.rule_id}] {b} (ต้องเป็น [ymin,xmin,ymax,xmax] ช่วง 0-1000)")

    return flags
