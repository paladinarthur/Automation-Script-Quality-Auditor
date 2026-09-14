"""
Unit tests for AP10 — Potentially Flaky Patterns Detector.

Verifies:
1. R1: Unsynchronized interaction after navigation (Selenium Python positive vs synchronized negative).
2. R2: Uncontrolled randomness (Python & JS/TS positive vs isolated random data negative).
3. R3: Test-order dependency (Python & JS/TS positive vs fixture/setup negative).
4. R4: Manual retry loop (Python & JS/TS positive vs normal data loop & framework retry config negative).
5. R5: Manual timestamp-based polling (Python & JS/TS multiline positive vs AP01 fixed delay exclusion).
6. Comments & docstrings exclusion.
7. Correct metadata (Severity.MEDIUM, Confidence.LOW/MEDIUM, AP10).
8. Empty/clean input & unsupported framework/language handling.
"""

import pytest
from src.detectors import detect_ap10
from src.models import Confidence, Framework, Language, Severity


class TestAP10R1UnsynchronizedNavigation:
    """Tests for R1: Unsynchronized interaction after navigation."""

    def test_selenium_unsynchronized_navigation_flagged(self):
        script = (
            'def test_search(driver):\n'
            '    driver.get("https://example.com")\n'
            '    driver.find_element("id", "btn").click()\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP10"
        assert f.anti_pattern_name == "Potentially Flaky Patterns"
        assert f.severity == Severity.MEDIUM
        assert f.confidence == Confidence.LOW
        assert f.line_start == 3
        assert "unsynchronized" in f.reason.lower()

    def test_selenium_synchronized_navigation_not_flagged(self):
        script = (
            'def test_search(driver):\n'
            '    driver.get("https://example.com")\n'
            '    WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.ID, "btn")))\n'
            '    driver.find_element("id", "btn").click()\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestAP10R2UncontrolledRandomness:
    """Tests for R2: Uncontrolled randomness."""

    def test_python_random_assertion_flagged(self):
        script = (
            'import random\n'
            'def test_random_expect():\n'
            '    val = random.randint(1, 100)\n'
            '    assert result == random.choice(["A", "B", "C"])\n'
        )
        findings = detect_ap10(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 4
        assert "random" in findings[0].reason.lower()

    def test_python_random_branching_flagged(self):
        script = (
            'import random\n'
            'def test_flow(page):\n'
            '    if random.random() > 0.5:\n'
            '        page.click("#btnA")\n'
            '    else:\n'
            '        page.click("#btnB")\n'
        )
        findings = detect_ap10(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 3

    def test_js_random_expect_flagged(self):
        script = (
            'test("random verification", async ({ page }) => {\n'
            '    const val = getVal();\n'
            '    expect(val).toBe(Math.random());\n'
            '});\n'
        )
        findings = detect_ap10(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 3

    def test_isolated_random_test_data_not_flagged(self):
        script = (
            'import uuid\n'
            'def test_create_user(page):\n'
            '    username = f"user_{uuid.uuid4()}"\n'
            '    page.goto("/register")\n'
            '    page.fill("#username", username)\n'
        )
        findings = detect_ap10(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0


class TestAP10R3TestOrderDependency:
    """Tests for R3: Test-order dependency."""

    def test_python_shared_mutable_state_flagged(self):
        script = (
            'created_id = None\n'
            '\n'
            'def test_create_entity():\n'
            '    global created_id\n'
            '    created_id = 12345\n'
            '\n'
            'def test_use_entity():\n'
            '    assert created_id is not None\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        assert "created_id" in findings[0].reason
        assert "test-order" in findings[0].reason.lower()

    def test_js_shared_mutable_state_flagged(self):
        script = (
            'let sharedUserId;\n'
            '\n'
            'it("creates user", () => {\n'
            '    sharedUserId = 99;\n'
            '});\n'
            '\n'
            'it("deletes user", () => {\n'
            '    expect(sharedUserId).toBeDefined();\n'
            '});\n'
        )
        findings = detect_ap10(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert "sharedUserId" in findings[0].reason

    def test_fixture_and_setup_not_flagged(self):
        script = (
            'import pytest\n'
            '@pytest.fixture\n'
            'def sample_user():\n'
            '    return {"name": "Alice"}\n'
            '\n'
            'def test_one(sample_user):\n'
            '    assert sample_user["name"] == "Alice"\n'
            '\n'
            'def test_two(sample_user):\n'
            '    assert sample_user["name"] == "Alice"\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestAP10R4ManualRetryLoops:
    """Tests for R4: Manual retry loops."""

    def test_python_manual_retry_loop_flagged(self):
        script = (
            'def test_click_with_retry(driver):\n'
            '    for attempt in range(3):\n'
            '        try:\n'
            '            driver.find_element("id", "btn").click()\n'
            '            break\n'
            '        except Exception:\n'
            '            pass\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 2
        assert "retry loop" in findings[0].reason.lower()

    def test_js_manual_retry_loop_flagged(self):
        script = (
            'test("retry click", async ({ page }) => {\n'
            '    for (let attempt = 0; attempt < 3; attempt++) {\n'
            '        try {\n'
            '            await page.click("#btn");\n'
            '            break;\n'
            '        } catch (e) {}\n'
            '    }\n'
            '});\n'
        )
        findings = detect_ap10(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 2

    def test_normal_data_loop_not_flagged(self):
        script = (
            'def test_batch_fill(page):\n'
            '    users = ["Alice", "Bob", "Charlie"]\n'
            '    for user in users:\n'
            '        page.fill("#name", user)\n'
        )
        findings = detect_ap10(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 0

    def test_framework_retry_config_not_flagged(self):
        script = (
            'import pytest\n'
            '@pytest.mark.flaky(reruns=3)\n'
            'def test_resilient():\n'
            '    assert True\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestAP10R5TimestampPolling:
    """Tests for R5: Manual timestamp-based polling."""

    def test_python_timestamp_polling_flagged(self):
        script = (
            'import time\n'
            'def test_poll_status(driver):\n'
            '    start = time.time()\n'
            '    while time.time() - start < 10:\n'
            '        if "Done" in driver.page_source:\n'
            '            break\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 4
        assert "timestamp-based polling" in findings[0].reason.lower()

    def test_js_multiline_timestamp_polling_flagged(self):
        script = (
            'test("wait for state", async ({ page }) => {\n'
            '    const startTime = Date.now();\n'
            '    while (\n'
            '        Date.now() - startTime < 5000\n'
            '    ) {\n'
            '        if (await page.isVisible("#done")) break;\n'
            '    }\n'
            '});\n'
        )
        findings = detect_ap10(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 3

    def test_ap01_fixed_delay_not_flagged_as_ap10(self):
        # Fixed sleeps must be AP01 only, not AP10
        script = (
            'import time\n'
            'def test_fixed_sleep(driver):\n'
            '    driver.get("https://example.com")\n'
            '    time.sleep(5)\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestAP10MetadataAndExclusions:
    """Tests for exclusions and metadata structure."""

    def test_comments_and_docstrings_not_flagged(self):
        script = (
            '"""\n'
            'while time.time() - start < 10:\n'
            '    driver.click()\n'
            '"""\n'
            'def test_clean():\n'
            '    # for attempt in range(3):\n'
            '    pass\n'
        )
        findings = detect_ap10(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_empty_and_clean_script(self):
        assert detect_ap10("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap10("   \n\n  ", Framework.PLAYWRIGHT, Language.JAVASCRIPT) == []

    def test_unsupported_framework_or_language(self):
        script = 'while time.time() - start < 10: pass\n'
        assert detect_ap10(script, "unknown_fw", Language.PYTHON) == []
        assert detect_ap10(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
