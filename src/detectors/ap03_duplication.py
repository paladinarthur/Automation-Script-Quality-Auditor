"""
AP03 — Copy-Paste / Duplicated Code Detector (Exact Duplicates).

Detects repeated automation blocks containing at least 3 consecutive meaningful
statements within the same script.

Normalization:
- Ignores blank lines
- Ignores full-line comments
- Trims leading/trailing whitespace and normalizes internal whitespace
- Ignores import statements
- Preserves original source line numbers and original code snippets

Exclusions:
- Single repeated statements (< 3 statements)
- Two repeated statements (< 3 statements)
- Imports (import ..., from ... import ..., require(...))
- Blank lines and comments
- Unique blocks that appear only once
"""

import re
from dataclasses import dataclass
from collections import defaultdict
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

MIN_DUPLICATE_STATEMENTS = 3


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
    # JavaScript / TypeScript
    return (
        stripped_line.startswith("import ")
        or stripped_line.startswith("from ")
        or bool(re.search(r"\brequire\s*\(", stripped_line))
    )


def _normalize_line_text(line: str) -> str:
    """Normalizes whitespace within a code line."""
    return re.sub(r"\s+", " ", line.strip())


def detect_ap03(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP03 (Copy-Paste / Duplicated Code) in the provided script content.

    Identifies repeated sequences of at least 3 consecutive meaningful statements.
    Reports separate Finding objects for each occurrence of a duplicated block.

    Returns:
        List of Finding objects with severity MEDIUM and confidence HIGH.
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

        norm_text = _normalize_line_text(raw_line)
        meaningful_stmts.append(
            _Statement(
                line_num=line_idx,
                raw_line=raw_line,
                norm_text=norm_text,
            )
        )

    num_stmts = len(meaningful_stmts)
    if num_stmts < MIN_DUPLICATE_STATEMENTS:
        return []

    # Greedy maximal block matching: search from longest possible window down to 3
    claimed = [False] * num_stmts
    duplicate_groups: list[tuple[list[int], int]] = []  # (list of start indices, window length)

    for length in range(num_stmts // 2, MIN_DUPLICATE_STATEMENTS - 1, -1):
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
                for start_idx in selected:
                    for k in range(length):
                        claimed[start_idx + k] = True
                duplicate_groups.append((selected, length))

    findings: list[Finding] = []

    for occurrences, length in duplicate_groups:
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
                    id=f"AP03-L{line_start}",
                    anti_pattern_id="AP03",
                    anti_pattern_name="Copy-Paste / Duplicated Code",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.HIGH,
                    line_start=line_start,
                    line_end=line_end,
                    code_snippet=code_snippet,
                    reason=(
                        f"Duplicated automation block ({length} statements); identical block also occurs at {other_loc_str}."
                    ),
                )
            )

    findings.sort(key=lambda f: (f.line_start, f.line_end))
    return findings
