"""app/compile_catalog.py — render the Catalog into the LLM context prefix · spec.md §5

Formats the parsed Catalog (app/catalog.py) into one string used as the first content block
(implicit caching relies on a repeated prefix). A pure function of the Catalog — no file I/O;
the caller (run_check) does the one load_catalog().

Important: the output must be byte-for-byte stable when the catalog is unchanged
  (ordering is fixed by the Catalog · no timestamps or any variable content).
⚠ The rendered section names (<compliance_rules> <dictionary> <required_text>, DON'T/REVIEW) are
  referenced in checker.py's INSTRUCTION — changing them here means updating the prompt there to match.
"""

from app.catalog import Catalog, Dictionary, Rule


def compile_catalog(catalog: Catalog) -> str:
    parts: list[str] = ["<compliance_rules>"]
    for cat in catalog.categories:  # judgment rules, ordered by file name (01_, 02_, ...)
        parts.append(f"\n## หมวด: {cat.category}")
        for rule in cat.rules:
            parts.extend(_render_rule(rule))
    parts.append("</compliance_rules>")

    parts.extend(_render_dictionary(catalog.dictionary))
    parts.extend(_render_required_text(catalog))
    return "\n".join(parts)


def _oneline(s: str) -> str:
    """Collapse the YAML block scalar's internal newlines/indent into a single line for the prompt"""
    return " ".join(s.split())


def _render_rule(r: Rule) -> list[str]:
    lines = [f'<rule id="{r.id}" severity="{r.severity}">']
    if r.title:
        lines.append(f"title: {_oneline(r.title)}")
    lines.append(f"check: {_oneline(r.check)}")
    if r.must_state:
        lines.append(f"must_state (ข้อความ/เงื่อนไขที่ต้องระบุเมื่อเข้าเคสนี้): {_oneline(r.must_state)}")
    for ex in r.pass_examples:
        lines.append(f"  PASS: {ex}")
    for ex in r.fail_examples:
        lines.append(f"  FAIL: {ex}")
    if r.citation:
        lines.append(f"  (อ้างอิง: {r.citation})")
    lines.append("</rule>")
    return lines


def _render_dictionary(d: Dictionary) -> list[str]:
    # DON'T / REVIEW / DO — plain phrase lists, verbatim from the Excel sheet
    lines = ["\n<dictionary>"]
    if d.usage_notes:
        lines.append(f"หมายเหตุการใช้: {_oneline(d.usage_notes)}")
    lines.append("ห้ามใช้เด็ดขาด (DON'T):")
    lines.extend(f'  - "{x}"' for x in d.dont)
    lines.append("ใช้ได้เฉพาะมีเงื่อนไข/บริบทรองรับ (REVIEW):")
    lines.extend(f'  - "{x}"' for x in d.review)
    lines.append("ใช้ได้ (DO): " + " / ".join(d.do))
    lines.append("</dictionary>")
    return lines


def _render_required_text(catalog: Catalog) -> list[str]:
    # mandatory text per product family: warning (always) + rate_text variants, verbatim
    lines = ["\n<required_text>"]
    for rt in catalog.required_text:
        lines.append(f'[{rt.key}] {rt.product} · ใช้กับ: {", ".join(rt.applies_to)}')
        lines.append(f'  คำเตือน (ต้องมีทุก ad): "{_oneline(rt.warning)}"')
        lines.append(f"  ข้อความบังคับ (verbatim เลือกตามเคสที่ ad เข้า): {_oneline(rt.rate_text)}")
    if catalog.note:
        lines.append(f"หมายเหตุ: {_oneline(catalog.note)}")
    lines.append("</required_text>")
    return lines
