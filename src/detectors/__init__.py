"""
Detectors package for Automation Script Quality Auditor.

Exposes anti-pattern detector modules.
"""

from .ap01_waits import detect_ap01
from .ap02_magic_numbers import detect_ap02
from .ap03_duplication import detect_ap03
from .ap04_test_structure import detect_ap04

__all__ = [
    "detect_ap01",
    "detect_ap02",
    "detect_ap03",
    "detect_ap04",
]
