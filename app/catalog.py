"""app/catalog.py — the Catalog, parsed once from catalog/ · spec.md §5 + ADR-0003

catalog/ has three parts (CONTEXT.md): judgment rules (rules/*.yaml) · dictionary (dictionary.yaml) ·
required text (required_text.yaml). This is the ONE place that knows their YAML shape — both the prompt
renderer (compile_catalog.py) and the anti-hallucination gate (postcheck.py) read the parsed Catalog,
never the raw files.

load_catalog() validates on load: every rule's required_text_ref must resolve to a real required-text key,
so a dangling ref fails fast here instead of silently disabling postcheck's required_text match (a flag
that never fires is invisible in a report-only system).

Parsed on demand — the catalog is a handful of small YAML files, so callers just call load_catalog()
when they need it (postcheck on every check; the prompt renderer once). Strings are kept verbatim:
whitespace shaping for the prompt is the renderer's job, which keeps the implicit-cache prefix
byte-stable (ADR-0001).
"""

import pathlib
from dataclasses import dataclass, field

import yaml

# Anchor the repo root off __file__ (not the CWD) — same convention as every module that reads from disk
CATALOG_DIR = pathlib.Path(__file__).resolve().parent.parent / "catalog"


@dataclass(frozen=True)
class Rule:
    """One judgment rule (CONTEXT.md): a requirement the LLM judges in context, id RL-<category>.<n>"""

    id: str
    severity: str
    check: str
    title: str | None = None
    must_state: str | None = None
    pass_examples: list[str] = field(default_factory=list)
    fail_examples: list[str] = field(default_factory=list)
    citation: str | None = None
    required_text_ref: list[str] = field(default_factory=list)

    @property
    def required_text_keys(self) -> list[str]:
        """The key each ref points at: 'warn.crl' → 'crl' (the key into required_text)"""
        return [ref.split(".")[-1] for ref in self.required_text_ref]


@dataclass(frozen=True)
class RuleCategory:
    """One rules/*.yaml file: a หมวด heading + its rules, kept in filename order"""

    category: str
    rules: list[Rule]


@dataclass(frozen=True)
class Dictionary:
    """The DO / REVIEW / DON'T phrase lists (CONTEXT.md), verbatim from the Excel sheet"""

    dont: list[str]
    review: list[str]
    do: list[str]
    usage_notes: str | None = None


@dataclass(frozen=True)
class RequiredText:
    """One required-text entry per product family: the risk warning (always) + rate_text variants"""

    key: str
    product: str
    warning: str
    applies_to: list[str]
    rate_text: str


@dataclass(frozen=True)
class Catalog:
    categories: list[RuleCategory]
    dictionary: Dictionary
    required_text: list[RequiredText]
    note: str | None = None

    @property
    def rules(self) -> list[Rule]:
        return [r for cat in self.categories for r in cat.rules]

    @property
    def rule_ids(self) -> frozenset[str]:
        return frozenset(r.id for r in self.rules)

    @property
    def required_text_refs(self) -> dict[str, list[str]]:
        """rule_id → the required-text keys it must satisfy (only rules that carry a required_text_ref)"""
        return {r.id: r.required_text_keys for r in self.rules if r.required_text_ref}

    @property
    def baseline(self) -> str:
        """The risk warning required in every ad — shared by all products, "" if none"""
        return next((rt.warning for rt in self.required_text if rt.warning), "")


def load_catalog(catalog_dir: str | pathlib.Path = CATALOG_DIR) -> Catalog:
    base = pathlib.Path(catalog_dir)
    categories = [_read_category(f) for f in sorted((base / "rules").glob("*.yaml"))]
    dictionary = _read_dictionary(base / "dictionary.yaml")
    required_text, note = _read_required_text(base / "required_text.yaml")
    catalog = Catalog(categories, dictionary, required_text, note)
    _validate(catalog)
    return catalog


def _read_category(path: pathlib.Path) -> RuleCategory:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules = [_read_rule(r) for r in data.get("rules") or []]
    return RuleCategory(category=data.get("category", path.stem), rules=rules)


def _read_rule(r: dict) -> Rule:
    return Rule(
        id=r["id"],
        severity=r["severity"],
        check=r["check"],
        title=r.get("title"),
        must_state=r.get("must_state"),
        pass_examples=r.get("pass") or [],
        fail_examples=r.get("fail") or [],
        citation=(r.get("source") or {}).get("citation"),
        required_text_ref=r.get("required_text_ref") or [],
    )


def _read_dictionary(path: pathlib.Path) -> Dictionary:
    d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Dictionary(
        dont=d.get("dont") or [],
        review=d.get("review") or [],
        do=d.get("do") or [],
        usage_notes=d.get("usage_notes"),
    )


def _read_required_text(path: pathlib.Path) -> tuple[list[RequiredText], str | None]:
    rt = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = [
        RequiredText(
            key=key,
            product=v.get("product", key),
            warning=v.get("warning", ""),
            applies_to=v.get("applies_to") or [],
            rate_text=v.get("rate_text", ""),
        )
        for key, v in (rt.get("warn") or {}).items()
    ]
    return entries, rt.get("note")


def _validate(catalog: Catalog) -> None:
    """Fail fast on a dangling required_text_ref — otherwise postcheck's required_text match would
    silently never fire for that rule, and nobody sees a flag that never fires (report-only)."""
    keys = {rt.key for rt in catalog.required_text}
    dangling = {r.id: missing for r in catalog.rules if (missing := [k for k in r.required_text_keys if k not in keys])}
    if dangling:
        detail = " · ".join(f"{rid} → {missing}" for rid, missing in dangling.items())
        raise ValueError(f"catalog: required_text_ref points at unknown required_text key(s): {detail}")
