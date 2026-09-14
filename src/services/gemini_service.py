"""
Gemini Advisory Service for Automation Script Quality Auditor.

Responsibilities:
- Enriches confirmed `Finding` objects with contextual AI-generated `explanation` and `suggested_fix`.
- Operates strictly downstream of deterministic static analysis and scoring.
- Enforces strict secret redaction prior to sending finding context to Gemini.
- Uses official `google-genai` SDK with structured JSON schema response contract.
- Provides resilient error handling: missing API key, timeouts, rate limits, malformed responses,
  or network failures return the original Finding safely intact without crashing the audit.

Strict AI Boundary:
- Gemini is ADVISORY ONLY.
- Gemini MUST NOT detect anti-patterns, calculate scores, alter severities, or modify line numbers.
- Gemini output ONLY updates `finding.explanation` and `finding.suggested_fix`.
"""

import json
import logging
import os
import re
from dataclasses import replace
from typing import Any

from src.models.finding import Finding

logger = logging.getLogger(__name__)

# Fallback text when Gemini is unavailable or fails
_DEFAULT_FALLBACK_EXPLANATION = ""
_DEFAULT_FALLBACK_FIX = ""

# Regex patterns for pre-transmission secret sanitization
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(?:password|passwd|pwd|api_?key|secret|secret_?key|token|auth_?token|bearer_?token)\s*[:=]\s*['\"]([^'\"]+)['\"]"
)
_JWT_TOKEN_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
)
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN\s+(?:[A-Z0-9_-]+\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:[A-Z0-9_-]+\s+)?PRIVATE\s+KEY-----|-----BEGIN\s+(?:[A-Z0-9_-]+\s+)?PRIVATE\s+KEY-----"
)
_PLACEHOLDER_VALUES = {"[REDACTED]", "REDACTED", "<PASSWORD>", "YOUR_API_KEY", "dummy-token", "fake-token"}


def _sanitize_text(text: str) -> str:
    """Sanitizes a single text string by redacting assignment secrets, JWTs, and private keys."""
    if not text:
        return ""

    result = text

    # 1. Sanitize string literal secret assignments: e.g. password = "secret" -> password = "[REDACTED]"
    def _replace_assignment(match: re.Match) -> str:
        full_match = match.group(0)
        secret_val = match.group(1)
        if secret_val in _PLACEHOLDER_VALUES:
            return full_match
        return full_match.replace(f"'{secret_val}'", "'[REDACTED]'").replace(
            f'"{secret_val}"', '"[REDACTED]"'
        )

    result = _SECRET_ASSIGNMENT_PATTERN.sub(_replace_assignment, result)

    # 2. Sanitize JWT tokens: e.g. eyJ... -> [REDACTED]
    result = _JWT_TOKEN_PATTERN.sub("[REDACTED]", result)

    # 3. Sanitize Private Key material: e.g. -----BEGIN PRIVATE KEY----- ... -> -----BEGIN [REDACTED] PRIVATE KEY-----
    result = _PRIVATE_KEY_PATTERN.sub("-----BEGIN [REDACTED] PRIVATE KEY-----", result)

    return result


def redact_finding_context(code_snippet: str, reason: str) -> tuple[str, str]:
    """
    Redacts any sensitive credential values from snippet and reason before sending to Gemini.

    Returns:
        Tuple of (redacted_snippet, redacted_reason)
    """
    redacted_snippet = _sanitize_text(code_snippet or "")
    redacted_reason = _sanitize_text(reason or "")

    return redacted_snippet, redacted_reason


def _build_prompt(
    finding: Finding,
    framework: str,
    language: str,
    redacted_snippet: str,
    redacted_reason: str,
) -> str:
    """Builds a constrained, focused prompt for Gemini advisory enrichment."""
    return f"""You are an expert QA automation code auditor reviewing an already-confirmed anti-pattern.

CRITICAL DIRECTIVES:
1. The anti-pattern below has already been deterministically confirmed. Do NOT question, debate, reclassify, or dismiss it.
2. Do NOT invent new findings, alter severity, or calculate scores.
3. Do NOT rewrite the entire script.
4. Return ONLY a structured response containing an explanation and a suggested fix.

CONTEXT:
- Framework: {framework}
- Language: {language}
- Anti-Pattern ID: {finding.anti_pattern_id}
- Anti-Pattern Name: {finding.anti_pattern_name}
- Severity: {finding.severity.value if hasattr(finding.severity, 'value') else finding.severity}
- Line Reference: {finding.line_display}
- Detection Reason: {redacted_reason}
- Code Snippet:
```
{redacted_snippet}
```

TASK:
1. "explanation": Provide a concise explanation (1-3 sentences) of why this specific pattern is harmful in automation scripts.
2. "suggested_fix": Provide a single, clean, actionable replacement code snippet or concise remediation advice for {framework} in {language}.
"""


class GeminiService:
    """Service wrapper for advisory Gemini API enrichment."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initializes GeminiService with API key from parameter or GEMINI_API_KEY env var."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client: Any = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning("Failed to initialize google-genai Client: %s", exc)
                self._client = None

    def is_available(self) -> bool:
        """Returns True if Gemini API key is present and client initialized."""
        return bool(self.api_key and self._client is not None)

    def enrich_finding(
        self,
        finding: Finding,
        framework: str,
        language: str,
    ) -> Finding:
        """
        Enriches a confirmed Finding with AI-generated explanation and suggested_fix.

        Args:
            finding: Confirmed Finding object.
            framework: Automation framework name.
            language: Script language name.

        Returns:
            Enriched Finding object (or original finding safely intact if API unavailable or fails).
        """
        if not self.is_available():
            logger.debug("GeminiService unavailable; returning un-enriched finding.")
            return finding

        # 1. Secret Redaction Boundary
        redacted_snippet, redacted_reason = redact_finding_context(
            finding.code_snippet, finding.reason
        )

        # 2. Build focused prompt
        prompt = _build_prompt(
            finding, framework, language, redacted_snippet, redacted_reason
        )

        try:
            # 3. Request structured output from Gemini using official SDK
            from google.genai import types

            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "explanation": {"type": "STRING"},
                            "suggested_fix": {"type": "STRING"},
                        },
                        "required": ["explanation", "suggested_fix"],
                    },
                    temperature=0.2,
                ),
            )

            # 4. Parse & Validate Response
            if not response or not response.text:
                logger.warning("Empty response received from Gemini for finding %s", finding.id)
                return finding

            data = json.loads(response.text)
            explanation = data.get("explanation", "").strip()
            suggested_fix = data.get("suggested_fix", "").strip()

            if not explanation or not suggested_fix:
                logger.warning(
                    "Incomplete JSON response from Gemini for finding %s: %s",
                    finding.id,
                    data,
                )
                return finding

            # 5. Return immutable/safe copy preserving all original metadata
            return replace(
                finding,
                explanation=explanation,
                suggested_fix=suggested_fix,
            )

        except Exception as exc:
            logger.error(
                "Gemini API enrichment failed for finding '%s': %s",
                finding.id,
                exc,
            )
            return finding


def enrich_findings(
    findings: list[Finding],
    framework: str,
    language: str,
    gemini_service: GeminiService | None = None,
) -> list[Finding]:
    """
    Convenience function to enrich a list of confirmed findings using Gemini.

    Args:
        findings: List of confirmed Finding objects.
        framework: Automation framework name.
        language: Script language name.
        gemini_service: Optional GeminiService instance.

    Returns:
        List of enriched Finding objects.
    """
    if not findings:
        return []

    service = gemini_service or GeminiService()
    if not service.is_available():
        return list(findings)

    enriched_list: list[Finding] = []
    for f in findings:
        enriched_list.append(service.enrich_finding(f, framework, language))

    return enriched_list
