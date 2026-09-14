"""
Domain Enums for Automation Script Quality Auditor.

Defines strictly controlled categorical values for severity, confidence,
rating bands, frameworks, and programming languages.
"""

from enum import Enum


class Severity(str, Enum):
    """
    Severity rating for an anti-pattern finding.
    Governs deterministic penalty scoring (-10 for High, -4 for Medium).
    """

    HIGH = "High"
    MEDIUM = "Medium"


class Confidence(str, Enum):
    """
    Detection certainty level.
    Communicates detection precision; does NOT affect score calculation.
    """

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RatingBand(str, Enum):
    """
    Qualitative rating mapped from the 0-100 quality score.
    - Excellent: 80-100
    - Good: 60-79
    - Fair: 50-59
    - Poor: 0-49
    """

    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"


class Framework(str, Enum):
    """Supported automation test frameworks."""

    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"
    CYPRESS = "cypress"


class Language(str, Enum):
    """Supported test script programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
