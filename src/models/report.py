"""
AuditReport data model representing the final assembled audit report.
"""

from dataclasses import dataclass, field
from typing import Any
from .finding import Finding
from .scorecard import ScoreCard


@dataclass
class AuditReport:
    """
    Represents the complete audit report presented to the user.

    Aggregates scorecard metrics, confirmed findings (supports 0 findings),
    executive summary, recommendations, and methodology notes.
    """

    scorecard: ScoreCard
    findings: list[Finding] = field(default_factory=list)
    executive_summary: dict[str, Any] = field(default_factory=dict)
    recommendations: dict[str, list[str]] = field(default_factory=dict)
    methodology: list[str] = field(default_factory=list)
