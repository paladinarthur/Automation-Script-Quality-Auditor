"""
AP02 — Magic Numbers / Hardcoded Values Detector.

Performs deterministic, heuristic static analysis to detect potential magic numbers
embedded directly in automation logic (timeouts, retries, thresholds, positional
selectors) without meaningful context.

Conservative exclusions:
- 0 and 1
- HTTP status codes (200, 404, etc.)
- Loop / index constructs (range(5), for (let i = 0; i < 5; i++), items[2])
- Named constants (MAX_RETRIES = 7, DEFAULT_TIMEOUT = 30)
- AP01 hardcoded waits (time.sleep, wait_for_timeout, cy.wait)
- Ordinary test data (e.g. age = 25)
- Comments and docstrings
"""

import re
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

# Standard HTTP status codes to exclude from magic number detection
_HTTP_STATUS_CODES = {
    100, 101, 102, 103,
    200, 201, 202, 203, 204, 205, 206, 207, 208, 226,
    300, 301, 302, 303, 304, 305, 307, 308,
    400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410,
    411, 412, 413, 414, 415, 416, 417, 418, 421, 422, 423,
    424, 426, 428, 429, 431, 451,
    500, 501, 502, 503, 504, 505, 506, 507, 508, 510, 511,
}

# AP01 Hardcoded Wait patterns to exclude so AP01 remains the sole finding
_AP01_WAIT_PATTERN = re.compile(
    r"(?:\btime\.sleep|\bwait_for_timeout|\bwaitForTimeout|\bcy\.wait)\s*\(\s*\d+"
)

# Named constant assignment patterns (e.g. MAX_RETRIES = 7, const DEFAULT_TIMEOUT = 30)
_NAMED_CONSTANT_PATTERN = re.compile(
    r"^(?:export\s+)?(?:const\s+|let\s+|var\s+)?([A-Z][A-Z0-9_]*)\s*(?::\s*[^=]+)?\s*=\s*\d+"
)

# Loop constructs to exclude
_PY_RANGE_LOOP_PATTERN = re.compile(r"\bfor\s+\w+\s+in\s+range\s*\(")
_JS_FOR_LOOP_PATTERN = re.compile(r"\bfor\s*\([^)]*\)")

# Automation control keywords indicating timing, retry, threshold, or limit logic
_AUTOMATION_CONTROL_KEYWORDS = {
    "retries", "retry", "timeout", "timeouts", "delay", "delays",
    "interval", "poll_interval", "pollinterval", "attempts", "attempt",
    "max_attempts", "maxattempts", "max_retries", "maxretries",
    "wait_time", "waittime", "duration", "backoff", "response_time",
    "responsetime", "threshold", "thresholds", "limit", "limits",
    "max_count", "maxcount", "max_wait", "maxwait", "poll_time",
    "load_time", "loadtime", "latency",
}

# Pattern 1: Automation control assignments (e.g. retries = 7, const timeout = 37)
_CONFIG_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:const\s+|let\s+|var\s+)?([a-z_][a-z0-9_]*)\s*(?::\s*number)?\s*(?:=|:)\s*(\d+(?:\.\d+)?)\b"
)

# Pattern 2: Conditional comparisons in automation logic (e.g. if retries > 7, if response_time > 3000)
_COMPARISON_PATTERN = re.compile(
    r"\b([a-z_][a-z0-9_]*)\s*(?:>|<|>=|<=|==|!=|===|!==)\s*(\d+(?:\.\d+)?)\b"
)
_INVERTED_COMPARISON_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:>|<|>=|<=|==|!=|===|!==)\s*([a-z_][a-z0-9_]*)\b"
)
_ASSERTION_COMPARISON_PATTERN = re.compile(
    r"\bexpect\s*\(\s*([a-z_][a-z0-9_]*)\s*\)\.(?:toBeGreaterThan|toBeLessThan|toBeGreaterThanOrEqual|toBeLessThanOrEqual)\s*\(\s*(\d+(?:\.\d+)?)\s*\)"
)

# Pattern 3: Positional locator values (e.g. :nth-child(7), .nth(5), .eq(5))
_POSITIONAL_LOCATOR_PATTERN = re.compile(
    r"""(?::nth-child|:nth-of-type)\s*\(\s*(\d+)\s*\)|\.(?:nth|eq)\s*\(\s*(\d+)\s*\)"""
)


def _is_excluded_number(num_str: str) -> bool:
    """Checks if a numeric value is among explicit exclusions (0, 1, HTTP status codes)."""
    try:
        val_float = float(num_str)
        # Exclude 0 and 1
        if val_float in (0.0, 1.0):
            return True
        # Exclude standard HTTP status codes when whole numbers
        if val_float.is_integer() and int(val_float) in _HTTP_STATUS_CODES:
            return True
    except ValueError:
        return True
    return False


def _is_comment_line(stripped_line: str, language: Language) -> bool:
    """Checks if a stripped line is purely a comment."""
    if language == Language.PYTHON:
        return (
            stripped_line.startswith("#")
            or (stripped_line.startswith('"""') and stripped_line.endswith('"""') and len(stripped_line) >= 6)
            or (stripped_line.startswith("'''") and stripped_line.endswith("'''") and len(stripped_line) >= 6)
        )
    return (
        stripped_line.startswith("//")
        or stripped_line.startswith("/*")
        or stripped_line.startswith("*")
    )


def _strip_inline_comment(line: str, language: Language) -> str:
    """Strips trailing inline comments from a line."""
    if language == Language.PYTHON:
        idx = line.find("#")
        if idx != -1:
            return line[:idx]
        return line

    # JavaScript / TypeScript
    # Avoid splitting on http:// or https://
    idx = line.find("//")
    while idx != -1:
        if idx > 0 and line[idx - 1] == ":":
            # Part of url protocol, search further
            idx = line.find("//", idx + 2)
        else:
            return line[:idx]
    return line


def detect_ap02(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP02 (Magic Numbers / Hardcoded Values) in the provided script content.

    Rules:
    - Flags potential magic numbers directly embedded in automation logic (timeouts,
      retries, thresholds, limits, positional locators).

    Excludes:
    - 0 and 1
    - HTTP status codes (200, 404, etc.)
    - Obvious loop / index usage (range(5), for (let i = 0; i < 5; i++), items[2])
    - Named constants (e.g. MAX_RETRIES = 7, DEFAULT_TIMEOUT = 30)
    - AP01 hardcoded waits (time.sleep, wait_for_timeout, cy.wait)
    - Ordinary test data (e.g. age = 25)
    - Comments and docstrings

    Returns:
        List of Finding objects with severity MEDIUM and confidence MEDIUM.
    """
    if not script_content or not script_content.strip():
        return []

    # Validate framework and language combination
    validation = validate_framework_and_language(framework, language)
    if not validation.is_valid:
        return []

    # Safe language normalization for comment parsing
    parsed_language = Language.PYTHON if "python" in str(language).lower() else (
        Language.TYPESCRIPT if "typescript" in str(language).lower() else Language.JAVASCRIPT
    )

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

        # Strip inline comments for scanning
        code_line = _strip_inline_comment(raw_line, parsed_language).strip()
        if not code_line:
            continue

        # Exclude AP01 hardcoded wait patterns so AP01 remains the sole finding
        if _AP01_WAIT_PATTERN.search(code_line):
            continue

        # Exclude named constant declarations (e.g. MAX_RETRIES = 7, const DEFAULT_TIMEOUT = 30)
        match_const = _NAMED_CONSTANT_PATTERN.match(code_line)
        if match_const:
            const_name = match_const.group(1)
            if const_name.isupper():
                continue

        # Exclude standard loop constructs
        if parsed_language == Language.PYTHON and _PY_RANGE_LOOP_PATTERN.search(code_line):
            continue
        if parsed_language in (Language.JAVASCRIPT, Language.TYPESCRIPT) and _JS_FOR_LOOP_PATTERN.search(code_line):
            continue

        # 1. Check for positional locators (e.g. :nth-child(7), .nth(5), .eq(5))
        pos_match = _POSITIONAL_LOCATOR_PATTERN.search(code_line)
        if pos_match:
            val = pos_match.group(1) or pos_match.group(2)
            if val and not _is_excluded_number(val):
                findings.append(
                    Finding(
                        id=f"AP02-L{line_num}",
                        anti_pattern_id="AP02",
                        anti_pattern_name="Magic Numbers / Hardcoded Values",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                        reason=f"Numeric value {val} is embedded directly in automation logic without meaningful context and may be better represented by a named constant.",
                    )
                )
                continue

        # 2. Check for automation control assignments (e.g. retries = 7, const timeout = 37)
        assign_match = _CONFIG_ASSIGNMENT_PATTERN.search(code_line)
        if assign_match:
            var_name, val = assign_match.group(1), assign_match.group(2)
            if var_name.lower() in _AUTOMATION_CONTROL_KEYWORDS and not _is_excluded_number(val):
                findings.append(
                    Finding(
                        id=f"AP02-L{line_num}",
                        anti_pattern_id="AP02",
                        anti_pattern_name="Magic Numbers / Hardcoded Values",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                        reason=f"Numeric value {val} is embedded directly in automation logic without meaningful context and may be better represented by a named constant.",
                    )
                )
                continue

        # 3. Check for conditional threshold comparisons (e.g. if retries > 7, if response_time > 3000)
        cmp_match = _COMPARISON_PATTERN.search(code_line)
        if cmp_match:
            var_name, val = cmp_match.group(1), cmp_match.group(2)
            if var_name.lower() in _AUTOMATION_CONTROL_KEYWORDS and not _is_excluded_number(val):
                findings.append(
                    Finding(
                        id=f"AP02-L{line_num}",
                        anti_pattern_id="AP02",
                        anti_pattern_name="Magic Numbers / Hardcoded Values",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                        reason=f"Numeric value {val} is embedded directly in automation logic without meaningful context and may be better represented by a named constant.",
                    )
                )
                continue

        inv_cmp_match = _INVERTED_COMPARISON_PATTERN.search(code_line)
        if inv_cmp_match:
            val, var_name = inv_cmp_match.group(1), inv_cmp_match.group(2)
            if var_name.lower() in _AUTOMATION_CONTROL_KEYWORDS and not _is_excluded_number(val):
                findings.append(
                    Finding(
                        id=f"AP02-L{line_num}",
                        anti_pattern_id="AP02",
                        anti_pattern_name="Magic Numbers / Hardcoded Values",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                        reason=f"Numeric value {val} is embedded directly in automation logic without meaningful context and may be better represented by a named constant.",
                    )
                )
                continue

        assert_cmp_match = _ASSERTION_COMPARISON_PATTERN.search(code_line)
        if assert_cmp_match:
            var_name, val = assert_cmp_match.group(1), assert_cmp_match.group(2)
            if var_name.lower() in _AUTOMATION_CONTROL_KEYWORDS and not _is_excluded_number(val):
                findings.append(
                    Finding(
                        id=f"AP02-L{line_num}",
                        anti_pattern_id="AP02",
                        anti_pattern_name="Magic Numbers / Hardcoded Values",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                        reason=f"Numeric value {val} is embedded directly in automation logic without meaningful context and may be better represented by a named constant.",
                    )
                )
                continue

    return findings
