"""
Unit tests for AP07 — Missing Assertions Detector.

Verifies:
1. Selenium Python test with browser actions and no assertion -> 1 finding.
2. Selenium Python test with assert -> 0 findings.
3. Playwright Python test with expect(...) -> 0 findings.
4. Playwright Python test with browser actions but no expect/assert -> 1 finding.
5. Playwright JavaScript test with expect(...) -> 0 findings.
6. Playwright TypeScript test with expect(...) -> 0 findings.
7. Playwright JS/TS test with browser actions but no assertion -> 1 finding.
8. Cypress JS test with .should(...) -> 0 findings.
9. Cypress JS test with browser actions but no assertion -> 1 finding.
10. Cypress TypeScript equivalents.
11. Helper function without assertion -> should not automatically be flagged.
12. Setup-only function -> should not be flagged.
13. Empty/clean script -> 0 findings.
14. Test with no meaningful browser/test action -> 0 findings.
15. Correct line references and metadata.
16. Unsupported framework/language -> [].
17. Comments/strings containing "assert", "expect", or ".should()" must not count as real assertions.
18. Function named check_* that performs browser actions without assertions is not treated as an assertion.
"""

import pytest
from src.detectors import detect_ap07
from src.models import Confidence, Framework, Language, Severity


class TestAP07Selenium:
    """Tests for Selenium (Python)."""

    def test_selenium_test_with_actions_no_assertion_flagged(self):
        script = (
            'from selenium import webdriver\n'
            'def test_user_login():\n'
            '    driver = webdriver.Chrome()\n'
            '    driver.get("https://example.com/login")\n'
            '    driver.find_element("id", "user").send_keys("admin")\n'
            '    driver.find_element("id", "btn").click()\n'
        )
        findings = detect_ap07(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP07"
        assert f.anti_pattern_name == "Missing Assertions"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 2
        assert f.line_end == 6
        assert "test_user_login" in f.reason
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_selenium_test_with_assert_not_flagged(self):
        script = (
            'def test_login_success():\n'
            '    driver.get("https://example.com/login")\n'
            '    driver.find_element("id", "btn").click()\n'
            '    assert "Dashboard" in driver.title\n'
        )
        findings = detect_ap07(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_selenium_test_with_unittest_assertion_not_flagged(self):
        script = (
            'class LoginTest:\n'
            '    def test_login(self):\n'
            '        self.driver.get("https://example.com/login")\n'
            '        self.assertEqual(self.driver.title, "Home")\n'
        )
        findings = detect_ap07(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestAP07Playwright:
    """Tests for Playwright."""

    def test_playwright_python_with_expect_not_flagged(self):
        script = (
            'from playwright.sync_api import expect\n'
            'def test_search(page):\n'
            '    page.goto("https://example.com")\n'
            '    page.fill("#search", "query")\n'
            '    expect(page.locator(".result")).to_be_visible()\n'
        )
        findings = detect_ap07(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_playwright_python_no_assertion_flagged(self):
        script = (
            'def test_checkout(page):\n'
            '    page.goto("https://example.com/cart")\n'
            '    page.click("#checkout")\n'
        )
        findings = detect_ap07(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 1

    def test_playwright_js_with_expect_not_flagged(self):
        script = (
            'test("user login", async ({ page }) => {\n'
            '    await page.goto("/login");\n'
            '    await page.click("#btn");\n'
            '    await expect(page.locator("#welcome")).toBeVisible();\n'
            '});\n'
        )
        findings = detect_ap07(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_playwright_ts_with_expect_not_flagged(self):
        script = (
            'test("profile update", async ({ page }: { page: Page }) => {\n'
            '    await page.goto("/profile");\n'
            '    await page.fill("#name", "Alice");\n'
            '    await expect(page).toHaveURL("/profile");\n'
            '});\n'
        )
        findings = detect_ap07(script, Framework.PLAYWRIGHT, Language.TYPESCRIPT)
        assert len(findings) == 0

    def test_playwright_js_no_assertion_flagged(self):
        script = (
            'test("unverified workflow", async ({ page }) => {\n'
            '    await page.goto("/dashboard");\n'
            '    await page.click(".menu-item");\n'
            '});\n'
        )
        findings = detect_ap07(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH
        assert findings[0].confidence == Confidence.HIGH


class TestAP07Cypress:
    """Tests for Cypress."""

    def test_cypress_js_with_should_not_flagged(self):
        script = (
            'it("displays items", () => {\n'
            '    cy.visit("/products");\n'
            '    cy.get(".product").should("have.length", 3);\n'
            '});\n'
        )
        findings = detect_ap07(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_js_with_and_not_flagged(self):
        script = (
            'it("checks button state", () => {\n'
            '    cy.visit("/form");\n'
            '    cy.get("button").should("be.visible").and("be.enabled");\n'
            '});\n'
        )
        findings = detect_ap07(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_ts_no_assertion_flagged(self):
        script = (
            'it("navigates without verification", () => {\n'
            '    cy.visit("/admin");\n'
            '    cy.get("#submit").click();\n'
            '});\n'
        )
        findings = detect_ap07(script, Framework.CYPRESS, Language.TYPESCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 1


class TestAP07BoundariesAndExclusions:
    """Tests for setup/helper exclusions and boundary rules."""

    def test_python_helper_function_not_flagged(self):
        script = (
            'def login_helper(driver, user, pwd):\n'
            '    driver.get("https://example.com")\n'
            '    driver.find_element("id", "u").send_keys(user)\n'
            '    driver.find_element("id", "btn").click()\n'
        )
        findings = detect_ap07(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_python_setup_function_not_flagged(self):
        script = (
            'def setup_method(self):\n'
            '    self.driver = webdriver.Chrome()\n'
            '    self.driver.get("https://example.com")\n'
        )
        findings = detect_ap07(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_test_without_browser_actions_not_flagged(self):
        script = (
            'def test_calculate():\n'
            '    x = 1 + 2\n'
            '    y = x * 3\n'
        )
        findings = detect_ap07(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_assertion_in_comment_or_string_does_not_count(self):
        # Comments or string literals containing assert/expect should not satisfy the rule
        script = (
            'def test_fake_assertion():\n'
            '    driver.get("https://example.com")\n'
            '    driver.find_element("id", "btn").click()\n'
            '    # assert page is loaded\n'
            '    msg = "expect this to work"\n'
        )
        findings = detect_ap07(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1

    def test_check_function_without_assert_is_not_treated_as_assertion(self):
        # A method called check_status that only clicks around does not count as an assertion
        script = (
            'def test_with_check_method():\n'
            '    driver.get("https://example.com")\n'
            '    check_profile(driver)\n'
            '\n'
            'def check_profile(driver):\n'
            '    driver.find_element("id", "profile").click()\n'
        )
        findings = detect_ap07(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 1

    def test_empty_and_clean_script(self):
        assert detect_ap07("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap07("   \n\n  ", Framework.PLAYWRIGHT, Language.JAVASCRIPT) == []

    def test_unsupported_framework_or_language(self):
        script = 'def test_foo(): driver.get("/");\n'
        assert detect_ap07(script, "unknown_fw", Language.PYTHON) == []
        assert detect_ap07(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
