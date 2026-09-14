"""
AP05 — Missing Abstractions Detector.

Detects reusable logical browser automation workflows (e.g. login sequences,
form submissions, multi-step navigation and input) that are repeated across multiple
locations in the same script without being extracted into a reusable helper function
or page-object method.

Distinction from AP03:
- AP03 detects arbitrary code duplication (>= 3 consecutive identical statements).
- AP05 specifically checks whether the repeated code represents a cohesive browser
  automation workflow (combining multiple browser interactions like fill, type,
  click, goto, send_keys) that warrants extraction into a reusable abstraction.
"""

import re
from dataclasses import dataclass
from collections import defaultdict
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

MIN_WORKFLOW_STATEMENTS = 3

# Regex recognizing browser interaction actions across Selenium, Playwright, and Cypress
_BROWSER_INTERACTION_PATTERN = re.compile(
    r"\b(?:click|fill|type|send_keys|goto|visit|get|press|select_option|check|uncheck|submit)\b",
    re.IGNORECASE,
)

# Workflow semantic keywords indicating logical UI user flows (login, auth, form, checkout, etc.)
_WORKFLOW_KEYWORDS_PATTERN = re.compile(
    r"\b(?:username|password|login|signin|submit|email|search|checkout|register|signup|cart|auth)\b",
    re.IGNORECASE,
)


@dataclass
class _Statement:
    line_num: int
    raw_line: str
    norm_text: str


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


def _is_import_line(stripped_line: str, language: Language) -> bool:
    """Checks if a stripped line is an import statement."""
    if language == Language.PYTHON:
        return stripped_line.startswith("import ") or stripped_line.startswith("from ")
    return (
        stripped_line.startswith("import ")
        or stripped_line.startswith("from ")
        or bool(re.search(r"\brequire\s*\(", stripped_line))
    )


def _normalize_line_text(line: str) -> str:
    """Normalizes whitespace within a code line."""
    return re.sub(r"\s+", " ", line.strip())


def _is_browser_workflow(statements: list[_Statement]) -> bool:
    """
    Evaluates whether a sequence of statements represents a cohesive browser automation workflow.

    Criteria:
    1. Contains multiple browser interaction operations (click, fill, type, goto, send_keys, etc.).
    2. Contains either at least 2 distinct interaction verbs or domain workflow keywords
       (e.g., username/password/login/submit), demonstrating a meaningful logical unit.
    """
    interaction_verbs = set()
    has_workflow_keyword = False

    for stmt in statements:
        matches = _BROWSER_INTERACTION_PATTERN.findall(stmt.norm_text)
        for m in matches:
            interaction_verbs.add(m.lower())

        if _WORKFLOW_KEYWORDS_PATTERN.search(stmt.norm_text):
            has_workflow_keyword = True

    # Requires multiple interaction steps
    total_actions = sum(len(_BROWSER_INTERACTION_PATTERN.findall(s.norm_text)) for s in statements)
    if total_actions < 2:
        return False

    # Meaningful workflow if it combines multiple distinct actions (e.g. fill + click, goto + click)
    # or targets workflow-specific form interactions (e.g. login credentials + submit)
    return len(interaction_verbs) >= 2 or has_workflow_keyword


def detect_ap05(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP05 (Missing Abstractions) in the provided script content.

    Flags multi-step browser workflows that are repeated in multiple locations instead
    of being encapsulated in reusable helper functions or page-object methods.

    Returns:
        List of Finding objects with severity MEDIUM and confidence MEDIUM.
    """
    if not script_content or not script_content.strip():
        return []

    validation = validate_framework_and_language(framework, language)
    if not validation.is_valid:
        return []

    parsed_language = Language.PYTHON if "python" in str(language).lower() else (
        Language.TYPESCRIPT if "typescript" in str(language).lower() else Language.JAVASCRIPT
    )

    raw_lines = script_content.splitlines()
    meaningful_stmts: list[_Statement] = []
    in_block_comment = False
    in_py_docstring = False
    py_docstring_delim = ""

    for line_idx, raw_line in enumerate(raw_lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        # Track Python docstrings
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

        # Track JS/TS block comments
        if parsed_language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith("/*"):
                if "*/" not in stripped:
                    in_block_comment = True
                continue

        # Skip comment lines
        if _is_comment_line(stripped, parsed_language):
            continue

        # Skip imports
        if _is_import_line(stripped, parsed_language):
            continue

        # Skip structural closing bracket lines in JS/TS
        if parsed_language in (Language.JAVASCRIPT, Language.TYPESCRIPT) and re.match(r"^[\s}\]);]+$", stripped):
            continue

        norm_text = _normalize_line_text(raw_line)
        meaningful_stmts.append(
            _Statement(
                line_num=line_idx,
                raw_line=raw_line,
                norm_text=norm_text,
            )
        )

    num_stmts = len(meaningful_stmts)
    if num_stmts < MIN_WORKFLOW_STATEMENTS:
        return []

    claimed = [False] * num_stmts
    workflow_groups: list[tuple[list[int], int]] = []

    # Search from longest candidate block down to MIN_WORKFLOW_STATEMENTS
    for length in range(num_stmts // 2, MIN_WORKFLOW_STATEMENTS - 1, -1):
        seq_positions: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for i in range(num_stmts - length + 1):
            if any(claimed[i + k] for k in range(length)):
                continue
            seq = tuple(meaningful_stmts[i + k].norm_text for k in range(length))
            seq_positions[seq].append(i)

        for seq, starts in seq_positions.items():
            valid_starts = [i for i in starts if not any(claimed[i + k] for k in range(length))]
            if len(valid_starts) < 2:
                continue

            # Select non-overlapping occurrences
            selected: list[int] = []
            for start_idx in valid_starts:
                if not selected or start_idx >= selected[-1] + length:
                    selected.append(start_idx)

            if len(selected) >= 2:
                candidate_block = [meaningful_stmts[selected[0] + k] for k in range(length)]
                # AP05 filter: must qualify as a cohesive browser workflow
                if _is_browser_workflow(candidate_block):
                    for start_idx in selected:
                        for k in range(length):
                            claimed[start_idx + k] = True
                    workflow_groups.append((selected, length))

    findings: list[Finding] = []

    for occurrences, length in workflow_groups:
        loc_ranges = []
        for start_idx in occurrences:
            first_line = meaningful_stmts[start_idx].line_num
            last_line = meaningful_stmts[start_idx + length - 1].line_num
            loc_ranges.append((first_line, last_line))

        for occ_idx, (line_start, line_end) in enumerate(loc_ranges):
            other_locs = [
                f"lines {s}–{e}" if s != e else f"line {s}"
                for i, (s, e) in enumerate(loc_ranges)
                if i != occ_idx
            ]
            other_loc_str = ", ".join(other_locs)

            snippet_lines = raw_lines[line_start - 1 : line_end]
            code_snippet = "\n".join(snippet_lines)

            findings.append(
                Finding(
                    id=f"AP05-L{line_start}",
                    anti_pattern_id="AP05",
                    anti_pattern_name="Missing Abstractions",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    line_start=line_start,
                    line_end=line_end,
                    code_snippet=code_snippet,
                    reason=(
                        f"Repeated multi-step browser workflow ({length} actions) is implemented directly "
                        f"across multiple locations (also at {other_loc_str}) instead of being extracted "
                        f"into a reusable helper function or page-object method."
                    ),
                )
            )

    findings.sort(key=lambda f: (f.line_start, f.line_end))
    return findings
