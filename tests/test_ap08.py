"""
Unit tests for AP08 — Testing Implementation Details Detector.

Verifies:
1. Python private state assertion -> flagged (Severity.MEDIUM, Confidence.MEDIUM).
2. Python internal method mock assertion -> flagged.
3. Python observable UI assertion -> not flagged.
4. Python mock setup without assertion -> not flagged.
5. JavaScript internal method expect(...).toHaveBeenCalled() -> flagged.
6. TypeScript private/internal property assertion -> flagged.
7. Cypress observable assertion -> not flagged.
8. Cypress mock/intercept setup without internal assertion -> not flagged.
9. Normal framework API usage -> not flagged.
10. Ambiguous assertion -> not flagged.
11. Multiple internal-detail assertions -> appropriate findings.
12. Correct AP08 metadata.
13. Empty/clean input -> no findings.
14. Unsupported framework/language -> no findings.
"""

import pytest
from src.detectors import detect_ap08
from src.models import Confidence, Framework, Language, Severity


class TestAP08Python:
    """Tests for Python (Selenium, Playwright)."""

    def test_python_private_state_assert_flagged(self):
        script = (
            'def test_component_state():\n'
            '    app.initialize()\n'
            '    assert app._internal_state == "ready"\n'
        )
        findings = detect_ap08(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP08"
        assert f.anti_pattern_name == "Testing Implementation Details"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.MEDIUM
        assert f.line_start == 3
        assert f.line_end == 3
        assert "_internal_state" in f.reason
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_python_private_cache_assert_flagged(self):
        script = (
            'def test_cache_population():\n'
            '    service.fetch_data()\n'
            '    assert "user_1" in service._cache\n'
        )
        findings = detect_ap08(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 3
        assert "_cache" in findings[0].reason

    def test_python_unittest_private_member_flagged(self):
        script = (
            'class TestService:\n'
            '    def test_internal_state(self):\n'
            '        service = Service()\n'
            '        self.assertEqual(service._internal_state, "active")\n'
        )
        findings = detect_ap08(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 4

    def test_python_internal_method_mock_assertion_flagged(self):
        script = (
            'def test_user_flow():\n'
            '    mock_service.internal_method.assert_called_once()\n'
        )
        findings = detect_ap08(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        f = findings[0]
        assert f.line_start == 2
        assert "assert_called_once" in f.reason
        assert "mock_service.internal_method" in f.reason

    def test_python_service_process_mock_assertion_flagged(self):
        script = (
            'def test_process_called():\n'
            '    service.process.assert_called_once()\n'
        )
        findings = detect_ap08(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 2

    def test_python_observable_ui_assertion_not_flagged(self):
        script = (
            'def test_login_title(driver):\n'
            '    driver.get("https://example.com/login")\n'
            '    assert "Dashboard" in driver.title\n'
            '    assert driver.current_url == "https://example.com/dashboard"\n'
        )
        findings = detect_ap08(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_python_mock_setup_without_assertion_not_flagged(self):
        script = (
            'from unittest.mock import Mock, patch\n'
            'def test_mock_setup():\n'
            '    service = Mock()\n'
            '    mock_api.get.return_value = {"status": "ok"}\n'
            '    result = perform_action(service)\n'
            '    assert result is True\n'
        )
        findings = detect_ap08(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestAP08JavaScriptTypeScript:
    """Tests for JavaScript and TypeScript (Playwright, Cypress)."""

    def test_js_mock_method_expect_to_have_been_called_flagged(self):
        script = (
            'test("calls internal method", async ({ page }) => {\n'
            '    await page.goto("/dashboard");\n'
            '    expect(mockService.internalMethod).toHaveBeenCalled();\n'
            '});\n'
        )
        findings = detect_ap08(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP08"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.MEDIUM
        assert f.line_start == 3
        assert "mockService.internalMethod" in f.reason

    def test_js_mock_method_expect_to_have_been_called_times_flagged(self):
        script = (
            'test("processes event once", async () => {\n'
            '    expect(mockService.process).toHaveBeenCalledTimes(1);\n'
            '});\n'
        )
        findings = detect_ap08(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 2

    def test_ts_private_property_assertion_flagged(self):
        script = (
            'test("component internal state", async ({ page }: { page: Page }) => {\n'
            '    await page.goto("/profile");\n'
            '    expect(component._internalState).toBe("ready");\n'
            '});\n'
        )
        findings = detect_ap08(script, Framework.PLAYWRIGHT, Language.TYPESCRIPT)
        assert len(findings) == 1
        f = findings[0]
        assert f.line_start == 3
        assert "component._internalState" in f.reason

    def test_ts_explicit_internal_property_assertion_flagged(self):
        script = (
            'test("app internal state", async () => {\n'
            '    expect(app.internalState).toBe(true);\n'
            '});\n'
        )
        findings = detect_ap08(script, Framework.PLAYWRIGHT, Language.TYPESCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 2


class TestAP08Cypress:
    """Tests for Cypress."""

    def test_cypress_observable_assertion_not_flagged(self):
        script = (
            'it("displays welcome message", () => {\n'
            '    cy.visit("/home");\n'
            '    cy.get(".success").should("be.visible");\n'
            '    cy.get("h1").should("contain.text", "Welcome");\n'
            '});\n'
        )
        findings = detect_ap08(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_mock_intercept_setup_not_flagged(self):
        script = (
            'it("stubs api call", () => {\n'
            '    cy.intercept("GET", "/api/users", { fixture: "users.json" }).as("getUsers");\n'
            '    cy.visit("/users");\n'
            '    cy.get(".user-row").should("have.length", 5);\n'
            '});\n'
        )
        findings = detect_ap08(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_internal_spy_assertion_flagged(self):
        script = (
            'it("checks spy call", () => {\n'
            '    cy.visit("/admin");\n'
            '    cy.get("@mockService").should("have.been.called");\n'
            '});\n'
        )
        findings = detect_ap08(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 3


class TestAP08ExclusionsAndMetadata:
    """Tests for edge cases, exclusions, and metadata checks."""

    def test_normal_framework_apis_not_flagged(self):
        script = (
            'from playwright.sync_api import expect\n'
            'def test_playwright_standard(page):\n'
            '    page.goto("https://example.com")\n'
            '    expect(page.locator("#header")).to_be_visible()\n'
            '    expect(page).to_have_url("https://example.com")\n'
        )
        findings = detect_ap08(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_ambiguous_variable_assertion_not_flagged(self):
        script = (
            'def test_calculate():\n'
            '    result = calculate_total(10, 20)\n'
            '    status = get_status()\n'
            '    assert result == 30\n'
            '    assert status == "active"\n'
        )
        findings = detect_ap08(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_multiple_internal_detail_assertions_flagged(self):
        script = (
            'def test_multiple_internals():\n'
            '    assert app._internal_state == "ready"\n'
            '    mock_service.internal_method.assert_called_once()\n'
            '    assert service._cache == {}\n'
        )
        findings = detect_ap08(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 3
        assert [f.line_start for f in findings] == [2, 3, 4]

    def test_empty_and_clean_script(self):
        assert detect_ap08("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap08("   \n\n  ", Framework.PLAYWRIGHT, Language.JAVASCRIPT) == []

    def test_unsupported_framework_or_language(self):
        script = 'assert app._state == "ready"\n'
        assert detect_ap08(script, "unknown_fw", Language.PYTHON) == []
        assert detect_ap08(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
