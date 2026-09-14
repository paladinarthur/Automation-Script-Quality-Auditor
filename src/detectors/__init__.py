"""
Detectors package for Automation Script Quality Auditor.

Exposes anti-pattern detector modules.
"""

from .ap01_waits import detect_ap01

__all__ = [
    "detect_ap01",
]
