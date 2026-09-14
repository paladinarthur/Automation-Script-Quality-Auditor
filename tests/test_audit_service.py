import logging
from unittest.mock import patch, MagicMock

import pytest

from src.models.input import ScriptInput
from src.models.finding import Finding
from src.services.audit_service import audit_script, run_audit


# 1. Valid Selenium/Python script reaches the orchestrator.
def test_valid_selenium_python_script():
    script_input = ScriptInput(
        script_content="from selenium import webdriver\ndriver = webdriver.Chrome()",
        framework="selenium",
        language="python",
    )
    findings = audit_script(script_input)
    assert isinstance(findings, list)


# 2. Valid Playwright/Python script reaches the orchestrator.
def test_valid_playwright_python_script():
    script_input = ScriptInput(
        script_content="from playwright.sync_api import sync_playwright",
        framework="playwright",
        language="python",
    )
    findings = audit_script(script_input)
    assert isinstance(findings, list)


# 3. Valid Playwright JavaScript script reaches the orchestrator.
def test_valid_playwright_javascript_script():
    script_input = ScriptInput(
        script_content="const { test, expect } = require('@playwright/test');",
        framework="playwright",
        language="javascript",
    )
    findings = audit_script(script_input)
    assert isinstance(findings, list)


# 4. Valid Playwright TypeScript script reaches the orchestrator.
def test_valid_playwright_typescript_script():
    script_input = ScriptInput(
        script_content="import { test, expect } from '@playwright/test';",
        framework="playwright",
        language="typescript",
    )
    findings = audit_script(script_input)
    assert isinstance(findings, list)


# 5. Valid Cypress JavaScript script reaches the orchestrator.
def test_valid_cypress_javascript_script():
    script_input = ScriptInput(
        script_content="describe('Test', () => { it('works', () => { cy.visit('/'); }); });",
        framework="cypress",
        language="javascript",
    )
    findings = audit_script(script_input)
    assert isinstance(findings, list)


# 6. Valid Cypress TypeScript script reaches the orchestrator.
def test_valid_cypress_typescript_script():
    script_input = ScriptInput(
        script_content="describe('Test', () => { it('works', () => { cy.visit('/'); }); });",
        framework="cypress",
        language="typescript",
    )
    findings = audit_script(script_input)
    assert isinstance(findings, list)


# 7. Invalid framework/language is rejected safely.
def test_invalid_framework_language_rejected_safely():
    script_input = ScriptInput(
        script_content="print('hello')",
        framework="selenium",
        language="javascript",  # Invalid combo
    )
    findings = audit_script(script_input)
    assert findings == []


# 8. Empty script produces no findings.
def test_empty_script_produces_no_findings():
    script_input = ScriptInput(
        script_content="",
        framework="playwright",
        language="python",
    )
    findings = audit_script(script_input)
    assert findings == []

    whitespace_input = ScriptInput(
        script_content="   \n\t  ",
        framework="playwright",
        language="python",
    )
    assert audit_script(whitespace_input) == []


# 9. Clean script produces zero findings.
def test_clean_script_produces_zero_findings():
    script_content = (
        "from playwright.sync_api import Page, expect\n"
        "def test_clean(page: Page):\n"
        "    page.goto('https://example.com')\n"
        "    expect(page.locator('#submit')).to_be_visible()\n"
    )
    script_input = ScriptInput(
        script_content=script_content,
        framework="playwright",
        language="python",
    )
    findings = audit_script(script_input)
    assert len(findings) == 0


# 10. Script containing a known AP01 issue produces an AP01 finding.
def test_ap01_issue_flagged():
    script_content = (
        "import time\n"
        "from selenium import webdriver\n"
        "driver = webdriver.Chrome()\n"
        "time.sleep(5)\n"
    )
    script_input = ScriptInput(
        script_content=script_content,
        framework="selenium",
        language="python",
    )
    findings = audit_script(script_input)
    ap01_findings = [f for f in findings if f.anti_pattern_id == "AP01"]
    assert len(ap01_findings) > 0


# 11. Script containing multiple known anti-patterns produces findings from multiple detectors.
def test_multiple_anti_patterns_flagged():
    script_content = (
        "import time\n"
        "from selenium import webdriver\n"
        "driver = webdriver.Chrome()\n"
        "time.sleep(5)\n"
        "driver.find_element('xpath', '/html/body/div[1]/div[2]/button[3]').click()\n"
    )
    script_input = ScriptInput(
        script_content=script_content,
        framework="selenium",
        language="python",
    )
    findings = audit_script(script_input)
    ap_ids = {f.anti_pattern_id for f in findings}
    assert "AP01" in ap_ids
    assert "AP06" in ap_ids


# 12. Findings are sorted deterministically by (line_start, line_end, anti_pattern_id).
def test_findings_sorted_deterministically():
    f1 = Finding(id="1", anti_pattern_id="AP06", anti_pattern_name="Locators", line_start=10, line_end=12, severity="Medium", confidence="High", code_snippet="...", reason="x")
    f2 = Finding(id="2", anti_pattern_id="AP01", anti_pattern_name="Waits", line_start=5, line_end=5, severity="High", confidence="High", code_snippet="...", reason="y")
    f3 = Finding(id="3", anti_pattern_id="AP02", anti_pattern_name="Magic Numbers", line_start=10, line_end=10, severity="Low", confidence="Low", code_snippet="...", reason="z")
    f4 = Finding(id="4", anti_pattern_id="AP01", anti_pattern_name="Waits", line_start=10, line_end=12, severity="High", confidence="High", code_snippet="...", reason="w")

    mock_ap01 = MagicMock(return_value=[f2, f4])
    mock_ap02 = MagicMock(return_value=[f3])
    mock_ap06 = MagicMock(return_value=[f1])

    with patch("src.services.audit_service.ALL_DETECTORS", [mock_ap01, mock_ap02, mock_ap06]):
        script_input = ScriptInput(
            script_content="code",
            framework="selenium",
            language="python",
        )
        result = audit_script(script_input)
        
        # Expected sort order:
        # 1. f2: line_start=5, line_end=5, anti_pattern_id=AP01
        # 2. f3: line_start=10, line_end=10, anti_pattern_id=AP02
        # 3. f4: line_start=10, line_end=12, anti_pattern_id=AP01
        # 4. f1: line_start=10, line_end=12, anti_pattern_id=AP06
        assert result == [f2, f3, f4, f1]


# 13. Finding metadata is preserved.
def test_finding_metadata_preserved():
    f = Finding(
        id="f1",
        anti_pattern_id="AP01",
        anti_pattern_name="Unconditional Wait",
        line_start=3,
        line_end=3,
        severity="High",
        confidence="High",
        reason="Hardcoded sleep detected",
        code_snippet="time.sleep(5)",
        explanation="",
        suggested_fix="",
    )
    with patch("src.services.audit_service.ALL_DETECTORS", [MagicMock(return_value=[f])]):
        script_input = ScriptInput(
            script_content="import time\ntime.sleep(5)",
            framework="selenium",
            language="python",
        )
        result = audit_script(script_input)
        assert len(result) == 1
        res = result[0]
        assert res.id == "f1"
        assert res.anti_pattern_id == "AP01"
        assert res.anti_pattern_name == "Unconditional Wait"
        assert res.line_start == 3
        assert res.line_end == 3
        assert res.severity == "High"
        assert res.confidence == "High"
        assert res.reason == "Hardcoded sleep detected"
        assert res.code_snippet == "time.sleep(5)"
        assert res.explanation == ""
        assert res.suggested_fix == ""


# 14. The orchestrator does not calculate or modify scores.
def test_orchestrator_does_not_modify_scores():
    f = Finding(
        id="f1",
        anti_pattern_id="AP01",
        anti_pattern_name="Unconditional Wait",
        line_start=1,
        line_end=1,
        severity="High",
        confidence="High",
        code_snippet="time.sleep(1)",
        reason="sleep",
    )
    with patch("src.services.audit_service.ALL_DETECTORS", [MagicMock(return_value=[f])]):
        script_input = ScriptInput(
            script_content="time.sleep(1)",
            framework="selenium",
            language="python",
        )
        result = audit_script(script_input)
        assert len(result) == 1
        assert not hasattr(result[0], "score")


# 15. The orchestrator does not invoke Gemini.
def test_orchestrator_does_not_invoke_gemini():
    # Verify that explanations and suggested fixes remain empty as returned by detectors
    script_content = "import time\ntime.sleep(5)"
    script_input = ScriptInput(
        script_content=script_content,
        framework="selenium",
        language="python",
    )
    findings = audit_script(script_input)
    for f in findings:
        assert f.explanation == ""
        assert f.suggested_fix == ""


# 16. A detector failure is handled according to documented error-handling behavior.
def test_detector_failure_isolation(caplog):
    good_finding = Finding(
        id="f2",
        anti_pattern_id="AP02",
        anti_pattern_name="Magic Numbers",
        line_start=2,
        line_end=2,
        severity="Low",
        confidence="Low",
        code_snippet="x = 42",
        reason="magic number",
    )
    bad_detector = MagicMock(side_effect=Exception("Unexpected AST parsing crash"))
    good_detector = MagicMock(return_value=[good_finding])

    with patch("src.services.audit_service.ALL_DETECTORS", [bad_detector, good_detector]):
        script_input = ScriptInput(
            script_content="x = 42",
            framework="selenium",
            language="python",
        )
        with caplog.at_level(logging.ERROR):
            findings = audit_script(script_input)

        # Audit completed despite detector failure, returning findings from good detector
        assert findings == [good_finding]
        assert "Detector" in caplog.text
        assert "failed unexpectedly" in caplog.text


def test_run_audit_alias():
    script_input = ScriptInput(
        script_content="",
        framework="playwright",
        language="python",
    )
    assert run_audit(script_input) == []


def test_orchestrator_runs_normalization():
    # Verify that orchestrator passes raw findings through normalize_findings
    script_content = "import time\ntime.sleep(5)"
    script_input = ScriptInput(
        script_content=script_content,
        framework="selenium",
        language="python",
    )
    findings = audit_script(script_input)
    # Even if AP01, AP02, or AP10 all match time.sleep(5), normalization deduplicates to AP01 only
    ap_ids = [f.anti_pattern_id for f in findings]
    assert ap_ids == ["AP01"]

