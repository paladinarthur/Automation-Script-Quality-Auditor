"""
Unit tests for AP04 — Poor Test Structure Detector.

Verifies:
- Signal 1: Potentially Large Test (29 stmts -> clean, 30 stmts -> AP04 finding)
- Comments, blank lines, and imports do not count toward statement count
- Signal 2: Excessive Nesting (depth 3 -> clean, depth 4 -> AP04 finding)
- Comments and braces inside strings do not increase nesting depth
- Both Python and JavaScript/TypeScript tests
- Correct line_start, line_end, code_snippet, reason
- MEDIUM severity and MEDIUM confidence
- Top-level code not treated as test
- Multiple functions with isolated signal reporting
"""

import pytest
from src.detectors import detect_ap04
from src.models import Confidence, Framework, Language, Severity


class TestAP04LargeTestSignal:
    """Tests for the large test signal (>= 30 meaningful statements)."""

    def test_python_29_statements_not_flagged(self):
        # Function with exactly 29 statements inside body
        statements = "\n".join([f"    page.click('#btn_{i}')" for i in range(29)])
        script = f"def test_twenty_nine(page):\n{statements}\n"

        findings = detect_ap04(script, Framework.PLAYWRIGHT, Language.PYTHON)
        large_findings = [f for f in findings if "meaningful statements" in f.reason]
        assert len(large_findings) == 0

    def test_python_30_statements_flagged(self):
        # Function with exactly 30 statements inside body
        statements = "\n".join([f"    page.click('#btn_{i}')" for i in range(30)])
        script = f"def test_thirty(page):\n{statements}\n"

        findings = detect_ap04(script, Framework.PLAYWRIGHT, Language.PYTHON)
        large_findings = [f for f in findings if "meaningful statements" in f.reason]
        assert len(large_findings) == 1
        f = large_findings[0]
        assert f.anti_pattern_id == "AP04"
        assert f.anti_pattern_name == "Poor Test Structure"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.MEDIUM
        assert f.line_start == 1
        assert f.line_end == 31
        assert "30 meaningful statements" in f.reason
        assert "threshold is 30" in f.reason
        assert "split into smaller" in f.reason

    def test_comments_blanks_imports_do_not_count_toward_threshold(self):
        # 28 statements + comments + blank lines + docstring + import -> 28 statements, not flagged
        statements = "\n".join([f"    page.click('#btn_{i}')" for i in range(28)])
        script = (
            "def test_with_noise(page):\n"
            '    """This is a docstring that spans\n'
            '    multiple lines.\n'
            '    """\n'
            "    # Line comment 1\n"
            "    # Line comment 2\n"
            "    \n"
            "    from utils import helper\n"
            "    \n"
            f"{statements}\n"
        )
        findings = detect_ap04(script, Framework.PLAYWRIGHT, Language.PYTHON)
        large_findings = [f for f in findings if "meaningful statements" in f.reason]
        assert len(large_findings) == 0

    def test_ast_statement_counting_vs_raw_lines(self):
        # 1 multiline statement (spanning 5 physical lines) + docstring + import + if with 2 nested statements
        # Total AST statements = 1 (multiline call) + 1 (if) + 2 (nested statements) = 4 statements
        # Even though there are ~15 source lines, AST count is 4 and not flagged.
        script = (
            "def test_ast_demo(page):\n"
            '    """Function docstring."""\n'
            "    import sys\n"
            "    page.click(\n"
            "        '#submit',\n"
            "        timeout=5000,\n"
            "        force=True,\n"
            "    )\n"
            "    if condition:\n"
            "        page.click('#a')\n"
            "        page.click('#b')\n"
        )
        findings = detect_ap04(script, Framework.PLAYWRIGHT, Language.PYTHON)
        large_findings = [f for f in findings if "meaningful statements" in f.reason]
        assert len(large_findings) == 0

    def test_js_30_statements_flagged(self):
        statements = "\n".join([f"    page.click('#btn_{i}');" for i in range(30)])
        script = f"it('should handle many steps', async () => {{\n{statements}\n}});\n"

        findings = detect_ap04(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        large_findings = [f for f in findings if "meaningful statements" in f.reason]
        assert len(large_findings) == 1
        assert large_findings[0].anti_pattern_id == "AP04"
        assert "30 meaningful statements" in large_findings[0].reason


class TestAP04ExcessiveNestingSignal:
    """Tests for the excessive nesting signal (depth >= 4)."""

    def test_python_nesting_depth_3_not_flagged(self):
        script = (
            "def test_depth_3():\n"
            "    if cond1:\n"             # depth 1
            "        for i in items:\n"    # depth 2
            "            while ready:\n"   # depth 3
            "                action()\n"
        )
        findings = detect_ap04(script, Framework.SELENIUM, Language.PYTHON)
        nesting_findings = [f for f in findings if "nesting depth" in f.reason]
        assert len(nesting_findings) == 0

    def test_python_nesting_depth_4_flagged(self):
        script = (
            "def test_depth_4():\n"
            "    if cond1:\n"             # depth 1
            "        for i in items:\n"    # depth 2
            "            while ready:\n"   # depth 3
            "                try:\n"       # depth 4
            "                    action()\n"
            "                except Exception:\n"
            "                    pass\n"
        )
        findings = detect_ap04(script, Framework.SELENIUM, Language.PYTHON)
        nesting_findings = [f for f in findings if "nesting depth" in f.reason]
        assert len(nesting_findings) == 1
        f = nesting_findings[0]
        assert f.anti_pattern_id == "AP04"
        assert f.anti_pattern_name == "Poor Test Structure"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.MEDIUM
        assert f.line_start == 1
        assert "nesting depth of 4" in f.reason
        assert "threshold is 4" in f.reason

    def test_js_nesting_depth_4_flagged(self):
        script = (
            "it('handles complex flow', () => {\n"
            "  if (a) {\n"                 # depth 1
            "    for (let x of list) {\n"  # depth 2
            "      while (flag) {\n"       # depth 3
            "        try {\n"              # depth 4
            "          doWork();\n"
            "        } catch (e) {}\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "});\n"
        )
        findings = detect_ap04(script, Framework.CYPRESS, Language.JAVASCRIPT)
        nesting_findings = [f for f in findings if "nesting depth" in f.reason]
        assert len(nesting_findings) == 1
        assert "nesting depth" in nesting_findings[0].reason


class TestAP04EdgeCases:
    """Tests for edge cases and isolation."""

    def test_empty_and_whitespace_scripts(self):
        assert detect_ap04("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap04("   \n\n   ", Framework.SELENIUM, Language.PYTHON) == []

    def test_clean_test_no_findings(self):
        script = (
            "def test_simple(page):\n"
            "    page.goto('https://example.com')\n"
            "    page.click('#submit')\n"
            "    assert page.title() == 'Home'\n"
        )
        findings = detect_ap04(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_multiple_tests_only_violating_one_flagged(self):
        short_test = (
            "def test_one(page):\n"
            "    page.click('#btn')\n"
        )
        long_statements = "\n".join([f"    page.click('#btn_{i}')" for i in range(30)])
        long_test = f"def test_two(page):\n{long_statements}\n"
        script = f"{short_test}\n{long_test}"

        findings = detect_ap04(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 4
        assert "test_two" in findings[0].reason

    def test_strings_with_braces_do_not_increase_nesting(self):
        script = (
            "it('checks json payload', () => {\n"
            '  const payload = "{ \"key\": { \"inner\": { \"deep\": { \"val\": 1 } } } }";\n'
            '  cy.request("/api", payload);\n'
            "});\n"
        )
        findings = detect_ap04(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_top_level_script_not_treated_as_test_function(self):
        # 35 top-level statements not in a def/test function
        statements = "\n".join([f"driver.get('https://example.com/{i}')" for i in range(35)])
        script = f"{statements}\n"

        findings = detect_ap04(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_unsupported_framework_language(self):
        script = "def test_foo():\n    pass\n"
        assert detect_ap04(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
        assert detect_ap04(script, Framework.CYPRESS, Language.PYTHON) == []
