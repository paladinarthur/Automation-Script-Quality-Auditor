"""
Finding data model representing a single confirmed anti-pattern issue.
"""

from dataclasses import dataclass
from .enums import Confidence, Severity


@dataclass
class Finding:
    """
    Represents one confirmed anti-pattern finding.

    Ownership Boundary:
    - Deterministic Detector owns:
        id, anti_pattern_id, anti_pattern_name, severity, confidence,
        line_start, line_end, code_snippet, reason.
    - Advisory Gemini Service owns:
        explanation, suggested_fix.
      Gemini must NEVER modify detector-owned fields.
    """

    id: str
    anti_pattern_id: str
    anti_pattern_name: str
    severity: Severity
    confidence: Confidence
    line_start: int
    line_end: int
    code_snippet: str
    reason: str
    explanation: str = ""
    suggested_fix: str = ""

    @property
    def title(self) -> str:
        """Alias for anti_pattern_name for architectural contract compatibility."""
        return self.anti_pattern_name

    @property
    def line_display(self) -> str:
        """User-friendly line number or line range representation."""
        if self.line_start == self.line_end:
            return f"Line {self.line_start}"
        return f"Lines {self.line_start}–{self.line_end}"
