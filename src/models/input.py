"""
ScriptInput data model representing the user's submitted script payload.
"""

from dataclasses import dataclass
from .enums import Framework, Language


@dataclass
class ScriptInput:
    """
    Structured representation of script input submitted for audit.
    Captures raw code content, target framework, and language.
    """

    script_content: str
    framework: Framework | str
    language: Language | str
