"""
AP01 — Hardcoded Waits Detector.

Performs deterministic static analysis to detect hardcoded numeric delays across
Selenium (Python), Playwright (Python, JS, TS), and Cypress (JS, TS).
"""

import re
from src.models import Confidence, Finding, Framework, Language, Severity

# Regex patterns targeting fixed numeric delay arguments
_TIME_SLEEP_PATTERN = re.compile(r"\btime\.sleep\s*\(\s*(\d+(?:\.\d+)?)\s*\)")
_PLAYWRIGHT_PY_WAIT_PATTERN = re.compile(
    r"(?:\b\w+\.)?wait_for_timeout\s*\(\s*(\d+(?:\.\d+)?)\s*\)"
)
_PLAYWRIGHT_JS_WAIT_PATTERN = re.compile(
    r"(?:\b\w+\.)?waitForTimeout\s*\(\s*(\d+(?:\.\d+)?)\s*\)"
)
_CYPRESS_WAIT_PATTERN = re.compile(r"\bcy\.wait\s*\(\s*(\d+(?:\.\d+)?)\s*(?:,|\))")


def _normalize_framework(framework: Framework | str) -> Framework | None:
    """Normalizes string or enum to Framework enum."""
    if isinstance(framework, Framework):
        return framework
    if isinstance(framework, str):
        val = framework.strip().lower()
        for member in Framework:
            if member.value == val or member.name.lower() == val:
                return member
    return None


def _normalize_language(language: Language | str) -> Language | None:
    """Normalizes string or enum to Language enum."""
    if isinstance(language, Language):
        return language
    if isinstance(language, str):
        val = language.strip().lower()
        for member in Language:
            if member.value == val or member.name.lower() == val:
                return member
    return None


def _get_active_patterns(framework: Framework, language: Language) -> list[re.Pattern]:
    """Returns the list of compiled regex patterns active for the given framework & language."""
    if framework == Framework.SELENIUM and language == Language.PYTHON:
        return [_TIME_SLEEP_PATTERN]

    if framework == Framework.PLAYWRIGHT and language == Language.PYTHON:
        return [_TIME_SLEEP_PATTERN, _PLAYWRIGHT_PY_WAIT_PATTERN]

    if framework == Framework.PLAYWRIGHT and language in (
        Language.JAVASCRIPT,
        Language.TYPESCRIPT,
    ):
        return [_PLAYWRIGHT_JS_WAIT_PATTERN]

    if framework == Framework.CYPRESS and language in (
        Language.JAVASCRIPT,
        Language.TYPESCRIPT,
    ):
        return [_CYPRESS_WAIT_PATTERN]

    return []


def _is_comment_line(stripped_line: str, language: Language) -> bool:
    """Checks if a stripped line is purely a comment."""
    if language == Language.PYTHON:
        return (
            stripped_line.startswith("#")
            or (stripped_line.startswith('"""') and stripped_line.endswith('"""') and len(stripped_line) >= 6)
            or (stripped_line.startswith("'''") and stripped_line.endswith("'''") and len(stripped_line) >= 6)
        )
    # JavaScript / TypeScript
    return (
        stripped_line.startswith("//")
        or stripped_line.startswith("/*")
        or stripped_line.startswith("*")
    )


def _is_match_in_comment(line: str, match_start: int, language: Language) -> bool:
    """Checks if an inline comment indicator precedes the match position on the same line."""
    prefix = line[:match_start]
    if language == Language.PYTHON:
        return "#" in prefix
    # JavaScript / TypeScript: check for // outside http:// or https://
    if "//" in prefix:
        # Ignore // when part of URL protocol (http:// or https://)
        cleaned = prefix.replace("https://", "").replace("http://", "")
        if "//" in cleaned:
            return True
    if "/*" in prefix:
        last_block_start = prefix.rfind("/*")
        last_block_end = prefix.rfind("*/")
        if last_block_start > last_block_end:
            return True
    return False


def detect_ap01(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP01 (Hardcoded Waits) in the provided script content.

    Rules:
    - Selenium + Python: time.sleep(number)
    - Playwright + Python: time.sleep(number), page.wait_for_timeout(number)
    - Playwright + JS/TS: page.waitForTimeout(number)
    - Cypress + JS/TS: cy.wait(number)

    Excludes:
    - Condition-based waits (WebDriverWait, etc.)
    - Cypress alias waits (cy.wait('@alias'), cy.wait(['@a', '@b']))
    - Commented-out lines and inline comments

    Returns:
        List of Finding objects, each with severity HIGH and confidence HIGH.
    """
    if not script_content or not script_content.strip():
        return []

    parsed_framework = _normalize_framework(framework)
    parsed_language = _normalize_language(language)

    if parsed_framework is None or parsed_language is None:
        return []

    active_patterns = _get_active_patterns(parsed_framework, parsed_language)
    if not active_patterns:
        return []

    findings: list[Finding] = []
    lines = script_content.splitlines()
    in_block_comment = False
    in_py_docstring = False
    py_docstring_delim = ""

    for line_num, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        # Handle Python multi-line docstrings (""" or ''')
        if parsed_language == Language.PYTHON:
            if in_py_docstring:
                if py_docstring_delim in raw_line:
                    in_py_docstring = False
                continue
            for delim in ('"""', "'''"):
                if stripped.startswith(delim):
                    if stripped.count(delim) % 2 == 1:
                        in_py_docstring = True
                        py_docstring_delim = delim
                    break
            if in_py_docstring:
                continue

        # Handle JS/TS block comments (/* ... */)
        if parsed_language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith("/*"):
                if "*/" not in stripped:
                    in_block_comment = True
                continue

        # Skip full-line comments
        if _is_comment_line(stripped, parsed_language):
            continue

        # Check for active wait patterns
        for pattern in active_patterns:
            match = pattern.search(raw_line)
            if match:
                # Ensure match is not preceded by an inline comment delimiter
                if _is_match_in_comment(raw_line, match.start(), parsed_language):
                    continue

                findings.append(
                    Finding(
                        id=f"AP01-L{line_num}",
                        anti_pattern_id="AP01",
                        anti_pattern_name="Hardcoded Waits",
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                        reason="Fixed delay is used instead of waiting for a specific application condition.",
                    )
                )
                # Only flag once per line even if multiple patterns match
                break

    return findings
