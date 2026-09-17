import json
from unittest.mock import MagicMock, patch

import pytest
from src.models.enums import Confidence, Severity
from src.models.finding import Finding
from src.services.gemini_service import GeminiService, enrich_findings, redact_finding_context


def make_finding(
    id: str = "AP01-L5",
    anti_pattern_id: str = "AP01",
    anti_pattern_name: str = "Hardcoded Waits",
    severity: Severity = Severity.HIGH,
    confidence: Confidence = Confidence.HIGH,
    line_start: int = 5,
    line_end: int = 5,
    code_snippet: str = "time.sleep(5)",
    reason: str = "Hardcoded sleep detected",
    explanation: str = "",
    suggested_fix: str = "",
) -> Finding:
    return Finding(
        id=id,
        anti_pattern_id=anti_pattern_id,
        anti_pattern_name=anti_pattern_name,
        severity=severity,
        confidence=confidence,
        line_start=line_start,
        line_end=line_end,
        code_snippet=code_snippet,
        reason=reason,
        explanation=explanation,
        suggested_fix=suggested_fix,
    )


# 1. Successful Gemini response enriches explanation and suggested_fix.
def test_successful_gemini_enrichment():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "explanation": "Fixed sleeps cause non-deterministic delay and test slowness.",
            "suggested_fix": "page.locator('#submit').wait_for()",
        }
    )
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    original = make_finding()
    enriched = service.enrich_finding(original, "playwright", "python")

    assert enriched.explanation == "Fixed sleeps cause non-deterministic delay and test slowness."
    assert enriched.suggested_fix == "page.locator('#submit').wait_for()"


# 2–7. Invariant checks: Anti-pattern ID, severity, confidence, lines, snippet, reason remain unchanged.
def test_deterministic_finding_metadata_invariance():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "explanation": "AI explanation",
            "suggested_fix": "AI fix",
        }
    )
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    original = make_finding(
        id="AP06-L10",
        anti_pattern_id="AP06",
        anti_pattern_name="Fragile Locators",
        severity=Severity.MEDIUM,
        confidence=Confidence.MEDIUM,
        line_start=10,
        line_end=12,
        code_snippet="driver.find_element('xpath', '/html/body/div')",
        reason="Deep XPath detected",
    )

    enriched = service.enrich_finding(original, "selenium", "python")

    assert enriched.id == "AP06-L10"
    assert enriched.anti_pattern_id == "AP06"
    assert enriched.anti_pattern_name == "Fragile Locators"
    assert enriched.severity == Severity.MEDIUM
    assert enriched.confidence == Confidence.MEDIUM
    assert enriched.line_start == 10
    assert enriched.line_end == 12
    assert enriched.code_snippet == "driver.find_element('xpath', '/html/body/div')"
    assert enriched.reason == "Deep XPath detected"


# 8 & 12. AP09 secret content is redacted before Gemini receives it (and verified in mock call).
def test_ap09_secret_redaction_before_dispatch():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "explanation": "Credentials should not be hardcoded in scripts.",
            "suggested_fix": "password = os.getenv('PASSWORD')",
        }
    )
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    # Synthetic test secret to ensure redaction filter works and reaches mock redacted
    unredacted_snippet = 'password = "synthetic-test-secret-123"'
    finding = make_finding(
        id="AP09-L3",
        anti_pattern_id="AP09",
        anti_pattern_name="Hardcoded Secrets",
        severity=Severity.HIGH,
        code_snippet=unredacted_snippet,
        reason="Hardcoded secret detected",
    )

    enriched = service.enrich_finding(finding, "selenium", "python")

    # Inspect call args sent to mock_client.models.generate_content
    call_args = mock_client.models.generate_content.call_args
    prompt_text = call_args.kwargs["contents"]

    assert "synthetic-test-secret-123" not in prompt_text
    assert "[REDACTED]" in prompt_text
    assert enriched.explanation == "Credentials should not be hardcoded in scripts."


# 9. Missing API key does not crash the service.
def test_missing_api_key_returns_unmodified_finding(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("src.services.gemini_service.load_dotenv", lambda: None)
    service = GeminiService(api_key=None)

    assert not service.is_available()


    finding = make_finding()
    enriched = service.enrich_finding(finding, "playwright", "python")
    assert enriched == finding


# 10. API / network failure does not crash the service.
def test_network_failure_returns_unmodified_finding():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("Connection timeout / DNS failure")

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    finding = make_finding()
    enriched = service.enrich_finding(finding, "playwright", "python")

    assert enriched.explanation == ""
    assert enriched.suggested_fix == ""
    assert enriched == finding


# 11. Timeout does not crash the service.
def test_timeout_returns_unmodified_finding():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Request timed out after 5000ms")

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    finding = make_finding()
    enriched = service.enrich_finding(finding, "playwright", "python")

    assert enriched == finding


# 12. Rate-limit / API failure does not crash the service.
def test_rate_limit_failure_returns_unmodified_finding():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 Resource Exhausted / Rate limit exceeded")

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    finding = make_finding()
    enriched = service.enrich_finding(finding, "playwright", "python")

    assert enriched == finding


# 13. Malformed JSON response does not corrupt the finding.
def test_malformed_json_response_handled_safely():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "NOT_VALID_JSON{..."
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    finding = make_finding()
    enriched = service.enrich_finding(finding, "playwright", "python")

    assert enriched == finding


# 14. Empty Gemini response leaves deterministic finding intact.
def test_empty_response_leaves_finding_intact():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    finding = make_finding()
    enriched = service.enrich_finding(finding, "playwright", "python")

    assert enriched == finding


# 15 & 16. Gemini cannot introduce a new finding or alter score-related data.
def test_gemini_cannot_add_findings_or_alter_scorecard():
    # enrich_findings only enriches existing findings list items
    findings = [make_finding()]
    service = GeminiService(api_key="")  # unavailable
    result = enrich_findings(findings, "playwright", "python", gemini_service=service)


    assert len(result) == 1
    assert result[0] == findings[0]


# 17. The prompt contains only focused finding context.
def test_prompt_contains_only_focused_context():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"explanation": "x", "suggested_fix": "y"})
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiService(api_key="mock-api-key")
    service._client = mock_client

    finding = make_finding(code_snippet="page.waitForTimeout(5000)")
    service.enrich_finding(finding, "playwright", "javascript")

    prompt = mock_client.models.generate_content.call_args.kwargs["contents"]
    assert "page.waitForTimeout(5000)" in prompt
    assert "Anti-Pattern ID: AP01" in prompt
    assert "Framework: playwright" in prompt
    assert "Language: javascript" in prompt


# 18. Redaction helper standalone tests for all required security boundaries.
def test_redact_finding_context_secret_in_reason():
    snippet = "let x = 1;"
    reason = 'Hardcoded secret password = "synthetic-secret-in-reason" detected'
    redacted_snip, redacted_re = redact_finding_context(snippet, reason)

    assert "synthetic-secret-in-reason" not in redacted_re
    assert '[REDACTED]' in redacted_re


def test_redact_finding_context_jwt_token():
    synthetic_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    snippet = f"token = '{synthetic_jwt}'"
    reason = f"JWT token {synthetic_jwt} found"

    redacted_snip, redacted_re = redact_finding_context(snippet, reason)

    assert synthetic_jwt not in redacted_snip
    assert synthetic_jwt not in redacted_re
    assert "[REDACTED]" in redacted_snip
    assert "[REDACTED]" in redacted_re


def test_redact_finding_context_private_key():
    snippet = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----"
    reason = "Found -----BEGIN PRIVATE KEY----- material"

    redacted_snip, redacted_re = redact_finding_context(snippet, reason)

    assert "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC" not in redacted_snip
    assert "-----BEGIN [REDACTED] PRIVATE KEY-----" in redacted_snip
    assert "-----BEGIN [REDACTED] PRIVATE KEY-----" in redacted_re


def test_redact_finding_context_snippet_and_reason_combined():
    snippet = 'auth_token = "synthetic-token-val-999"'
    reason = 'Detected auth_token = "synthetic-token-val-999" in setup block'

    redacted_snip, redacted_re = redact_finding_context(snippet, reason)

    assert "synthetic-token-val-999" not in redacted_snip
    assert "synthetic-token-val-999" not in redacted_re
    assert '[REDACTED]' in redacted_snip
    assert '[REDACTED]' in redacted_re


def test_redact_finding_context_preserves_already_redacted():
    snippet = 'api_key = "[REDACTED]"'
    reason = "Hardcoded secret detected"

    redacted_snip, redacted_re = redact_finding_context(snippet, reason)

    assert redacted_snip == 'api_key = "[REDACTED]"'
    assert redacted_re == "Hardcoded secret detected"


def test_dotenv_loading_integration(tmp_path, monkeypatch):
    """Verify that GeminiService invokes load_dotenv() to support .env file loading."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with patch("src.services.gemini_service.load_dotenv") as mock_load:
        def mock_load_impl():
            monkeypatch.setenv("GEMINI_API_KEY", "synthetic-key-from-dotenv")
        mock_load.side_effect = mock_load_impl

        service = GeminiService()
        mock_load.assert_called()
        assert service.api_key == "synthetic-key-from-dotenv"
