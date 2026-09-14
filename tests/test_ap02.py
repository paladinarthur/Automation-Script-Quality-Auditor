"""
Unit tests for AP02 — Magic Numbers / Hardcoded Values Detector.

Verifies:
- Positive cases in Python, JavaScript, and TypeScript
- Exclusions: 0 and 1
- Exclusions: HTTP status codes (200, 404, etc.)
- Exclusions: Normal loop/index usage (range(5), for (let i = 0; i < 5; i++), items[2])
- Exclusions: Named constants (MAX_RETRIES = 7, DEFAULT_TIMEOUT = 30)
- Exclusions: AP01 hardcoded waits (time.sleep, wait_for_timeout, cy.wait)
- Exclusions: Ordinary test data (age = 25)
- Exclusions: Comments and docstrings
- Unsupported framework/language combinations
- Exact Finding metadata (AP02, Severity.MEDIUM, Confidence.MEDIUM, line numbers, snippet, reason)
- Multiple findings tracking
"""

import pytest
from src.detectors import detect_ap02
from src.models import Confidence, Framework, Language, Severity


class TestAP02PositiveCases:
    """Positive test cases where AP02 must be flagged."""

    def test_python_retries_assignment(self):
        script = "def run():\n    retries = 7\n"
        findings = detect_ap02(script, Framework.SELENIUM, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP02"
        assert f.anti_pattern_name == "Magic Numbers / Hardcoded Values"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.MEDIUM
        assert f.line_start == 2
        assert f.line_end == 2
        assert f.code_snippet == "retries = 7"
        assert "7" in f.reason
        assert f.explanation == ""
        assert f.suggested_fix == ""

    def test_python_retries_condition(self):
        script = "if retries > 7:\n    raise Exception('Too many retries')\n"
        findings = detect_ap02(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP02"
        assert f.line_start == 1
        assert f.code_snippet == "if retries > 7:"
        assert "7" in f.reason

    def test_python_timeout_assignment(self):
        script = "timeout = 37\n"
        findings = detect_ap02(script, Framework.SELENIUM, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP02"
        assert f.line_start == 1
        assert f.code_snippet == "timeout = 37"
        assert "37" in f.reason

    def test_python_response_time_condition(self):
        script = "if response_time > 3000:\n    logger.warning('Slow response')\n"
        findings = detect_ap02(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP02"
        assert f.line_start == 1
        assert f.code_snippet == "if response_time > 3000:"
        assert "3000" in f.reason

    def test_python_positional_locator(self):
        script = 'element = page.locator("div:nth-child(7)")\n'
        findings = detect_ap02(script, Framework.PLAYWRIGHT, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP02"
        assert f.line_start == 1
        assert f.code_snippet == 'element = page.locator("div:nth-child(7)")'
        assert "7" in f.reason

    def test_javascript_const_retries(self):
        script = "const retries = 7;\n"
        findings = detect_ap02(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP02"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.MEDIUM
        assert f.line_start == 1
        assert f.code_snippet == "const retries = 7;"
        assert "7" in f.reason

    def test_javascript_attempts_condition(self):
        script = "if (attempts > 7) {\n  throw new Error('Limit reached');\n}\n"
        findings = detect_ap02(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP02"
        assert f.line_start == 1
        assert f.code_snippet == "if (attempts > 7) {"

    def test_javascript_const_timeout(self):
        script = "const timeout = 37;\n"
        findings = detect_ap02(script, Framework.CYPRESS, Language.JAVASCRIPT)

        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP02"
        assert f.line_start == 1
        assert f.code_snippet == "const timeout = 37;"
        assert "37" in f.reason

    def test_typescript_typed_retries_and_timeout(self):
        script = "const retries: number = 7;\nconst timeout: number = 37;\n"
        findings = detect_ap02(script, Framework.PLAYWRIGHT, Language.TYPESCRIPT)

        assert len(findings) == 2
        assert findings[0].line_start == 1
        assert findings[0].code_snippet == "const retries: number = 7;"
        assert findings[1].line_start == 2
        assert findings[1].code_snippet == "const timeout: number = 37;"

    def test_typescript_attempts_condition(self):
        script = "if (attempts > 7) {\n  return false;\n}\n"
        findings = detect_ap02(script, Framework.CYPRESS, Language.TYPESCRIPT)

        assert len(findings) == 1
        assert findings[0].line_start == 1
        assert findings[0].code_snippet == "if (attempts > 7) {"


class TestAP02Exclusions:
    """Tests verifying all explicit exclusions are NOT flagged as AP02."""

    def test_zero_and_one_excluded(self):
        script = (
            "count = 0\n"
            "flag = 1\n"
            "if count == 0:\n"
            "    pass\n"
            "if flag == 1:\n"
            "    pass\n"
        )
        findings = detect_ap02(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_loop_range_excluded(self):
        script = (
            "for i in range(5):\n"
            "    print(i)\n"
        )
        findings = detect_ap02(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_javascript_for_loop_excluded(self):
        script = "for (let i = 0; i < 5; i++) {\n  console.log(i);\n}\n"
        findings = detect_ap02(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_array_indexing_excluded(self):
        script = (
            "first = items[0]\n"
            "third = items[2]\n"
        )
        findings = detect_ap02(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_http_status_codes_excluded(self):
        script_py = (
            "assert response.status_code == 200\n"
            "assert response.status_code == 404\n"
            "assert status == 500\n"
        )
        findings_py = detect_ap02(script_py, Framework.SELENIUM, Language.PYTHON)
        assert len(findings_py) == 0

        script_js = (
            "expect(response.status).toBe(200);\n"
            "if (res.status === 404) {}\n"
        )
        findings_js = detect_ap02(script_js, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings_js) == 0

    def test_ordinary_test_data_excluded(self):
        script = (
            "age = 25\n"
            "price = 99\n"
            "user_id = 'user_123'\n"
        )
        findings = detect_ap02(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_named_constants_excluded(self):
        script_py = (
            "MAX_RETRIES = 7\n"
            "DEFAULT_TIMEOUT = 30\n"
            "TIMEOUT_SECONDS = 60\n"
        )
        findings_py = detect_ap02(script_py, Framework.SELENIUM, Language.PYTHON)
        assert len(findings_py) == 0

        script_js = (
            "const MAX_RETRIES = 7;\n"
            "const DEFAULT_TIMEOUT = 30;\n"
            "export const TIMEOUT_MS = 5000;\n"
        )
        findings_js = detect_ap02(script_js, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings_js) == 0

    def test_ap01_waits_excluded(self):
        # AP01 waits belong strictly to AP01 and must NOT produce AP02 findings
        script_py = (
            "import time\n"
            "time.sleep(5)\n"
            "page.wait_for_timeout(5000)\n"
        )
        findings_py = detect_ap02(script_py, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings_py) == 0

        script_js = (
            "await page.waitForTimeout(5000);\n"
            "cy.wait(5000);\n"
        )
        findings_js = detect_ap02(script_js, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings_js) == 0

        findings_cy = detect_ap02(script_js, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings_cy) == 0

    def test_comments_and_docstrings_excluded(self):
        script_py = (
            "# retries = 7\n"
            "# timeout = 37\n"
            '"""\n'
            "timeout = 50\n"
            '"""\n'
            "def test_foo():\n"
            "    pass  # if retries > 7:\n"
        )
        findings_py = detect_ap02(script_py, Framework.SELENIUM, Language.PYTHON)
        assert len(findings_py) == 0

        script_js = (
            "// const retries = 7;\n"
            "/* if (attempts > 7) { } */\n"
            "const valid = true; // timeout = 37\n"
        )
        findings_js = detect_ap02(script_js, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings_js) == 0

    def test_unsupported_framework_language_combinations(self):
        script = "retries = 7\n"
        # Selenium + JavaScript is unsupported
        assert detect_ap02(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
        # Selenium + TypeScript is unsupported
        assert detect_ap02(script, Framework.SELENIUM, Language.TYPESCRIPT) == []
        # Cypress + Python is unsupported
        assert detect_ap02(script, Framework.CYPRESS, Language.PYTHON) == []

    def test_empty_and_whitespace_scripts(self):
        assert detect_ap02("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap02("   \n\t\n  ", Framework.SELENIUM, Language.PYTHON) == []


class TestAP02MultipleFindingsAndMetadata:
    """Verifies multiple findings on distinct lines and exact model contract."""

    def test_multiple_findings_exact_lines(self):
        script = (
            "# Start\n"                 # Line 1
            "retries = 7\n"             # Line 2
            "action()\n"                # Line 3
            "timeout = 37\n"            # Line 4
            "\n"                        # Line 5
            "if response_time > 3000:\n"  # Line 6
            "    pass\n"                # Line 7
        )
        findings = detect_ap02(script, Framework.SELENIUM, Language.PYTHON)

        assert len(findings) == 3
        assert findings[0].line_start == 2
        assert findings[0].line_end == 2
        assert findings[0].code_snippet == "retries = 7"
        assert findings[0].id == "AP02-L2"

        assert findings[1].line_start == 4
        assert findings[1].line_end == 4
        assert findings[1].code_snippet == "timeout = 37"
        assert findings[1].id == "AP02-L4"

        assert findings[2].line_start == 6
        assert findings[2].line_end == 6
        assert findings[2].code_snippet == "if response_time > 3000:"
        assert findings[2].id == "AP02-L6"

    def test_finding_contract_attributes(self):
        script = "timeout = 45\n"
        findings = detect_ap02(script, Framework.SELENIUM, Language.PYTHON)

        assert len(findings) == 1
        f = findings[0]
        assert f.id == "AP02-L1"
        assert f.anti_pattern_id == "AP02"
        assert f.anti_pattern_name == "Magic Numbers / Hardcoded Values"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.MEDIUM
        assert f.line_start == 1
        assert f.line_end == 1
        assert f.code_snippet == "timeout = 45"
        assert isinstance(f.reason, str) and len(f.reason.strip()) > 0
        assert f.explanation == ""
        assert f.suggested_fix == ""
