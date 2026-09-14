"""
Unit tests for AP06 — Fragile Locators Detector.

Verifies:
1. Selenium absolute XPath -> flagged (Confidence.HIGH)
2. Selenium deep XPath -> flagged (Confidence.MEDIUM)
3. Selenium stable ID/name locator -> not flagged
4. Playwright deep CSS selector -> flagged (Confidence.MEDIUM)
5. Playwright get_by_role/get_by_label -> not flagged
6. Cypress nth-child selector -> flagged (Confidence.HIGH)
7. Cypress stable data-testid selector -> not flagged
8. Generated-looking CSS class -> flagged (Confidence.MEDIUM)
9. Normal meaningful class -> not flagged
10. Shallow XPath/CSS -> not flagged
11. Multiple fragile locators get appropriate line references
12. Empty/clean script -> no findings
13. Unsupported framework/language -> []
14. Finding metadata is correct
15. Ensure strings that are not actually used as locators are not blindly flagged
"""

import pytest
from src.detectors import detect_ap06
from src.models import Confidence, Framework, Language, Severity


class TestAP06Selenium:
    """Tests for Selenium (Python)."""

    def test_selenium_absolute_xpath_flagged(self):
        script = (
            'from selenium import webdriver\n'
            'from selenium.webdriver.common.by import By\n'
            'driver = webdriver.Chrome()\n'
            'element = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/button")\n'
        )
        findings = detect_ap06(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP06"
        assert f.anti_pattern_name == "Fragile Locators"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 4
        assert f.line_end == 4
        assert "absolute xpath" in f.reason.lower()
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_selenium_absolute_body_xpath_flagged(self):
        script = (
            'driver.find_element_by_xpath("/body/div/section/button")\n'
        )
        findings = detect_ap06(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].confidence == Confidence.HIGH
        assert "absolute XPath" in findings[0].reason

    def test_selenium_deep_xpath_flagged(self):
        script = (
            'driver.find_element(By.XPATH, "//div/div/div/button")\n'
        )
        findings = detect_ap06(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence == Confidence.MEDIUM
        assert "deeply nested XPath" in f.reason

    def test_selenium_deep_xpath_with_attribute_predicates(self):
        # Attribute predicates should not inflate structural tag count
        # Here only 2 tag levels: div and button
        script = (
            'driver.find_element(By.XPATH, "//div[@id=\'main\'][@class=\'active\']/button")\n'
        )
        findings = detect_ap06(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_selenium_stable_id_name_not_flagged(self):
        script = (
            'driver.find_element(By.ID, "login-btn")\n'
            'driver.find_element(By.NAME, "username")\n'
            'driver.find_element(By.XPATH, "//button[@id=\'submit\']")\n'
        )
        findings = detect_ap06(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestAP06Playwright:
    """Tests for Playwright (Python, JS, TS)."""

    def test_playwright_deep_css_selector_flagged(self):
        script = (
            'await page.locator("div > div > section > div > button").click();\n'
        )
        findings = detect_ap06(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence == Confidence.MEDIUM
        assert "deeply nested CSS hierarchy" in f.reason

    def test_playwright_role_and_label_not_flagged(self):
        script = (
            'await page.get_by_role("button", name="Submit").click()\n'
            'await page.get_by_label("Username").fill("admin")\n'
            'await page.get_by_text("Welcome back").is_visible()\n'
        )
        findings = detect_ap06(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_playwright_positional_selector_flagged(self):
        script = (
            'page.locator("ul.menu > li:nth-child(3)").click()\n'
        )
        findings = detect_ap06(script, Framework.PLAYWRIGHT, Language.TYPESCRIPT)
        assert len(findings) == 1
        assert findings[0].confidence == Confidence.HIGH
        assert "positional pseudo-class indexing" in findings[0].reason


class TestAP06Cypress:
    """Tests for Cypress (JS, TS)."""

    def test_cypress_nth_child_flagged(self):
        script = (
            'cy.get("table tbody tr:nth-child(2)").click();\n'
        )
        findings = detect_ap06(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence == Confidence.HIGH
        assert "positional pseudo-class indexing" in f.reason

    def test_cypress_nth_of_type_flagged(self):
        script = (
            'cy.get("div:nth-of-type(3)").should("be.visible");\n'
        )
        findings = detect_ap06(script, Framework.CYPRESS, Language.TYPESCRIPT)
        assert len(findings) == 1
        assert findings[0].confidence == Confidence.HIGH

    def test_cypress_stable_testid_not_flagged(self):
        script = (
            'cy.get("[data-testid=\'login-button\']").click();\n'
            'cy.get("[data-cy=\'submit\']").click();\n'
            'cy.get("#login").click();\n'
        )
        findings = detect_ap06(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_contains_not_flagged(self):
        script = (
            'cy.contains("Log In").click();\n'
            'cy.contains("button", "Submit").click();\n'
        )
        findings = detect_ap06(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0


class TestAP06GeneratedClasses:
    """Tests for generated and dynamic class detection."""

    def test_emotion_generated_class_flagged(self):
        script = (
            'cy.get(".css-abc123").click();\n'
        )
        findings = detect_ap06(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].confidence == Confidence.MEDIUM
        assert "auto-generated or dynamic class" in findings[0].reason

    def test_styled_components_generated_class_flagged(self):
        script = (
            'page.locator(".sc-aXZ123").click()\n'
        )
        findings = detect_ap06(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].confidence == Confidence.MEDIUM

    def test_hash_suffix_generated_class_flagged(self):
        script = (
            'cy.get(".header-7f8a9b").click();\n'
        )
        findings = detect_ap06(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].confidence == Confidence.MEDIUM

    def test_normal_meaningful_classes_not_flagged(self):
        script = (
            'cy.get(".btn-primary").click();\n'
            'cy.get(".card").should("exist");\n'
            'cy.get(".nav-item").first();\n'
            'cy.get(".form-control").type("test");\n'
            'cy.get(".col-md-6").should("be.visible");\n'
            'cy.get(".text-gray-500").should("be.visible");\n'
        )
        findings = detect_ap06(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0


class TestAP06ShallowAndClean:
    """Tests for shallow selectors and clean scripts."""

    def test_shallow_xpath_not_flagged(self):
        script = (
            'driver.find_element(By.XPATH, "//button")\n'
            'driver.find_element(By.XPATH, "//div/button")\n'
            'driver.find_element(By.XPATH, "//section//button")\n'
        )
        findings = detect_ap06(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_shallow_css_not_flagged(self):
        script = (
            'page.locator("div > button")\n'
            'page.locator(".container .btn")\n'
            'page.locator("header > nav > a")\n'
        )
        findings = detect_ap06(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_non_locator_strings_not_flagged(self):
        # URLs, messages, test data containing /html or :nth-child should NOT be flagged
        script = (
            'url = "https://example.com/html/body/div"\n'
            'message = "Found :nth-child(2) item in list"\n'
            'driver.get("https://example.com/html/body/report")\n'
            'assert text == "div > div > section > div > button"\n'
        )
        findings = detect_ap06(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_empty_and_whitespace_script(self):
        assert detect_ap06("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap06("   \n\n  ", Framework.PLAYWRIGHT, Language.JAVASCRIPT) == []

    def test_unsupported_framework_or_language(self):
        script = 'driver.find_element(By.XPATH, "/html/body/div")\n'
        assert detect_ap06(script, "unknown_fw", Language.PYTHON) == []
        assert detect_ap06(script, Framework.SELENIUM, Language.JAVASCRIPT) == []

    def test_multiple_fragile_locators_line_references(self):
        script = (
            '# Line 1: setup\n'
            'driver.find_element(By.XPATH, "/html/body/div")\n'            # Line 2
            'driver.find_element(By.ID, "username").send_keys("admin")\n'  # Line 3
            'driver.find_element(By.XPATH, "//div/div/div/button")\n'     # Line 4
        )
        findings = detect_ap06(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 2
        assert findings[0].line_start == 2
        assert findings[0].line_end == 2
        assert findings[0].confidence == Confidence.HIGH
        assert findings[1].line_start == 4
        assert findings[1].line_end == 4
        assert findings[1].confidence == Confidence.MEDIUM
