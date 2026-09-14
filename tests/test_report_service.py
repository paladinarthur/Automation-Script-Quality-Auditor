import pytest
from src.models.enums import Confidence, RatingBand, Severity
from src.models.finding import Finding
from src.models.scorecard import ScoreCard
from src.models.input import ScriptInput
from src.services.report_service import generate_report
from src.services.scoring_service import calculate_score
from src.services.audit_service import audit_script


def make_finding(
    id: str,
    anti_pattern_id: str,
    anti_pattern_name: str = "Test Pattern",
    severity: Severity = Severity.MEDIUM,
    confidence: Confidence = Confidence.HIGH,
    line_start: int = 1,
    line_end: int = 1,
    code_snippet: str = "code()",
    reason: str = "Test reason",
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


# 1. Report generation with zero findings.
def test_generate_report_zero_findings():
    scorecard = ScoreCard(
        overall_score=100,
        rating=RatingBand.EXCELLENT,
        total_issues=0,
        high_severity_count=0,
        medium_severity_count=0,
        anti_patterns_detected=0,
        category_breakdown={},
    )
    report = generate_report([], scorecard)

    assert report.scorecard == scorecard
    assert report.findings == []
    assert report.executive_summary["overall_score"] == 100
    assert report.executive_summary["rating"] == "Excellent"
    assert report.executive_summary["total_issues"] == 0
    assert "No checklist anti-patterns were detected" in report.executive_summary["summary"]


# 2. Report generation with one High finding.
def test_generate_report_one_high_finding():
    f = make_finding("1", "AP01", "Hardcoded Waits", severity=Severity.HIGH, line_start=5)
    scorecard = calculate_score([f])

    report = generate_report([f], scorecard)

    assert report.scorecard.overall_score == 90
    assert len(report.findings) == 1
    assert report.findings[0] == f
    assert report.executive_summary["high_severity_count"] == 1
    assert len(report.recommendations["high_priority"]) == 1
    assert len(report.recommendations["medium_priority"]) == 0


# 3. Report generation with multiple findings.
def test_generate_report_multiple_findings():
    f1 = make_finding("1", "AP01", "Hardcoded Waits", severity=Severity.HIGH, line_start=5)
    f2 = make_finding("2", "AP02", "Magic Numbers", severity=Severity.MEDIUM, line_start=10)
    scorecard = calculate_score([f1, f2])

    report = generate_report([f1, f2], scorecard)

    assert report.scorecard.overall_score == 86
    assert len(report.findings) == 2
    assert report.executive_summary["total_issues"] == 2
    assert report.executive_summary["high_severity_count"] == 1
    assert report.executive_summary["medium_severity_count"] == 1


# 4. Executive summary reflects the supplied ScoreCard.
def test_executive_summary_reflects_scorecard():
    scorecard = ScoreCard(
        overall_score=72,
        rating=RatingBand.GOOD,
        total_issues=3,
        high_severity_count=1,
        medium_severity_count=2,
        anti_patterns_detected=2,
        category_breakdown={"AP01": 10, "AP02": 8},
    )
    findings = [
        make_finding("1", "AP01", severity=Severity.HIGH, line_start=1),
        make_finding("2", "AP02", severity=Severity.MEDIUM, line_start=2),
        make_finding("3", "AP02", severity=Severity.MEDIUM, line_start=3),
    ]

    report = generate_report(findings, scorecard)

    summary = report.executive_summary
    assert summary["overall_score"] == 72
    assert summary["rating"] == "Good"
    assert summary["total_issues"] == 3
    assert summary["high_severity_count"] == 1
    assert summary["medium_severity_count"] == 2
    assert summary["anti_patterns_detected"] == 2
    assert summary["detected_categories"] == ["AP01", "AP02"]


# 5. ScoreCard is preserved and not recalculated.
def test_scorecard_is_preserved_unmodified():
    # Pass a scorecard with custom metrics and ensure report does not recalculate it
    scorecard = ScoreCard(
        overall_score=88,
        rating=RatingBand.EXCELLENT,
        total_issues=1,
        high_severity_count=0,
        medium_severity_count=1,
        anti_patterns_detected=1,
        category_breakdown={"AP06": 4},
    )
    f = make_finding("1", "AP06", severity=Severity.MEDIUM)

    report = generate_report([f], scorecard)
    assert report.scorecard == scorecard
    assert report.scorecard.overall_score == 88


# 6. Findings are preserved without modification.
def test_findings_preserved_without_modification():
    f = make_finding(
        id="AP09-L10",
        anti_pattern_id="AP09",
        anti_pattern_name="Hardcoded Secrets",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        line_start=10,
        line_end=10,
        code_snippet="api_key = '[REDACTED]'",
        reason="Hardcoded secret detected",
    )
    scorecard = calculate_score([f])

    report = generate_report([f], scorecard)

    assert len(report.findings) == 1
    res = report.findings[0]
    assert res.id == "AP09-L10"
    assert res.anti_pattern_id == "AP09"
    assert res.anti_pattern_name == "Hardcoded Secrets"
    assert res.severity == Severity.HIGH
    assert res.confidence == Confidence.HIGH
    assert res.line_start == 10
    assert res.line_end == 10
    assert res.code_snippet == "api_key = '[REDACTED]'"
    assert res.reason == "Hardcoded secret detected"


# 7. Recommendations are deterministic and ordered High before Medium.
def test_recommendations_ordered_high_before_medium():
    f_med = make_finding("1", "AP02", severity=Severity.MEDIUM, line_start=10)
    f_high = make_finding("2", "AP01", severity=Severity.HIGH, line_start=5)
    scorecard = calculate_score([f_med, f_high])

    report = generate_report([f_med, f_high], scorecard)

    recs = report.recommendations
    assert "high_priority" in recs
    assert "medium_priority" in recs
    assert len(recs["high_priority"]) == 1
    assert len(recs["medium_priority"]) == 1
    assert "[AP01 - " in recs["high_priority"][0]
    assert "[AP02 - " in recs["medium_priority"][0]


# 8. No findings produce no checklist-specific recommendations.
def test_no_findings_produces_no_checklist_recommendations():
    scorecard = ScoreCard(
        overall_score=100,
        rating=RatingBand.EXCELLENT,
        total_issues=0,
        high_severity_count=0,
        medium_severity_count=0,
        anti_patterns_detected=0,
        category_breakdown={},
    )
    report = generate_report([], scorecard)

    assert report.recommendations["high_priority"] == []
    assert report.recommendations["medium_priority"] == []
    assert "note" in report.recommendations
    assert "No checklist-specific recommendations required." in report.recommendations["note"]


# 9. Methodology contains agreed static-analysis/scoring/Gemini boundary information.
def test_methodology_contains_boundary_information():
    scorecard = calculate_score([])
    report = generate_report([], scorecard)

    methodology = " ".join(report.methodology)
    assert "static analysis" in methodology.lower()
    assert "100" in methodology
    assert "10 points" in methodology
    assert "4 points" in methodology
    assert "20 points" in methodology
    assert "gemini" in methodology.lower()
    assert "redacted" in methodology.lower()


# 10. Same input produces the same report.
def test_report_generation_is_deterministic():
    f1 = make_finding("1", "AP01", severity=Severity.HIGH, line_start=2)
    f2 = make_finding("2", "AP06", severity=Severity.MEDIUM, line_start=8)
    scorecard = calculate_score([f1, f2])

    report1 = generate_report([f1, f2], scorecard)
    report2 = generate_report([f1, f2], scorecard)

    assert report1 == report2


# Integration test: Audit -> Normalization -> Scoring -> Report
def test_full_pipeline_audit_to_report():
    script_input = ScriptInput(
        script_content="import time\ntime.sleep(5)\n",
        framework="selenium",
        language="python",
    )
    findings = audit_script(script_input)
    scorecard = calculate_score(findings)
    report = generate_report(findings, scorecard)

    assert report.scorecard.overall_score == 90
    assert len(report.findings) == 1
    assert report.executive_summary["overall_score"] == 90
    assert len(report.recommendations["high_priority"]) == 1
    assert len(report.methodology) == 7
