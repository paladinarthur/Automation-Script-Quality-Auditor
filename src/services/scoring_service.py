"""
Scoring Engine Service for Automation Script Quality Auditor.

Responsibilities:
- Converts normalized `Finding` objects into a deterministic `ScoreCard`.
- Evaluates severity-based deductions:
  - High severity finding: -10 points
  - Medium severity finding: -4 points
- Applies a maximum penalty cap of -20 points per anti-pattern ID.
- Calculates final overall score: max(0, 100 - total_penalty).
- Maps final score to qualitative rating band:
  - 80–100: Excellent
  - 60–79: Good
  - 50–59: Fair
  - 0–49: Poor
- Generates scorecard metadata (issue counts, anti-patterns detected, deterministic category breakdown).

Deliberate Design Boundaries:
- Isolated from detection and normalization: receives final findings.
- Deterministic scoring only: severity-based rules without floating-point math or arbitrary weighting.
- Does NOT use confidence, script length, lines of code, or issue density in score calculation.
- Does NOT invoke Gemini API, execute code, or render UI.
"""

from collections import defaultdict
from src.models.enums import RatingBand, Severity
from src.models.finding import Finding
from src.models.scorecard import ScoreCard

# Penalty values per finding severity
_SEVERITY_PENALTIES = {
    Severity.HIGH: 10,
    Severity.MEDIUM: 4,
}

# Maximum penalty allowed per single anti-pattern category
_MAX_PENALTY_PER_ANTI_PATTERN = 20


def _derive_rating(score: int) -> RatingBand:
    """Maps an integer score (0-100) to its corresponding RatingBand."""
    if score >= 80:
        return RatingBand.EXCELLENT
    if score >= 60:
        return RatingBand.GOOD
    if score >= 50:
        return RatingBand.FAIR
    return RatingBand.POOR


def calculate_score(findings: list[Finding]) -> ScoreCard:
    """
    Calculates the quality score and populates the ScoreCard model from normalized findings.

    Args:
        findings: List of normalized Finding objects.

    Returns:
        ScoreCard containing overall score, rating band, counts, and category breakdown.
    """
    if not findings:
        return ScoreCard(
            overall_score=100,
            rating=RatingBand.EXCELLENT,
            total_issues=0,
            high_severity_count=0,
            medium_severity_count=0,
            anti_patterns_detected=0,
            category_breakdown={},
        )

    high_count = 0
    medium_count = 0

    # Group findings by anti_pattern_id to apply per-category caps
    findings_by_ap: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        findings_by_ap[f.anti_pattern_id].append(f)
        if f.severity == Severity.HIGH:
            high_count += 1
        elif f.severity == Severity.MEDIUM:
            medium_count += 1

    total_penalty = 0
    category_breakdown: dict[str, int] = {}

    # Process each detected anti-pattern category deterministically by ID
    for ap_id in sorted(findings_by_ap.keys()):
        ap_findings = findings_by_ap[ap_id]
        uncapped_penalty = sum(_SEVERITY_PENALTIES.get(f.severity, 0) for f in ap_findings)
        capped_penalty = min(uncapped_penalty, _MAX_PENALTY_PER_ANTI_PATTERN)
        
        total_penalty += capped_penalty
        category_breakdown[ap_id] = capped_penalty

    overall_score = max(0, 100 - total_penalty)
    rating = _derive_rating(overall_score)

    return ScoreCard(
        overall_score=overall_score,
        rating=rating,
        total_issues=len(findings),
        high_severity_count=high_count,
        medium_severity_count=medium_count,
        anti_patterns_detected=len(findings_by_ap),
        category_breakdown=category_breakdown,
    )
