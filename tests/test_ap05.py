"""
Unit tests for AP05 — Missing Abstractions Detector.

Verifies:
- Repeated multi-step browser workflow without abstraction -> AP05 findings
- Same workflow extracted into a helper function -> clean (0 AP05 findings)
- Single repeated statement -> clean
- Common setup / imports -> clean
- Unrelated similar browser actions -> clean
- AP03 duplication alone (non-browser code) does NOT trigger AP05
- Correct framework/language support across Selenium, Playwright, and Cypress
- Correct Finding metadata (Severity.MEDIUM, Confidence.MEDIUM, line references, reason)
- Empty and clean scripts -> 0 findings
"""

import pytest
from src.detectors import detect_ap03, detect_ap05
from src.models import Confidence, Framework, Language, Severity


class TestAP05PositiveCases:
    """Positive test cases where repeated browser workflows must be flagged."""

    def test_playwright_repeated_login_workflow(self):
        script = (
            '# Test 1\n'
            'page.goto("/login")\n'                     # Line 2
            'page.fill("#username", "admin")\n'         # Line 3
            'page.fill("#password", "secret")\n'        # Line 4
            'page.click("#submit")\n'                   # Line 5
            'assert page.title() == "Dashboard"\n'      # Line 6
            '\n'
            '# Test 2\n'
            'page.goto("/login")\n'                     # Line 9
            'page.fill("#username", "admin")\n'         # Line 10
            'page.fill("#password", "secret")\n'        # Line 11
            'page.click("#submit")\n'                   # Line 12
            'assert page.url() == "/dashboard"\n'       # Line 13
        )
        findings = detect_ap05(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 2
        f1, f2 = findings[0], findings[1]

        assert f1.anti_pattern_id == "AP05"
        assert f1.anti_pattern_name == "Missing Abstractions"
        assert f1.severity == Severity.MEDIUM
        assert f1.confidence == Confidence.MEDIUM
        assert f1.line_start == 2
        assert f1.line_end == 5
        assert 'page.fill("#username", "admin")' in f1.code_snippet
        assert "lines 9–12" in f1.reason
        assert f1.explanation == ""
        assert f1.suggested_fix == ""

        assert f2.anti_pattern_id == "AP05"
        assert f2.line_start == 9
        assert f2.line_end == 12
        assert "lines 2–5" in f2.reason

    def test_cypress_repeated_checkout_workflow(self):
        script = (
            'it("test 1", () => {\n'
            '  cy.visit("/cart");\n'           # Line 2
            '  cy.get("#item-1").click();\n'   # Line 3
            '  cy.get("#checkout").click();\n' # Line 4
            '});\n'
            '\n'
            'it("test 2", () => {\n'
            '  cy.visit("/cart");\n'           # Line 8
            '  cy.get("#item-1").click();\n'   # Line 9
            '  cy.get("#checkout").click();\n' # Line 10
            '});\n'
        )
        findings = detect_ap05(script, Framework.CYPRESS, Language.JAVASCRIPT)

        assert len(findings) == 2
        assert findings[0].anti_pattern_id == "AP05"
        assert findings[0].line_start == 2
        assert findings[0].line_end == 4
        assert findings[1].line_start == 8
        assert findings[1].line_end == 10

    def test_selenium_python_repeated_form_interaction(self):
        script = (
            'driver.get("https://example.com")\n'
            'driver.find_element_by_id("name").send_keys("Arthur")\n'
            'driver.find_element_by_id("submit").click()\n'
            '\n'
            'driver.get("https://example.com")\n'
            'driver.find_element_by_id("name").send_keys("Arthur")\n'
            'driver.find_element_by_id("submit").click()\n'
        )
        findings = detect_ap05(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 2
        assert findings[0].anti_pattern_id == "AP05"


class TestAP05NegativeCases:
    """Negative test cases where AP05 must NOT be flagged."""

    def test_abstracted_helper_not_flagged(self):
        # When extracted into a helper and called, there is no repeated raw workflow
        script = (
            'def login(page, username, password):\n'
            '    page.goto("/login")\n'
            '    page.fill("#username", username)\n'
            '    page.fill("#password", password)\n'
            '    page.click("#submit")\n'
            '\n'
            'def test_one(page):\n'
            '    login(page, "admin", "secret")\n'
            '    page.click("#reports")\n'
            '\n'
            'def test_two(page):\n'
            '    login(page, "user", "pass123")\n'
            '    page.click("#profile")\n'
        )
        findings = detect_ap05(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_single_repeated_statement_not_flagged(self):
        script = (
            'page.click("#btn")\n'
            'page.goto("/home")\n'
            'page.click("#btn")\n'
        )
        findings = detect_ap05(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_common_setup_and_imports_not_flagged(self):
        script = (
            'import time\n'
            'from selenium import webdriver\n'
            'from selenium.webdriver.common.by import By\n'
            '\n'
            'import time\n'
            'from selenium import webdriver\n'
            'from selenium.webdriver.common.by import By\n'
        )
        findings = detect_ap05(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_unrelated_similar_browser_actions_not_flagged(self):
        # Different targets, not a repeated cohesive workflow
        script = (
            'page.click("#header-home")\n'
            'page.click("#sidebar-link")\n'
            'page.click("#footer-about")\n'
            '\n'
            'page.click("#header-logout")\n'
            'page.click("#modal-close")\n'
            'page.click("#tab-settings")\n'
        )
        findings = detect_ap05(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_ap03_duplicate_without_browser_workflow_not_flagged_by_ap05(self):
        # Mathematical / data calculation duplication:
        # AP03 MUST detect code duplication, but AP05 MUST NOT flag this as a missing browser abstraction.
        script = (
            'x = a * 10\n'
            'y = b * 20\n'
            'z = x + y\n'
            '\n'
            'print(z)\n'
            '\n'
            'x = a * 10\n'
            'y = b * 20\n'
            'z = x + y\n'
        )
        # AP03 correctly flags code duplication
        ap03_findings = detect_ap03(script, Framework.SELENIUM, Language.PYTHON)
        assert len(ap03_findings) == 2

        # AP05 must NOT trigger because there is no browser automation workflow
        ap05_findings = detect_ap05(script, Framework.SELENIUM, Language.PYTHON)
        assert len(ap05_findings) == 0

    def test_empty_and_clean_script(self):
        assert detect_ap05("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap05("   \n\n  ", Framework.SELENIUM, Language.PYTHON) == []

        clean_script = (
            'def test_clean(page):\n'
            '    page.goto("https://example.com")\n'
            '    page.click("#submit")\n'
        )
        assert detect_ap05(clean_script, Framework.PLAYWRIGHT, Language.PYTHON) == []

    def test_unsupported_framework_language(self):
        script = (
            'page.click("#a")\n'
            'page.fill("#b", "c")\n'
            'page.click("#d")\n'
            'page.click("#a")\n'
            'page.fill("#b", "c")\n'
            'page.click("#d")\n'
        )
        assert detect_ap05(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
        assert detect_ap05(script, Framework.CYPRESS, Language.PYTHON) == []
