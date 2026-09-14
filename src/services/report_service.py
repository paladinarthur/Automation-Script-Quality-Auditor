"""
Report Generator Service for Automation Script Quality Auditor.

Responsibilities:
- Assembles the final `AuditReport` from normalized `Finding` objects and `ScoreCard`.
- Generates 5 structured report sections:
  1. Executive Summary: High-level overview of overall score, rating, total issues, severity counts, and anti-pattern categories.
  2. Scorecard: Embedded unmodified ScoreCard metrics.
  3. Findings: List of confirmed normalized findings preserving all metadata.
  4. Recommendations: High-severity recommendations followed by Medium-severity recommendations.
  5. Methodology: Static analysis approach, checklist rules, deduplication, scoring formula, and Gemini advisory boundaries.

Deliberate Design Boundaries:
- Assembles existing data only: does NOT make detection decisions or modify findings/scoring.
- Purely deterministic: produces identical reports for identical inputs without random values or network calls.
- Independent of AI: does NOT call Gemini or generate AI fixes.
- Static analysis presentation layer: does NOT execute user scripts or access browsers.
"""

import logging
from src.models.enums import Severity
from src.models.finding import Finding
from src.models.report import AuditReport
from src.models.scorecard import ScoreCard

logger = logging.getLogger(__name__)

# Standard methodology notes describing auditor design boundaries and rules
_METHODOLOGY_NOTES = [
    "Static Analysis Only: The auditor performs deterministic static analysis without executing browser automation scripts.",
    "Checklist Based: Evaluates code against the 10 fixed anti-pattern rules (AP01–AP10).",
    "Normalization & Deduplication: Raw findings undergo exact deduplication and AP01 fixed-delay overlap resolution prior to scoring.",
    "Deterministic Scoring Formula: Base score starts at 100 points. High-severity issues deduct 10 points; Medium-severity issues deduct 4 points.",
    "Penalty Cap: Each anti-pattern category penalty is capped at a maximum of 20 points, with a final score floor of 0.",
    "Gemini Advisory Boundary: Gemini is strictly an advisory post-scoring layer for contextual explanations and suggested fixes; it cannot alter scores, severities, or detection findings.",
    "Secret Protection: Secrets detected by AP09 are sanitized ([REDACTED]) before any optional external AI processing.",
]


def _build_executive_summary(findings: list[Finding], scorecard: ScoreCard) -> dict:
    """Builds a deterministic executive summary dictionary."""
    if not findings:
        summary_text = (
            f"Automation script scored {scorecard.overall_score}/100 ({scorecard.rating.value}). "
            "No checklist anti-patterns were detected."
        )
    else:
        summary_text = (
            f"Automation script scored {scorecard.overall_score}/100 ({scorecard.rating.value}) "
            f"with {scorecard.total_issues} issue(s) detected across "
            f"{scorecard.anti_patterns_detected} anti-pattern category(ies)."
        )

    # Collect distinct anti-pattern names detected
    detected_categories = sorted(list(scorecard.category_breakdown.keys()))

    return {
        "summary": summary_text,
        "overall_score": scorecard.overall_score,
        "rating": scorecard.rating.value,
        "total_issues": scorecard.total_issues,
        "high_severity_count": scorecard.high_severity_count,
        "medium_severity_count": scorecard.medium_severity_count,
        "anti_patterns_detected": scorecard.anti_patterns_detected,
        "detected_categories": detected_categories,
    }


def _build_recommendations(findings: list[Finding]) -> dict[str, list[str]]:
    """Builds deterministic recommendations grouped by priority (High severity first, then Medium)."""
    if not findings:
        return {
            "high_priority": [],
            "medium_priority": [],
            "note": ["No checklist-specific recommendations required."],
        }

    high_recs: list[str] = []
    medium_recs: list[str] = []

    # Map anti_pattern_id to a concise recommendation template
    # Unique recommendations per anti-pattern ID to avoid duplicate generic advice
    seen_ap_high: set[str] = set()
    seen_ap_medium: set[str] = set()

    for f in findings:
        ap_id = f.anti_pattern_id
        title = f.anti_pattern_name
        
        if f.severity == Severity.HIGH:
            if ap_id not in seen_ap_high:
                seen_ap_high.add(ap_id)
                high_recs.append(f"[{ap_id} - {title}] Resolve high-severity issues (e.g. line {f.line_start}): {f.reason}")
        else:
            if ap_id not in seen_ap_medium:
                seen_ap_medium.add(ap_id)
                medium_recs.append(f"[{ap_id} - {title}] Address medium-severity issues (e.g. line {f.line_start}): {f.reason}")

    return {
        "high_priority": high_recs,
        "medium_priority": medium_recs,
    }


def generate_report(findings: list[Finding], scorecard: ScoreCard) -> AuditReport:
    """
    Assembles an AuditReport object from normalized findings and calculated scorecard.

    Args:
        findings: List of normalized Finding objects.
        scorecard: Calculated ScoreCard object.

    Returns:
        AuditReport containing executive summary, scorecard, findings, recommendations, and methodology.
    """
    exec_summary = _build_executive_summary(findings, scorecard)
    recommendations = _build_recommendations(findings)

    return AuditReport(
        scorecard=scorecard,
        findings=list(findings),
        executive_summary=exec_summary,
        recommendations=recommendations,
        methodology=list(_METHODOLOGY_NOTES),
    )
