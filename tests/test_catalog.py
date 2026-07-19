import pytest

from app.catalog import load_catalog

CAT = "catalog"


def test_real_catalog_loads_and_validates():
    cat = load_catalog(CAT)
    assert "RL-2.1" in cat.rule_ids
    assert cat.baseline  # the risk warning required in every ad
    # RL-2.1's required_text_ref resolves to the required_text keys (validated on load)
    assert cat.required_text_refs["RL-2.1"] == ["combined", "crl", "c2c"]
    assert {"crl", "c2c", "combined"} <= {rt.key for rt in cat.required_text}


def _write_catalog(base, ref: str):
    (base / "rules").mkdir()
    (base / "rules" / "01.yaml").write_text(
        f"category: x\nrules:\n  - id: RL-1.1\n    severity: high\n    check: c\n    required_text_ref: [{ref}]\n",
        encoding="utf-8",
    )
    (base / "dictionary.yaml").write_text("dont: []\nreview: []\ndo: []\n", encoding="utf-8")
    (base / "required_text.yaml").write_text(
        "warn:\n  crl:\n    warning: w\n    applies_to: [CRL]\n    rate_text: r\n", encoding="utf-8"
    )


def test_dangling_required_text_ref_raises(tmp_path):
    _write_catalog(tmp_path, "warn.nope")  # 'nope' is not a required_text key
    with pytest.raises(ValueError, match="RL-1.1"):
        load_catalog(str(tmp_path))


def test_resolvable_required_text_ref_loads(tmp_path):
    _write_catalog(tmp_path, "warn.crl")  # 'crl' exists → validates clean
    cat = load_catalog(str(tmp_path))
    assert cat.required_text_refs["RL-1.1"] == ["crl"]
