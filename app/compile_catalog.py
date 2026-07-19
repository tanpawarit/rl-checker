"""app/compile_catalog.py — collapse catalog/ → a single context payload · spec.md §5

Walks all three parts of catalog/ (rules/ · dictionary.yaml · required_text.yaml)
and returns one string used as the context prefix (implicit caching relies on a repeated prefix).

Important: the output must be byte-for-byte stable when the catalog is unchanged
  (always ordered with sorted() · no timestamps or any variable content).
⚠ The rendered section names (<required_text>, DON'T/REVIEW) are referenced in checker.py's INSTRUCTION
  — changing them here means updating the prompt there to match.
"""

import pathlib

import yaml

# Anchor the repo root off __file__ (not the CWD) — same convention as every module that reads from disk
CATALOG_DIR = pathlib.Path(__file__).resolve().parent.parent / "catalog"


def compile_catalog(catalog_dir: str | pathlib.Path = CATALOG_DIR) -> str:
    base = pathlib.Path(catalog_dir)
    parts: list[str] = ["<compliance_rules>"]

    # 1) judgment rules — ordered by file name (01_, 02_, ...)
    for f in sorted((base / "rules").glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        parts.append(f'\n## หมวด: {data.get("category", f.stem)}')
        for r in data.get("rules") or []:
            parts.append(f'<rule id="{r["id"]}" severity="{r["severity"]}">')
            if r.get("title"):
                parts.append(f'title: {" ".join(r["title"].split())}')
            parts.append(f'check: {" ".join(r["check"].split())}')
            if r.get("must_state"):
                parts.append(f'must_state (ข้อความ/เงื่อนไขที่ต้องระบุเมื่อเข้าเคสนี้): {" ".join(r["must_state"].split())}')
            for kind in ("pass", "fail"):
                for ex in r.get(kind) or []:
                    parts.append(f"  {kind.upper()}: {ex}")
            if (r.get("source") or {}).get("citation"):
                parts.append(f'  (อ้างอิง: {r["source"]["citation"]})')
            parts.append("</rule>")
    parts.append("</compliance_rules>")

    # 2) dictionary — DON'T / REVIEW / DO (plain phrase lists, verbatim from the Excel sheet)
    d = yaml.safe_load((base / "dictionary.yaml").read_text(encoding="utf-8")) or {}
    parts.append("\n<dictionary>")
    if d.get("usage_notes"):
        parts.append(f'หมายเหตุการใช้: {" ".join(d["usage_notes"].split())}')
    parts.append("ห้ามใช้เด็ดขาด (DON'T):")
    for x in d.get("dont") or []:
        parts.append(f'  - "{x}"')
    parts.append("ใช้ได้เฉพาะมีเงื่อนไข/บริบทรองรับ (REVIEW):")
    for x in d.get("review") or []:
        parts.append(f'  - "{x}"')
    parts.append("ใช้ได้ (DO): " + " / ".join(d.get("do") or []))
    parts.append("</dictionary>")

    # 3) required_text — mandatory text per product family: warning (always) + rate_text variants, verbatim
    rt = yaml.safe_load((base / "required_text.yaml").read_text(encoding="utf-8")) or {}
    parts.append("\n<required_text>")
    for key, v in (rt.get("warn") or {}).items():
        parts.append(f'[{key}] {v.get("product", key)} · ใช้กับ: {", ".join(v.get("applies_to") or [])}')
        parts.append(f'  คำเตือน (ต้องมีทุก ad): "{" ".join(v["warning"].split())}"')
        parts.append(f'  ข้อความบังคับ (verbatim เลือกตามเคสที่ ad เข้า): {" ".join(v["rate_text"].split())}')
    if rt.get("note"):
        parts.append(f'หมายเหตุ: {" ".join(rt["note"].split())}')
    parts.append("</required_text>")

    return "\n".join(parts)
