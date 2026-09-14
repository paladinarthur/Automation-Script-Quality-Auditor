"""
Detectors package for Automation Script Quality Auditor.

Exposes anti-pattern detector modules.
"""

from .ap01_waits import detect_ap01
from .ap02_magic_numbers import detect_ap02
from .ap03_duplication import detect_ap03
from .ap04_test_structure import detect_ap04
from .ap05_abstractions import detect_ap05
from .ap06_fragile_locators import detect_ap06
from .ap07_missing_assertions import detect_ap07
from .ap08_implementation_details import detect_ap08

__all__ = [
    "detect_ap01",
    "detect_ap02",
    "detect_ap03",
    "detect_ap04",
    "detect_ap05",
    "detect_ap06",
    "detect_ap07",
    "detect_ap08",
]
