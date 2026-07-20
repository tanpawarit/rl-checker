from app.catalog import load_catalog
from app.postcheck import normalize, post_check
from tests.factories import BASELINE, CRL_PERSONAL_TEXT, finding, make_result

CAT = load_catalog("catalog")


def test_clean_pass_has_no_flags():
    assert post_check(make_result(), CAT) == []


def test_hallucinated_rule_id_flagged():
    flags = post_check(make_result(findings=[finding(rule_id="RL-9.9")]), CAT)
    assert any("rule_id ไม่มีใน catalog" in f for f in flags)


def test_missing_baseline_warning_flagged():
    r = make_result(
        text_verbatim="โปรจำนำเล่มทะเบียนรถ บุคคลธรรมดา 12.82% - 24.00%",
        warnings=[],
    )
    assert any("baseline" in f for f in post_check(r, CAT))


def test_saw_findings_contradiction_flagged():
    # text contains the warning (baseline passes) but warnings_found is empty + RL-2.1 passes → contradiction
    r = make_result(text_verbatim=CRL_PERSONAL_TEXT, warnings=[])
    assert any("saw↔findings" in f for f in post_check(r, CAT))


def test_per_product_required_text_missing_flagged():
    # the product (จำนำเล่ม) is clearly stated but saw has only the warning (no rate variant) → confirm fail
    r = make_result(text_verbatim=BASELINE)
    flags = post_check(r, CAT)
    assert any("per-product" in f and "'crl'" in f for f in flags)


def test_any_rate_text_variant_satisfies_required_text():
    # the Excel lists several acceptable phrasings per family — matching any one variant is enough
    r = make_result(text_verbatim=CRL_PERSONAL_TEXT, products=["สินเชื่อจำนำเล่มทะเบียนรถ"])
    assert not any("per-product" in f for f in post_check(r, CAT))


def test_evidence_fake_quote_soft_flagged():
    r = make_result(findings=[finding(evidence='โฆษณาเขียนว่า "อนุมัติไวใน 5 นาที"')])
    flags = post_check(r, CAT)
    assert any(f.startswith("soft:") and "อนุมัติไวใน 5 นาที" in f for f in flags)


def test_evidence_visual_description_not_flagged():
    r = make_result(findings=[finding(evidence="ภาพเงินปลิวสื่อว่ากู้ง่าย (ไม่มีคำพูด)")])
    assert not any(f.startswith("soft:") for f in post_check(r, CAT))


def test_normalize_dash_space_thaidigit():
    assert normalize("12.82%  -  24.00%") == normalize("12.82% – 24.00%")
    assert normalize("๑๒.๘๒%") == "12.82%"


def test_bad_box_2d_flagged_good_box_not():
    r = make_result(
        findings=[
            finding(box_2d=[100, 100, 900, 900]),  # sane
            finding(rule_id="RL-1.1", box_2d=[900, 100, 100, 900]),  # ymin > ymax
            finding(rule_id="RL-1.2", box_2d=[0, 0, 1500, 500]),  # out of 0-1000
        ]
    )
    flags = [f for f in post_check(r, CAT) if f.startswith("box_2d")]
    assert len(flags) == 2
    assert any("RL-1.1" in f for f in flags) and any("RL-1.2" in f for f in flags)
