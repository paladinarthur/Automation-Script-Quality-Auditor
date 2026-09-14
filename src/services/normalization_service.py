"""
Finding Normalization and Deduplication Service for Automation Script Quality Auditor.

Responsibilities:
- Accepts raw `Finding` list collected from detectors AP01-AP10.
- Removes exact duplicate findings (same anti_pattern_id, line_start, line_end, code_snippet).
- Resolves AP01 precedence over AP02 and AP10:
  - If a line contains a fixed hardcoded delay (AP01 finding), any AP02 (Magic Numbers)
    or AP10 (Flaky Patterns) findings that arise solely from the same fixed timing delay/operation
    are deduplicated in favor of AP01.
- Preserves distinct coexisting findings (e.g. AP03 Duplicated Code and AP05 Missing Abstractions,
  or multiple distinct anti-patterns on the same line).
- Preserves all Finding metadata without modification (severity, confidence, line ranges, snippets, reason).
- Returns findings deterministically sorted by (line_start, line_end, anti_pattern_id).

Deliberate Design Boundaries:
- Static analysis data processing only.
- Does NOT execute anti-pattern detection rules or alter script code.
- Does NOT calculate scores or apply severity penalties.
- Does NOT call Gemini or generate explanations / suggested fixes.
"""

import logging
import re
from src.models.finding import Finding

logger = logging.getLogger(__name__)

# Patterns identifying fixed hardcoded delays across supported frameworks/languages
_FIXED_DELAY_PATTERNS = (
    r"\btime\.sleep\b",
    r"\bwait_for_timeout\b",
    r"\bwaitForTimeout\b",
    r"\bcy\.wait\b",
)


def _is_fixed_delay_code(snippet: str) -> bool:
    """Checks if a code snippet contains a fixed numeric delay call."""
    if not snippet:
        return False
    return any(re.search(pat, snippet) for pat in _FIXED_DELAY_PATTERNS)


def normalize_findings(findings: list[Finding]) -> list[Finding]:
    """
    Normalizes and deduplicates raw detector findings according to approved rules.

    Args:
        findings: List of raw Finding objects collected from detectors.

    Returns:
        List of deduplicated Finding objects sorted by (line_start, line_end, anti_pattern_id).
    """
    if not findings:
        return []

    # 1. Deduplicate exact duplicate findings (same anti_pattern_id, line_start, line_end, code_snippet/reason)
    unique_raw: list[Finding] = []
    seen_keys: set[tuple[str, int, int, str]] = set()

    for f in findings:
        key = (f.anti_pattern_id, f.line_start, f.line_end, f.code_snippet.strip())
        if key not in seen_keys:
            seen_keys.add(key)
            unique_raw.append(f)

    # 2. Identify AP01 fixed-delay locations to resolve precedence over AP02/AP10
    ap01_delay_lines: set[int] = set()
    for f in unique_raw:
        if f.anti_pattern_id == "AP01":
            # Check lines covered by AP01 finding
            for line_num in range(f.line_start, f.line_end + 1):
                ap01_delay_lines.add(line_num)

    # 3. Filter out AP02 / AP10 findings that overlap with AP01 fixed delays
    filtered_findings: list[Finding] = []
    for f in unique_raw:
        if f.anti_pattern_id in ("AP02", "AP10"):
            # Check if this finding falls on a line with an AP01 fixed delay AND represents that delay
            overlaps_ap01_line = any(l in ap01_delay_lines for l in range(f.line_start, f.line_end + 1))
            if overlaps_ap01_line and _is_fixed_delay_code(f.code_snippet):
                logger.debug(
                    "Deduplicated %s at line %d in favor of AP01 hardcoded wait precedence.",
                    f.anti_pattern_id,
                    f.line_start,
                )
                continue

        filtered_findings.append(f)

    # 4. Sort findings deterministically by line_start, line_end, anti_pattern_id
    filtered_findings.sort(key=lambda f: (f.line_start, f.line_end, f.anti_pattern_id))

    return filtered_findings
