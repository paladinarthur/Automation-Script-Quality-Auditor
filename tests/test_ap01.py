"""
Unit tests for AP01 — Hardcoded Waits Detector.

Verifies:
- All positive cases across supported frameworks and languages
- All negative cases (expected condition waits, aliases, comments, normal numeric code)
- Framework isolation (cross-framework patterns not flagged)
- Exact Finding model attributes (ID, Severity, Confidence, Line numbers, Snippet, Reason)
- Multi-line / multiple occurrence tracking
"""

import pytest
from src.detectors import detect_ap01
from src.models import Confidence, Framework, Language, Severity


class TestAP01PositiveCases:
    """Positive test cases where AP01 must be flagged."""

    def test_selenium_python_time_sleep(self):
        script = "from selenium import webdriver\nimport time\n\ntime.sleep(5)\n"
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 4
        assert f.line_end == 4
        assert f.code_snippet == "time.sleep(5)"
        assert bool(f.reason)
        assert "Fixed delay" in f.reason
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_playwright_python_time_sleep(self):
        script = "import time\n\ndef test_pw():\n    time.sleep(2.5)\n"
        findings = detect_ap01(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 4
        assert f.line_end == 4
        assert f.code_snippet == "time.sleep(2.5)"
        assert bool(f.reason)
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_playwright_python_wait_for_timeout(self):
        script = "async def test_flow(page):\n    await page.wait_for_timeout(3000)\n"
        findings = detect_ap01(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 2
        assert f.line_end == 2
        assert f.code_snippet == "await page.wait_for_timeout(3000)"
        assert bool(f.reason)
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_playwright_javascript_wait_for_timeout(self):
        script = "const { test } = require('@playwright/test');\n\ntest('demo', async ({ page }) => {\n  await page.waitForTimeout(5000);\n});\n"
        findings = detect_ap01(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 4
        assert f.line_end == 4
        assert f.code_snippet == "await page.waitForTimeout(5000);"
        assert bool(f.reason)
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_playwright_typescript_wait_for_timeout(self):
        script = "import { test, Page } from '@playwright/test';\n\ntest('test', async ({ page }: { page: Page }) => {\n  await page.waitForTimeout(10000);\n});\n"
        findings = detect_ap01(script, Framework.PLAYWRIGHT, Language.TYPESCRIPT)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 4
        assert f.line_end == 4
        assert f.code_snippet == "await page.waitForTimeout(10000);"
        assert bool(f.reason)
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_cypress_javascript_cy_wait_numeric(self):
        script = "describe('login', () => {\n  it('loads', () => {\n    cy.wait(5000);\n  });\n});\n"
        findings = detect_ap01(script, Framework.CYPRESS, Language.JAVASCRIPT)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 3
        assert f.line_end == 3
        assert f.code_snippet == "cy.wait(5000);"
        assert bool(f.reason)
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_cypress_typescript_cy_wait_numeric(self):
        script = "it('should wait', () => {\n  cy.get('#submit').click();\n  cy.wait(2000);\n});\n"
        findings = detect_ap01(script, Framework.CYPRESS, Language.TYPESCRIPT)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 3
        assert f.line_end == 3
        assert f.code_snippet == "cy.wait(2000);"
        assert bool(f.reason)
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_cypress_wait_with_options(self):
        script = "cy.wait(5000, { log: false });\n"
        findings = detect_ap01(script, Framework.CYPRESS, Language.JAVASCRIPT)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 1
        assert f.code_snippet == "cy.wait(5000, { log: false });"
        assert bool(f.reason)


class TestAP01NegativeCases:
    """Negative test cases where AP01 must NOT be flagged."""

    def test_selenium_webdriverwait_until(self):
        script = (
            "from selenium.webdriver.support.ui import WebDriverWait\n"
            "from selenium.webdriver.support import expected_conditions as EC\n"
            "from selenium.webdriver.common.by import By\n\n"
            "element = WebDriverWait(driver, 10).until(\n"
            "    EC.presence_of_element_located((By.ID, 'myDynamicElement'))\n"
            ")\n"
        )
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_cypress_alias_wait(self):
        script = (
            "cy.intercept('GET', '/users').as('getUsers');\n"
            "cy.visit('/users');\n"
            "cy.wait('@getUsers');\n"
        )
        findings = detect_ap01(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_alias_at_login(self):
        script = "cy.wait('@login');\n"
        findings = detect_ap01(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_multiple_alias_wait(self):
        script = "cy.wait(['@getUsers', '@getSettings']);\n"
        findings = detect_ap01(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_alias_array_at_login(self):
        script = "cy.wait(['@login']);\n"
        findings = detect_ap01(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_python_commented_out_wait(self):
        script = (
            "# time.sleep(5)\n"
            "   # time.sleep(10)\n"
            "print('hello')  # time.sleep(2)\n"
        )
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_python_docstring_wait(self):
        script = (
            '"""\n'
            "time.sleep(5)\n"
            '"""\n'
            "def test_func():\n"
            "    pass\n"
        )
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_javascript_commented_out_wait(self):
        script = (
            "// page.waitForTimeout(5000);\n"
            "   // cy.wait(3000);\n"
            "/* page.waitForTimeout(5000) */\n"
            "const x = 1; // cy.wait(2000)\n"
        )
        findings_pw = detect_ap01(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings_pw) == 0

        findings_cy = detect_ap01(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings_cy) == 0

    def test_normal_numeric_code(self):
        script = (
            "age = 25\n"
            "count = 10\n"
            "for i in range(5):\n"
            "    print(i)\n"
            "assert response.status_code == 200\n"
        )
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestFrameworkIsolationAndCrossFrameworkRules:
    """Tests ensuring framework-specific wait calls do not trigger in other frameworks."""

    def test_cypress_wait_ignored_in_selenium(self):
        # cy.wait should not be flagged when analyzing Selenium Python
        script = "cy.wait(5000)\n"
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_time_sleep_ignored_in_cypress(self):
        # time.sleep is not a valid Cypress wait construct
        script = "time.sleep(5)\n"
        findings = detect_ap01(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_unsupported_framework_language_pair(self):
        # Selenium + JavaScript is unsupported; should return empty list
        script = "time.sleep(5)\n"
        findings = detect_ap01(script, "selenium", "javascript")
        assert len(findings) == 0

    def test_all_unsupported_combinations(self):
        script = "time.sleep(5)\ncy.wait(5000)\npage.waitForTimeout(5000)\n"
        # Selenium + JS
        assert detect_ap01(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
        # Selenium + TS
        assert detect_ap01(script, Framework.SELENIUM, Language.TYPESCRIPT) == []
        # Cypress + Python
        assert detect_ap01(script, Framework.CYPRESS, Language.PYTHON) == []

    def test_empty_and_whitespace_script(self):
        assert detect_ap01("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap01("   \n\n  ", Framework.SELENIUM, Language.PYTHON) == []


class TestFindingModelContractAndAttributes:
    """Explicitly verifies all Finding attributes required by the specification."""

    def test_exact_finding_fields_contract(self):
        script = "time.sleep(12)\n"
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP01"
        assert f.anti_pattern_name == "Hardcoded Waits"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 1
        assert f.line_end == 1
        assert f.code_snippet == "time.sleep(12)"
        assert isinstance(f.reason, str) and len(f.reason.strip()) > 0
        assert f.explanation == ""
        assert f.suggested_fix == ""


class TestMultipleWaitsAndLineNumbers:
    """Tests that scripts with multiple waits report accurate line numbers for each."""

    def test_multiple_waits_different_lines(self):
        script = (
            "driver.get('https://example.com')\n"  # Line 1
            "time.sleep(2)\n"                     # Line 2
            "driver.find_element_by_id('btn').click()\n"  # Line 3
            "\n"                                   # Line 4
            "time.sleep(10)\n"                    # Line 5
        )
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)

        assert len(findings) == 2
        assert findings[0].line_start == 2
        assert findings[0].line_end == 2
        assert findings[0].code_snippet == "time.sleep(2)"
        assert findings[0].id == "AP01-L2"

        assert findings[1].line_start == 5
        assert findings[1].line_end == 5
        assert findings[1].code_snippet == "time.sleep(10)"
        assert findings[1].id == "AP01-L5"

    def test_wait_with_trailing_inline_comment(self):
        script = "time.sleep(5)  # Wait for page to settle\n"
        findings = detect_ap01(script, Framework.SELENIUM, Language.PYTHON)

        assert len(findings) == 1
        assert findings[0].line_start == 1
        assert findings[0].line_end == 1
        assert findings[0].code_snippet == "time.sleep(5)  # Wait for page to settle"

    def test_three_waits_distinct_lines(self):
        script = (
            "# Setup\n"                                # Line 1
            "await page.wait_for_timeout(1000)\n"       # Line 2
            "await page.click('#login')\n"              # Line 3
            "\n"                                        # Line 4
            "time.sleep(2.5)\n"                         # Line 5
            "await page.fill('#input', 'text')\n"       # Line 6
            "\n"                                        # Line 7
            "await page.wait_for_timeout(5000)\n"       # Line 8
        )
        findings = detect_ap01(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 3
        assert [f.line_start for f in findings] == [2, 5, 8]
        assert [f.line_end for f in findings] == [2, 5, 8]
        assert findings[0].code_snippet == "await page.wait_for_timeout(1000)"
        assert findings[1].code_snippet == "time.sleep(2.5)"
        assert findings[2].code_snippet == "await page.wait_for_timeout(5000)"
        for f in findings:
            assert f.anti_pattern_id == "AP01"
            assert f.anti_pattern_name == "Hardcoded Waits"
            assert f.severity == Severity.HIGH
            assert f.confidence == Confidence.HIGH
            assert bool(f.reason)
            assert f.explanation == ""
            assert f.suggested_fix == ""
