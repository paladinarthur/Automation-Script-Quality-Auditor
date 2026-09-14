import pytest
from src.models.finding import Finding
from src.models.enums import Severity, Confidence
from src.services.normalization_service import normalize_findings


# Helper factory for findings
def make_finding(
    id: str,
    anti_pattern_id: str,
    anti_pattern_name: str = "Test Pattern",
    line_start: int = 1,
    line_end: int = 1,
    code_snippet: str = "some_code()",
    reason: str = "Test reason",
    severity: Severity = Severity.MEDIUM,
    confidence: Confidence = Confidence.HIGH,
) -> Finding:
    return Finding(
        id=id,
        anti_pattern_id=anti_pattern_id,
        anti_pattern_name=anti_pattern_name,
        severity=severity,
        confidence=confidence,
        line_start=line_start,
        line_end=line_end,
        code_snippet=code_snippet,
        reason=reason,
        explanation="",
        suggested_fix="",
    )


# 1. Empty findings return empty findings.
def test_empty_findings_returns_empty():
    assert normalize_findings([]) == []


# 2. A single finding remains unchanged.
def test_single_finding_remains_unchanged():
    f = make_finding("1", "AP01", line_start=5, line_end=5)
    result = normalize_findings([f])
    assert result == [f]


# 3. Exact duplicate findings are reduced to one.
def test_exact_duplicate_findings_reduced_to_one():
    f1 = make_finding("1", "AP01", line_start=5, line_end=5, code_snippet="time.sleep(5)")
    f2 = make_finding("2", "AP01", line_start=5, line_end=5, code_snippet="time.sleep(5)")
    result = normalize_findings([f1, f2])
    assert len(result) == 1
    assert result[0].id == "1"


# 4. Duplicate findings at different locations are preserved.
def test_duplicate_findings_at_different_locations_preserved():
    f1 = make_finding("1", "AP01", line_start=5, line_end=5, code_snippet="time.sleep(5)")
    f2 = make_finding("2", "AP01", line_start=12, line_end=12, code_snippet="time.sleep(5)")
    result = normalize_findings([f1, f2])
    assert len(result) == 2
    assert [f.line_start for f in result] == [5, 12]


# 5. Different anti-patterns at the same line are preserved.
def test_different_anti_patterns_at_same_line_preserved():
    f1 = make_finding("1", "AP06", line_start=10, line_end=10, code_snippet="driver.find_element('xpath', '/html/body/div[5]').click()")
    f2 = make_finding("2", "AP08", line_start=10, line_end=10, code_snippet="driver.find_element('xpath', '/html/body/div[5]').click()")
    result = normalize_findings([f1, f2])
    assert len(result) == 2
    assert {f.anti_pattern_id for f in result} == {"AP06", "AP08"}


# 6. AP01 fixed-delay finding takes precedence over overlapping AP02/AP10 findings when they represent the same delay.
def test_ap01_takes_precedence_over_ap02_and_ap10():
    ap01 = make_finding("1", "AP01", line_start=5, line_end=5, code_snippet="time.sleep(5000)")
    ap02 = make_finding("2", "AP02", line_start=5, line_end=5, code_snippet="time.sleep(5000)")
    ap10 = make_finding("3", "AP10", line_start=5, line_end=5, code_snippet="time.sleep(5000)")

    result = normalize_findings([ap01, ap02, ap10])
    assert len(result) == 1
    assert result[0].anti_pattern_id == "AP01"


# 7. AP03 and AP05 can coexist when they represent distinct findings.
def test_ap03_and_ap05_can_coexist():
    ap03 = make_finding("1", "AP03", anti_pattern_name="Duplicated Code", line_start=10, line_end=20, code_snippet="dupe_block()")
    ap05 = make_finding("2", "AP05", anti_pattern_name="Missing Abstractions", line_start=10, line_end=20, code_snippet="dupe_block()")

    result = normalize_findings([ap03, ap05])
    assert len(result) == 2
    assert {f.anti_pattern_id for f in result} == {"AP03", "AP05"}


# 8. Finding metadata is preserved.
def test_finding_metadata_preserved():
    f = make_finding(
        id="f100",
        anti_pattern_id="AP09",
        anti_pattern_name="Hardcoded Secrets",
        line_start=3,
        line_end=4,
        code_snippet="api_key = '[REDACTED]'",
        reason="Hardcoded secret detected",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
    )
    result = normalize_findings([f])
    res = result[0]
    assert res.id == "f100"
    assert res.anti_pattern_id == "AP09"
    assert res.anti_pattern_name == "Hardcoded Secrets"
    assert res.line_start == 3
    assert res.line_end == 4
    assert res.code_snippet == "api_key = '[REDACTED]'"
    assert res.reason == "Hardcoded secret detected"
    assert res.severity == Severity.HIGH
    assert res.confidence == Confidence.HIGH


# 9. Findings are deterministically sorted by line_start, line_end, anti_pattern_id.
def test_findings_deterministically_sorted():
    f1 = make_finding("1", "AP06", line_start=10, line_end=12)
    f2 = make_finding("2", "AP01", line_start=3, line_end=3)
    f3 = make_finding("3", "AP04", line_start=10, line_end=10)
    f4 = make_finding("4", "AP01", line_start=10, line_end=12)

    result = normalize_findings([f1, f2, f3, f4])
    # Expected order:
    # 1. f2: line_start=3
    # 2. f3: line_start=10, line_end=10
    # 3. f4: line_start=10, line_end=12, AP01
    # 4. f1: line_start=10, line_end=12, AP06
    assert result == [f2, f3, f4, f1]


# 10. Multiple unrelated findings remain intact.
def test_multiple_unrelated_findings_remain_intact():
    f1 = make_finding("1", "AP01", line_start=2, line_end=2, code_snippet="time.sleep(2)")
    f2 = make_finding("2", "AP02", line_start=8, line_end=8, code_snippet="timeout = 37")
    f3 = make_finding("3", "AP06", line_start=15, line_end=15, code_snippet="driver.find_element('xpath', '/html/body')")
    f4 = make_finding("4", "AP07", line_start=20, line_end=25, code_snippet="def test_foo(): pass")
    f5 = make_finding("5", "AP09", line_start=30, line_end=30, code_snippet="secret = '[REDACTED]'")

    result = normalize_findings([f1, f2, f3, f4, f5])
    assert len(result) == 5
    assert result == [f1, f2, f3, f4, f5]


# 11. The normalizer does not modify the original input list unexpectedly.
def test_normalizer_does_not_mutate_original_list():
    f1 = make_finding("1", "AP01", line_start=5, line_end=5, code_snippet="time.sleep(5)")
    f2 = make_finding("2", "AP01", line_start=5, line_end=5, code_snippet="time.sleep(5)")
    original = [f1, f2]
    original_copy = list(original)

    result = normalize_findings(original)
    assert original == original_copy
    assert len(result) == 1


# 12. Normalization does not calculate or modify scores.
def test_normalization_does_not_add_or_modify_scores():
    f1 = make_finding("1", "AP01", line_start=1, line_end=1)
    result = normalize_findings([f1])
    assert not hasattr(result[0], "score")
