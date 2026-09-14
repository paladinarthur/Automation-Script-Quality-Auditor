"""
Unit tests for shared domain data models (Finding, ScoreCard, AuditReport, ScriptInput).
Validates model construction, enum mappings, default values, and data integrity.
"""

from src.models import (
    AuditReport,
    Confidence,
    Finding,
    Framework,
    Language,
    RatingBand,
    ScoreCard,
    ScriptInput,
    Severity,
)


def test_finding_construction_with_defaults():
    """Verify Finding can be constructed with valid data and default explanation/fix."""
    finding = Finding(
        id="finding-1",
        anti_pattern_id="AP01",
        anti_pattern_name="Hardcoded Waits",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        line_start=14,
        line_end=14,
        code_snippet="time.sleep(5)",
        reason="Fixed delay is used instead of waiting for condition.",
    )

    assert finding.id == "finding-1"
    assert finding.anti_pattern_id == "AP01"
    assert finding.anti_pattern_name == "Hardcoded Waits"
    assert finding.title == "Hardcoded Waits"
    assert finding.severity == Severity.HIGH
    assert finding.severity == "High"
    assert finding.confidence == Confidence.HIGH
    assert finding.confidence == "High"
    assert finding.line_start == 14
    assert finding.line_end == 14
    assert finding.code_snippet == "time.sleep(5)"
    assert finding.reason == "Fixed delay is used instead of waiting for condition."
    assert finding.explanation == ""
    assert finding.suggested_fix == ""
    assert finding.line_display == "Line 14"


def test_finding_with_line_range_and_ai_enrichment():
    """Verify Finding correctly handles line ranges and post-detection AI enrichment fields."""
    finding = Finding(
        id="finding-2",
        anti_pattern_id="AP03",
        anti_pattern_name="Copy-Paste / Duplicated Code",
        severity=Severity.MEDIUM,
        confidence=Confidence.MEDIUM,
        line_start=12,
        line_end=15,
        code_snippet="page.fill('#username', user)\npage.fill('#password', pwd)",
        reason="Duplicated 4-statement interaction block detected.",
        explanation="Repeated authentication interaction sequence violates DRY principles.",
        suggested_fix="Extract login sequence into a reusable helper method.",
    )

    assert finding.severity == Severity.MEDIUM
    assert finding.confidence == Confidence.MEDIUM
    assert finding.line_start == 12
    assert finding.line_end == 15
    assert finding.line_display == "Lines 12–15"
    assert finding.explanation != ""
    assert finding.suggested_fix != ""


def test_scorecard_perfect_score():
    """Verify ScoreCard can represent a clean 100/100 Excellent result with zero issues."""
    scorecard = ScoreCard(
        overall_score=100,
        rating=RatingBand.EXCELLENT,
        total_issues=0,
        high_severity_count=0,
        medium_severity_count=0,
        anti_patterns_detected=0,
    )

    assert scorecard.overall_score == 100
    assert scorecard.rating == RatingBand.EXCELLENT
    assert scorecard.rating == "Excellent"
    assert scorecard.total_issues == 0
    assert scorecard.high_severity_count == 0
    assert scorecard.medium_severity_count == 0
    assert scorecard.anti_patterns_detected == 0
    assert scorecard.category_breakdown == {}


def test_scorecard_rating_bands():
    """Verify ScoreCard supports all 4 approved rating bands with category breakdowns."""
    bands = [
        (85, RatingBand.EXCELLENT),
        (72, RatingBand.GOOD),
        (55, RatingBand.FAIR),
        (35, RatingBand.POOR),
    ]

    for score, expected_band in bands:
        card = ScoreCard(
            overall_score=score,
            rating=expected_band,
            total_issues=3,
            high_severity_count=1,
            medium_severity_count=2,
            anti_patterns_detected=2,
            category_breakdown={"AP01": 1, "AP06": 2},
        )
        assert card.overall_score == score
        assert card.rating == expected_band
        assert card.category_breakdown["AP01"] == 1


def test_audit_report_with_zero_findings():
    """Verify AuditReport supports clean runs with zero findings."""
    scorecard = ScoreCard(
        overall_score=100,
        rating=RatingBand.EXCELLENT,
        total_issues=0,
        high_severity_count=0,
        medium_severity_count=0,
        anti_patterns_detected=0,
    )
    report = AuditReport(
        scorecard=scorecard,
        findings=[],
        executive_summary={"summary": "Clean script with no anti-patterns."},
        recommendations={"high_priority": [], "medium_priority": []},
        methodology=["Static AST & Regex pattern matching"],
    )

    assert report.scorecard.overall_score == 100
    assert len(report.findings) == 0
    assert report.executive_summary["summary"] == "Clean script with no anti-patterns."
    assert len(report.recommendations["high_priority"]) == 0
    assert len(report.methodology) == 1


def test_audit_report_with_findings():
    """Verify AuditReport aggregates scorecard, findings list, and metadata."""
    finding = Finding(
        id="f-1",
        anti_pattern_id="AP01",
        anti_pattern_name="Hardcoded Waits",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        line_start=20,
        line_end=20,
        code_snippet="time.sleep(10)",
        reason="Fixed sleep duration detected.",
    )
    scorecard = ScoreCard(
        overall_score=90,
        rating=RatingBand.EXCELLENT,
        total_issues=1,
        high_severity_count=1,
        medium_severity_count=0,
        anti_patterns_detected=1,
    )
    report = AuditReport(
        scorecard=scorecard,
        findings=[finding],
    )

    assert report.scorecard.overall_score == 90
    assert len(report.findings) == 1
    assert report.findings[0].anti_pattern_id == "AP01"
    assert report.executive_summary == {}
    assert report.recommendations == {}
    assert report.methodology == []


def test_script_input_model():
    """Verify ScriptInput correctly encapsulates submitted script and framework context."""
    user_input = ScriptInput(
        script_content="import time\ntime.sleep(5)",
        framework=Framework.SELENIUM,
        language=Language.PYTHON,
    )

    assert user_input.script_content == "import time\ntime.sleep(5)"
    assert user_input.framework == Framework.SELENIUM
    assert user_input.framework == "selenium"
    assert user_input.language == Language.PYTHON
    assert user_input.language == "python"
