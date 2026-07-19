from app.compile_catalog import compile_catalog


def test_byte_stable():
    # the core condition for implicit caching: a byte-for-byte stable payload
    assert compile_catalog("catalog") == compile_catalog("catalog")


def test_contains_expected_sections():
    out = compile_catalog("catalog")
    assert "RL-2.1" in out
    assert "กู้เท่าที่จำเป็นและชำระคืนไหว" in out  # required_text baseline
    assert "อนุมัติ 100%" in out  # dictionary DON'T (forbidden phrase)
    assert "<compliance_rules>" in out and "<dictionary>" in out and "<required_text>" in out
