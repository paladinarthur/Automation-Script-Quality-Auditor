"""
Validation package for Automation Script Quality Auditor.

Exposes framework and language validation components.
"""

from .validator import (
    SUPPORTED_COMBINATIONS,
    ValidationResult,
    get_supported_languages,
    validate_framework_and_language,
)

__all__ = [
    "SUPPORTED_COMBINATIONS",
    "ValidationResult",
    "get_supported_languages",
    "validate_framework_and_language",
]
