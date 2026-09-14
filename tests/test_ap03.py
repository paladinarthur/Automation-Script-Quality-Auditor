"""
Unit tests for AP03 — Copy-Paste / Duplicated Code Detector (Exact Duplicates).

Verifies:
- Exact 3-line duplicate block
- Exact 4-line duplicate block
- Duplicate blocks separated by other code
- Different indentation still matches
- Comments/blank lines between statements don't prevent match
- Both duplicate locations reported as separate Findings
- Correct line_start and line_end
- Correct code_snippet
- HIGH confidence, MEDIUM severity, non-empty reason, empty explanation/suggested_fix
- Single repeated statement is NOT flagged
- Two repeated statements are NOT flagged
- Imports are NOT flagged
- Comments-only / blank-only content is NOT flagged
- Unique blocks are NOT flagged
- Multiple independent duplicate blocks
"""

import pytest
from src.detectors import detect_ap03
from src.models import Confidence, Framework, Language, Severity


class TestAP03PositiveCases:
    """Positive test cases where exact duplicated blocks must be flagged."""

    def test_exact_three_line_duplicate(self):
        script = (
            'page.click("#login")\n'                 # Line 1
            'page.fill("#username", "admin")\n'      # Line 2
            'page.click("#submit")\n'                # Line 3
            '\n'                                     # Line 4
            'page.goto("/home")\n'                   # Line 5
            '\n'                                     # Line 6
            'page.click("#login")\n'                 # Line 7
            'page.fill("#username", "admin")\n'      # Line 8
            'page.click("#submit")\n'                # Line 9
        )
        findings = detect_ap03(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 2
        # First occurrence
        f1 = findings[0]
        assert f1.anti_pattern_id == "AP03"
        assert f1.anti_pattern_name == "Copy-Paste / Duplicated Code"
        assert f1.severity == Severity.MEDIUM
        assert f1.confidence == Confidence.HIGH
        assert f1.line_start == 1
        assert f1.line_end == 3
        assert 'page.click("#login")' in f1.code_snippet
        assert 'page.click("#submit")' in f1.code_snippet
        assert bool(f1.reason)
        assert "lines 7–9" in f1.reason
        assert f1.explanation == ""
        assert f1.suggested_fix == ""

        # Second occurrence
        f2 = findings[1]
        assert f2.anti_pattern_id == "AP03"
        assert f2.severity == Severity.MEDIUM
        assert f2.confidence == Confidence.HIGH
        assert f2.line_start == 7
        assert f2.line_end == 9
        assert 'page.click("#login")' in f2.code_snippet
        assert 'page.click("#submit")' in f2.code_snippet
        assert "lines 1–3" in f2.reason

    def test_exact_four_line_duplicate(self):
        script = (
            'driver.find_element_by_id("u").send_keys("user")\n'   # Line 1
            'driver.find_element_by_id("p").send_keys("pass")\n'   # Line 2
            'driver.find_element_by_id("login").click()\n'         # Line 3
            'assert driver.title == "Dashboard"\n'                 # Line 4
            '\n'                                                   # Line 5
            'driver.get("https://example.com/login")\n'            # Line 6
            '\n'                                                   # Line 7
            'driver.find_element_by_id("u").send_keys("user")\n'   # Line 8
            'driver.find_element_by_id("p").send_keys("pass")\n'   # Line 9
            'driver.find_element_by_id("login").click()\n'         # Line 10
            'assert driver.title == "Dashboard"\n'                 # Line 11
        )
        findings = detect_ap03(script, Framework.SELENIUM, Language.PYTHON)

        # Must report full 4-line block and NOT generate overlapping 3-line findings
        assert len(findings) == 2
        assert findings[0].line_start == 1
        assert findings[0].line_end == 4
        assert findings[1].line_start == 8
        assert findings[1].line_end == 11
        assert "4 statements" in findings[0].reason
        assert "4 statements" in findings[1].reason

    def test_different_indentation_matches(self):
        script = (
            'def test_one():\n'
            '    page.click("#login")\n'            # Line 2
            '    page.fill("#username", "admin")\n' # Line 3
            '    page.click("#submit")\n'           # Line 4
            '\n'
            'def test_two():\n'
            '        page.click("#login")\n'            # Line 7
            '        page.fill("#username", "admin")\n' # Line 8
            '        page.click("#submit")\n'           # Line 9
        )
        findings = detect_ap03(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 2
        assert findings[0].line_start == 2
        assert findings[0].line_end == 4
        assert findings[1].line_start == 7
        assert findings[1].line_end == 9

    def test_comments_and_blank_lines_within_blocks(self):
        script = (
            'cy.get("#login").click();\n'             # Line 1
            '// enter username\n'                     # Line 2
            'cy.get("#username").type("admin");\n'    # Line 3
            '\n'                                      # Line 4
            'cy.get("#submit").click();\n'            # Line 5
            '\n'                                      # Line 6
            'cy.visit("/dashboard");\n'               # Line 7
            '\n'                                      # Line 8
            'cy.get("#login").click();\n'             # Line 9
            'cy.get("#username").type("admin");\n'    # Line 10
            'cy.get("#submit").click();\n'            # Line 11
        )
        findings = detect_ap03(script, Framework.CYPRESS, Language.JAVASCRIPT)

        assert len(findings) == 2
        # First block spans lines 1 to 5
        assert findings[0].line_start == 1
        assert findings[0].line_end == 5
        # Second block spans lines 9 to 11
        assert findings[1].line_start == 9
        assert findings[1].line_end == 11

    def test_multiple_independent_duplicate_blocks(self):
        script = (
            '# Block A\n'
            'page.click("#btn1")\n'       # Line 2
            'page.fill("#in1", "val1")\n' # Line 3
            'page.press("Enter")\n'       # Line 4
            '\n'
            '# Block B\n'
            'page.click("#btn2")\n'       # Line 7
            'page.fill("#in2", "val2")\n' # Line 8
            'page.press("Escape")\n'      # Line 9
            '\n'
            '# Repeat Block A\n'
            'page.click("#btn1")\n'       # Line 12
            'page.fill("#in1", "val1")\n' # Line 13
            'page.press("Enter")\n'       # Line 14
            '\n'
            '# Repeat Block B\n'
            'page.click("#btn2")\n'       # Line 17
            'page.fill("#in2", "val2")\n' # Line 18
            'page.press("Escape")\n'      # Line 19
        )
        findings = detect_ap03(script, Framework.PLAYWRIGHT, Language.TYPESCRIPT)

        assert len(findings) == 4
        # Block A occurrences
        assert findings[0].line_start == 2
        assert findings[0].line_end == 4
        assert findings[1].line_start == 7
        assert findings[1].line_end == 9
        assert findings[2].line_start == 12
        assert findings[2].line_end == 14
        assert findings[3].line_start == 17
        assert findings[3].line_end == 19


class TestAP03NegativeCases:
    """Negative test cases where AP03 must NOT be flagged."""

    def test_single_repeated_statement_not_flagged(self):
        script = (
            'page.click("#login")\n'
            'page.goto("/home")\n'
            'page.click("#login")\n'
        )
        findings = detect_ap03(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_two_repeated_statements_not_flagged(self):
        script = (
            'page.click("#login")\n'
            'page.fill("#username", "admin")\n'
            'page.goto("/home")\n'
            'page.click("#login")\n'
            'page.fill("#username", "admin")\n'
        )
        findings = detect_ap03(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_imports_not_flagged_as_duplicates(self):
        script = (
            'from selenium import webdriver\n'
            'from selenium.webdriver.common.by import By\n'
            'import time\n'
            '\n'
            'driver = webdriver.Chrome()\n'
            '\n'
            'from selenium import webdriver\n'
            'from selenium.webdriver.common.by import By\n'
            'import time\n'
        )
        findings = detect_ap03(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_js_require_imports_not_flagged(self):
        script = (
            'const { test } = require("@playwright/test");\n'
            'const { expect } = require("@playwright/test");\n'
            'const path = require("path");\n'
            '\n'
            'test("one", () => {});\n'
            '\n'
            'const { test } = require("@playwright/test");\n'
            'const { expect } = require("@playwright/test");\n'
            'const path = require("path");\n'
        )
        findings = detect_ap03(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_comments_and_blank_lines_only_not_flagged(self):
        script = (
            '# Comment line 1\n'
            '# Comment line 2\n'
            '# Comment line 3\n'
            '\n\n'
            '# Comment line 1\n'
            '# Comment line 2\n'
            '# Comment line 3\n'
        )
        findings = detect_ap03(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_unique_blocks_not_flagged(self):
        script = (
            'page.click("#login")\n'
            'page.fill("#username", "admin")\n'
            'page.click("#submit")\n'
            'page.goto("/dashboard")\n'
            'page.click("#logout")\n'
            'page.close()\n'
        )
        findings = detect_ap03(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_unsupported_framework_language(self):
        script = (
            'page.click("#login")\n'
            'page.fill("#username", "admin")\n'
            'page.click("#submit")\n'
            '\n'
            'page.click("#login")\n'
            'page.fill("#username", "admin")\n'
            'page.click("#submit")\n'
        )
        assert detect_ap03(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
        assert detect_ap03(script, Framework.CYPRESS, Language.PYTHON) == []

    def test_empty_and_whitespace_script(self):
        assert detect_ap03("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap03("   \n\t\n  ", Framework.SELENIUM, Language.PYTHON) == []
