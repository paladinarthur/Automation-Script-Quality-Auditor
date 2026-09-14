"""
ScoreCard data model representing the deterministic quality score result.
"""

from dataclasses import dataclass, field
from .enums import RatingBand


@dataclass
class ScoreCard:
    """
    Represents the deterministic audit scorecard.

    Calculation is performed exclusively by the scoring engine; this model
    stores the calculated score, rating band, and issue counts.
    """

    overall_score: int
    rating: RatingBand
    total_issues: int
    high_severity_count: int
    medium_severity_count: int
    anti_patterns_detected: int
    category_breakdown: dict[str, int] = field(default_factory=dict)
