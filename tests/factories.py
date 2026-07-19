"""tests/factories.py — build sample CheckResults for testing the deterministic layer"""

from app.schemas import CheckResult, Finding, RateShown, Saw, WarningFound

BASELINE = "กู้เท่าที่จำเป็นและชำระคืนไหว"
# matches required_text.yaml → warn.crl rate_text, the กรณีลูกค้าบุคคลธรรมดาอย่างเดียว variant (verbatim)
CRL_PERSONAL_TEXT = (
    "กู้เท่าที่จำเป็นและชำระคืนไหว อัตราดอกเบี้ยที่แท้จริงต่อปี "
    "สินเชื่อจำนำเล่มทะเบียนรถ 12.82% - 24.00%"
)
PERSONAL_PRODUCT = "สินเชื่อจำนำเล่มทะเบียนรถ บุคคลธรรมดา"


def finding(
    rule_id: str = "RL-2.1",
    status: str = "pass",
    severity: str = "critical",
    evidence: str = "เห็นคำเตือนชัดในภาพ",
    title: str = "คำเตือน + เรต",
    issue: str = "",
    fix_note: str = "",
    box_2d: list[int] | None = None,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        title=title,
        status=status,
        severity=severity,
        evidence=evidence,
        issue=issue,
        fix_note=fix_note,
        box_2d=box_2d,
    )


def make_result(
    text_verbatim: str = CRL_PERSONAL_TEXT,
    products: list[str] | None = None,
    warnings: list[WarningFound] | None = None,
    rates: list[RateShown] | None = None,
    findings: list[Finding] | None = None,
    manual: list[str] | None = None,
    visual_notes: str = "",
) -> CheckResult:
    return CheckResult(
        saw=Saw(
            text_verbatim=text_verbatim,
            products_mentioned=[PERSONAL_PRODUCT] if products is None else products,
            warnings_found=[WarningFound(text=BASELINE, location="ท้ายภาพ", prominence="ชัด")]
            if warnings is None
            else warnings,
            rates_shown=[RateShown(product="จำนำเล่ม บุคคลธรรมดา", rate="12.82% - 24.00%")]
            if rates is None
            else rates,
            visual_notes=visual_notes,
        ),
        findings=[finding()] if findings is None else findings,
        manual_checks=manual or [],
    )
