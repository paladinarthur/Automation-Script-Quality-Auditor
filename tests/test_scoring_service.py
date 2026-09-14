import pytest
from src.models.enums import Confidence, RatingBand, Severity
from src.models.finding import Finding
from src.models.input import ScriptInput
from src.services.audit_service import audit_script
from src.services.scoring_service import calculate_score


def make_finding(
    id: str,
    anti_pattern_id: str,
    severity: Severity = Severity.MEDIUM,
    confidence: Confidence = Confidence.HIGH,
    line_start: int = 1,
    line_end: int = 1,
    code_snippet: str = "code()",
    reason: str = "reason",
) -> Finding:
    return Finding(
        id=id,
        anti_pattern_id=anti_pattern_id,
        anti_pattern_name=f"Pattern {anti_pattern_id}",
        severity=severity,
        confidence=confidence,
        line_start=line_start,
        line_end=line_end,
        code_snippet=code_snippet,
        reason=reason,
        explanation="",
        suggested_fix="",
    )


# 1. Empty findings -> 100 / Excellent.
def test_empty_findings_scores_100_excellent():
    scorecard = calculate_score([])
    assert scorecard.overall_score == 100
    assert scorecard.rating == RatingBand.EXCELLENT
    assert scorecard.total_issues == 0
    assert scorecard.high_severity_count == 0
    assert scorecard.medium_severity_count == 0
    assert scorecard.anti_patterns_detected == 0
    assert scorecard.category_breakdown == {}


# 2. One High finding -> 90 / Excellent.
def test_one_high_finding_scores_90():
    f = make_finding("1", "AP01", severity=Severity.HIGH)
    card = calculate_score([f])
    assert card.overall_score == 90
    assert card.rating == RatingBand.EXCELLENT
    assert card.total_issues == 1
    assert card.high_severity_count == 1
    assert card.medium_severity_count == 0
    assert card.anti_patterns_detected == 1
    assert card.category_breakdown == {"AP01": 10}


# 3. One Medium finding -> 96 / Excellent.
def test_one_medium_finding_scores_96():
    f = make_finding("1", "AP02", severity=Severity.MEDIUM)
    card = calculate_score([f])
    assert card.overall_score == 96
    assert card.rating == RatingBand.EXCELLENT
    assert card.total_issues == 1
    assert card.high_severity_count == 0
    assert card.medium_severity_count == 1
    assert card.anti_patterns_detected == 1
    assert card.category_breakdown == {"AP02": 4}


# 4. Two High findings for the same AP -> 80 / Excellent.
def test_two_high_findings_same_ap_scores_80():
    f1 = make_finding("1", "AP01", severity=Severity.HIGH, line_start=1)
    f2 = make_finding("2", "AP01", severity=Severity.HIGH, line_start=5)
    card = calculate_score([f1, f2])
    assert card.overall_score == 80
    assert card.rating == RatingBand.EXCELLENT
    assert card.total_issues == 2
    assert card.high_severity_count == 2
    assert card.category_breakdown == {"AP01": 20}


# 5. Three High findings for the same AP -> still 80 (capped at -20).
def test_three_high_findings_same_ap_capped_at_20():
    f1 = make_finding("1", "AP01", severity=Severity.HIGH, line_start=1)
    f2 = make_finding("2", "AP01", severity=Severity.HIGH, line_start=5)
    f3 = make_finding("3", "AP01", severity=Severity.HIGH, line_start=10)
    card = calculate_score([f1, f2, f3])
    assert card.overall_score == 80
    assert card.rating == RatingBand.EXCELLENT
    assert card.total_issues == 3
    assert card.category_breakdown == {"AP01": 20}


# 6. Five Medium findings for the same AP -> 80 (capped at -20).
def test_five_medium_findings_same_ap_capped_at_20():
    findings = [
        make_finding(str(i), "AP02", severity=Severity.MEDIUM, line_start=i)
        for i in range(1, 6)
    ]
    card = calculate_score(findings)
    assert card.overall_score == 80
    assert card.rating == RatingBand.EXCELLENT
    assert card.total_issues == 5
    assert card.category_breakdown == {"AP02": 20}


# 7. Multiple anti-patterns with mixed severities calculate correctly.
# Example from spec: AP01 (1 High = 10), AP02 (2 Medium = 8), AP06 (3 Medium = 12), AP07 (1 High = 10) -> total penalty 40 -> score 60 Good
def test_mixed_anti_patterns_example_from_spec():
    f_ap01 = [make_finding("1", "AP01", severity=Severity.HIGH, line_start=1)]
    f_ap02 = [make_finding(str(i), "AP02", severity=Severity.MEDIUM, line_start=i + 5) for i in range(2)]
    f_ap06 = [make_finding(str(i), "AP06", severity=Severity.MEDIUM, line_start=i + 10) for i in range(3)]
    f_ap07 = [make_finding("10", "AP07", severity=Severity.HIGH, line_start=20)]

    all_findings = f_ap01 + f_ap02 + f_ap06 + f_ap07
    card = calculate_score(all_findings)
    assert card.overall_score == 60
    assert card.rating == RatingBand.GOOD
    assert card.total_issues == 7
    assert card.high_severity_count == 2
    assert card.medium_severity_count == 5
    assert card.anti_patterns_detected == 4
    assert card.category_breakdown == {
        "AP01": 10,
        "AP02": 8,
        "AP06": 12,
        "AP07": 10,
    }


# 8. Score floors at 0.
def test_score_floors_at_zero():
    # 6 distinct AP categories with 2 High findings each (-20 * 6 = -120 penalty)
    findings = []
    ap_list = ["AP01", "AP04", "AP07", "AP08", "AP09", "AP10"]
    for idx, ap in enumerate(ap_list):
        findings.append(make_finding(f"{ap}-1", ap, severity=Severity.HIGH, line_start=idx * 2 + 1))
        findings.append(make_finding(f"{ap}-2", ap, severity=Severity.HIGH, line_start=idx * 2 + 2))

    card = calculate_score(findings)
    assert card.overall_score == 0
    assert card.rating == RatingBand.POOR


# 9. Rating boundaries testing.
@pytest.mark.parametrize(
    "findings, expected_score, expected_rating",
    [
        ([], 100, RatingBand.EXCELLENT),
        ([make_finding("1", "AP01", severity=Severity.HIGH, line_start=1), make_finding("2", "AP01", severity=Severity.HIGH, line_start=2)], 80, RatingBand.EXCELLENT),
        ([make_finding("1", "AP01", severity=Severity.HIGH, line_start=1), make_finding("2", "AP01", severity=Severity.HIGH, line_start=2), make_finding("3", "AP02", severity=Severity.MEDIUM, line_start=3)], 76, RatingBand.GOOD),
        ([make_finding(str(i), f"AP0{i}", severity=Severity.HIGH, line_start=i) for i in (1, 4, 7, 8)], 60, RatingBand.GOOD),
        ([make_finding(str(i), f"AP0{i}", severity=Severity.HIGH, line_start=i) for i in (1, 4, 7, 8)] + [make_finding("9", "AP02", severity=Severity.MEDIUM, line_start=9)], 56, RatingBand.FAIR),
        ([make_finding(str(i), f"AP0{i}", severity=Severity.HIGH, line_start=i) for i in (1, 4, 7, 8, 9)], 50, RatingBand.FAIR),
        ([make_finding(str(i), f"AP0{i}", severity=Severity.HIGH, line_start=i) for i in (1, 4, 7, 8, 9)] + [make_finding("10", "AP02", severity=Severity.MEDIUM, line_start=10)], 46, RatingBand.POOR),
    ],
)
def test_rating_boundaries(findings, expected_score, expected_rating):
    card = calculate_score(findings)
    assert card.overall_score == expected_score
    assert card.rating == expected_rating


# 10. Confidence does not affect score.
def test_confidence_does_not_affect_score():
    f_high_conf = make_finding("1", "AP02", severity=Severity.MEDIUM, confidence=Confidence.HIGH)
    f_low_conf = make_finding("2", "AP02", severity=Severity.MEDIUM, confidence=Confidence.LOW)

    card1 = calculate_score([f_high_conf])
    card2 = calculate_score([f_low_conf])

    assert card1.overall_score == card2.overall_score == 96


# 11. Anti-pattern count does not directly affect score.
def test_anti_pattern_count_does_not_directly_affect_score():
    # 2 Medium findings in 1 AP category -> -8 penalty -> 92
    f_single_cat = [
        make_finding("1", "AP02", severity=Severity.MEDIUM, line_start=1),
        make_finding("2", "AP02", severity=Severity.MEDIUM, line_start=2),
    ]
    # 2 Medium findings in 2 distinct AP categories -> -8 penalty -> 92
    f_multi_cat = [
        make_finding("1", "AP02", severity=Severity.MEDIUM, line_start=1),
        make_finding("2", "AP06", severity=Severity.MEDIUM, line_start=2),
    ]

    card1 = calculate_score(f_single_cat)
    card2 = calculate_score(f_multi_cat)

    assert card1.overall_score == card2.overall_score == 92
    assert card1.anti_patterns_detected == 1
    assert card2.anti_patterns_detected == 2


# 12. Finding metadata remains untouched.
def test_finding_metadata_remains_untouched():
    f = make_finding("f1", "AP01", severity=Severity.HIGH, line_start=10, line_end=12, code_snippet="time.sleep(5)", reason="sleep")
    calculate_score([f])
    assert f.id == "f1"
    assert f.anti_pattern_id == "AP01"
    assert f.severity == Severity.HIGH
    assert f.line_start == 10
    assert f.line_end == 12
    assert f.code_snippet == "time.sleep(5)"
    assert f.reason == "sleep"


# 13. Category breakdown is deterministic.
def test_category_breakdown_is_deterministic():
    f1 = make_finding("1", "AP06", severity=Severity.MEDIUM, line_start=1)
    f2 = make_finding("2", "AP01", severity=Severity.HIGH, line_start=2)
    card = calculate_score([f1, f2])
    assert list(card.category_breakdown.keys()) == ["AP01", "AP06"]
    assert card.category_breakdown == {"AP01": 10, "AP06": 4}


# 14. AP03 and AP05 can both contribute when both are present.
def test_ap03_and_ap05_both_contribute():
    f_ap03 = make_finding("1", "AP03", severity=Severity.MEDIUM, line_start=1)
    f_ap05 = make_finding("2", "AP05", severity=Severity.MEDIUM, line_start=10)

    card = calculate_score([f_ap03, f_ap05])
    assert card.overall_score == 92  # 100 - 4 - 4
    assert card.category_breakdown == {"AP03": 4, "AP05": 4}


# 15. Findings from normalization are what get scored.
def test_scoring_pipeline_with_normalized_findings():
    # If raw findings had AP01/AP02 overlap, passing through normalization first ensures clean scoring
    f_ap01 = make_finding("AP01-L5", "AP01", severity=Severity.HIGH, line_start=5, line_end=5, code_snippet="time.sleep(5)")
    f_ap02 = make_finding("AP02-L5", "AP02", severity=Severity.MEDIUM, line_start=5, line_end=5, code_snippet="time.sleep(5)")

    from src.services.normalization_service import normalize_findings
    normalized = normalize_findings([f_ap01, f_ap02])
    card = calculate_score(normalized)

    assert card.overall_score == 90
    assert card.total_issues == 1
    assert card.category_breakdown == {"AP01": 10}





# 16. No floating-point scoring is introduced.
def test_no_floating_point_scoring():
    f = make_finding("1", "AP02", severity=Severity.MEDIUM)
    card = calculate_score([f])
    assert isinstance(card.overall_score, int)
    assert isinstance(card.high_severity_count, int)
    assert isinstance(card.medium_severity_count, int)
    assert isinstance(card.total_issues, int)
    assert all(isinstance(v, int) for v in card.category_breakdown.values())


# Integration test: Audit -> Normalization -> Scoring
def test_audit_normalization_scoring_integration():
    script_input = ScriptInput(
        script_content="import time\ntime.sleep(5)\n",
        framework="selenium",
        language="python",
    )
    raw_findings = audit_script(script_input)
    scorecard = calculate_score(raw_findings)

    assert scorecard.overall_score == 90
    assert scorecard.rating == RatingBand.EXCELLENT
    assert scorecard.total_issues == 1
    assert scorecard.high_severity_count == 1
    assert scorecard.medium_severity_count == 0
    assert scorecard.category_breakdown == {"AP01": 10}
