"""
Unit tests for framework and language validation (Build Step 3).
Verifies supported matrix, unsupported combinations, error messaging, and edge cases.
"""

import pytest
from src.models import Framework, Language
from src.validation import (
    SUPPORTED_COMBINATIONS,
    ValidationResult,
    get_supported_languages,
    validate_framework_and_language,
)


class TestSupportedCombinations:
    """Tests covering all officially supported framework and language pairs."""

    @pytest.mark.parametrize(
        "framework,language",
        [
            (Framework.SELENIUM, Language.PYTHON),
            (Framework.PLAYWRIGHT, Language.PYTHON),
            (Framework.PLAYWRIGHT, Language.JAVASCRIPT),
            (Framework.PLAYWRIGHT, Language.TYPESCRIPT),
            (Framework.CYPRESS, Language.JAVASCRIPT),
            (Framework.CYPRESS, Language.TYPESCRIPT),
        ],
    )
    def test_all_supported_enum_combinations(self, framework, language):
        result = validate_framework_and_language(framework, language)
        assert result.is_valid is True
        assert bool(result) is True
        assert result.error_message is None

    @pytest.mark.parametrize(
        "framework_str,language_str",
        [
            ("selenium", "python"),
            ("playwright", "python"),
            ("playwright", "javascript"),
            ("playwright", "typescript"),
            ("cypress", "javascript"),
            ("cypress", "typescript"),
        ],
    )
    def test_all_supported_string_combinations(self, framework_str, language_str):
        result = validate_framework_and_language(framework_str, language_str)
        assert result.is_valid is True
        assert bool(result) is True
        assert result.error_message is None

    def test_case_insensitive_string_inputs(self):
        result = validate_framework_and_language("SELENIUM", "Python")
        assert result.is_valid is True
        result_ts = validate_framework_and_language("Playwright", "TYPESCRIPT")
        assert result_ts.is_valid is True


class TestUnsupportedCombinations:
    """Tests covering unsupported framework/language combinations and expected messages."""

    def test_selenium_with_javascript(self):
        result = validate_framework_and_language(Framework.SELENIUM, Language.JAVASCRIPT)
        assert result.is_valid is False
        assert bool(result) is False
        assert result.error_message == "Selenium is supported only with Python."

    def test_selenium_with_typescript(self):
        result = validate_framework_and_language(Framework.SELENIUM, Language.TYPESCRIPT)
        assert result.is_valid is False
        assert bool(result) is False
        assert result.error_message == "Selenium is supported only with Python."

    def test_cypress_with_python(self):
        result = validate_framework_and_language(Framework.CYPRESS, Language.PYTHON)
        assert result.is_valid is False
        assert bool(result) is False
        assert result.error_message == "Cypress is supported only with JavaScript and TypeScript."


class TestInvalidInputs:
    """Tests covering invalid or unknown frameworks and languages."""

    def test_unknown_framework(self):
        result = validate_framework_and_language("robot_framework", "python")
        assert result.is_valid is False
        assert "Unsupported framework 'robot_framework'" in result.error_message

    def test_unknown_language(self):
        result = validate_framework_and_language("selenium", "ruby")
        assert result.is_valid is False
        assert "Unsupported language 'ruby'" in result.error_message

    def test_empty_strings(self):
        result_fw = validate_framework_and_language("", "python")
        assert result_fw.is_valid is False

        result_lang = validate_framework_and_language("selenium", "")
        assert result_lang.is_valid is False


class TestGetSupportedLanguagesHelper:
    """Tests covering the get_supported_languages lookup helper."""

    def test_selenium_supported_languages(self):
        langs = get_supported_languages(Framework.SELENIUM)
        assert langs == [Language.PYTHON]

    def test_playwright_supported_languages(self):
        langs = get_supported_languages(Framework.PLAYWRIGHT)
        assert set(langs) == {Language.PYTHON, Language.JAVASCRIPT, Language.TYPESCRIPT}

    def test_cypress_supported_languages(self):
        langs = get_supported_languages(Framework.CYPRESS)
        assert set(langs) == {Language.JAVASCRIPT, Language.TYPESCRIPT}

    def test_unknown_framework_lookup(self):
        assert get_supported_languages("unknown_fw") == []
