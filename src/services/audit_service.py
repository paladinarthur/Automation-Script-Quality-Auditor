"""
Audit Orchestrator Service for Automation Script Quality Auditor.

Coordinates the deterministic audit pipeline:
1. Validates input framework and language combination.
2. Invokes active detectors (AP01 through AP10) with error isolation per detector.
3. Collects and deterministically sorts confirmed findings by line number and anti-pattern ID.

Deliberate Design Boundaries:
- Coordination only: Contains NO anti-pattern detection rules.
- Deterministic only: Does NOT calculate scores or invoke Gemini API.
- Static analysis only: Does NOT execute user scripts, open browsers, or perform network calls.
- Simple architecture: Uses straightforward procedural coordination without unnecessary class abstractions.
"""

import logging
from src.detectors import (
    detect_ap01,
    detect_ap02,
    detect_ap03,
    detect_ap04,
    detect_ap05,
    detect_ap06,
    detect_ap07,
    detect_ap08,
    detect_ap09,
    detect_ap10,
)
from src.models import Finding, ScriptInput
from src.validation.validator import validate_framework_and_language

logger = logging.getLogger(__name__)

# Canonical sequence of deterministic detectors (AP01 - AP10)
ALL_DETECTORS = [
    detect_ap01,
    detect_ap02,
    detect_ap03,
    detect_ap04,
    detect_ap05,
    detect_ap06,
    detect_ap07,
    detect_ap08,
    detect_ap09,
    detect_ap10,
]



def audit_script(script_input: ScriptInput) -> list[Finding]:
    """
    Coordinates the deterministic audit pipeline for a given script input.

    Args:
        script_input: ScriptInput payload containing script_content, framework, and language.

    Returns:
        List of Finding objects sorted deterministically by (line_start, line_end, anti_pattern_id).
        Returns an empty list if input is empty or framework/language combination is invalid.
    """
    if not script_input or not script_input.script_content or not script_input.script_content.strip():
        return []

    # 1. Validate framework & language combination
    validation = validate_framework_and_language(script_input.framework, script_input.language)
    if not validation.is_valid:
        logger.warning(
            "Audit skipped due to invalid framework/language combination: %s",
            validation.error_message,
        )
        return []

    all_findings: list[Finding] = []

    # 2. Execute detectors with simple per-detector error isolation
    for detector in ALL_DETECTORS:
        try:
            detector_findings = detector(
                script_input.script_content,
                script_input.framework,
                script_input.language,
            )
            if detector_findings:
                all_findings.extend(detector_findings)
        except Exception as exc:
            logger.error(
                "Detector '%s' failed unexpectedly on script content: %s",
                getattr(detector, "__name__", str(detector)),
                exc,
                exc_info=True,
            )

    # 3. Sort findings deterministically by line_start, line_end, then anti_pattern_id
    all_findings.sort(key=lambda f: (f.line_start, f.line_end, f.anti_pattern_id))

    return all_findings


# Friendly alias for orchestrator pipeline entrypoint
run_audit = audit_script
