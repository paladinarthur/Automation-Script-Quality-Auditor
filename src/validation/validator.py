"""
Framework & Language Validation Module.

Provides deterministic validation to verify whether a given automation framework
and programming language combination is supported by the auditor.
"""

from dataclasses import dataclass
from src.models.enums import Framework, Language

# Single source of truth for supported framework and language combinations
SUPPORTED_COMBINATIONS: dict[Framework, set[Language]] = {
    Framework.SELENIUM: {Language.PYTHON},
    Framework.PLAYWRIGHT: {Language.PYTHON, Language.JAVASCRIPT, Language.TYPESCRIPT},
    Framework.CYPRESS: {Language.JAVASCRIPT, Language.TYPESCRIPT},
}


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of framework and language compatibility validation.
    """

    is_valid: bool
    error_message: str | None = None

    def __bool__(self) -> bool:
        return self.is_valid


def _parse_framework(framework: Framework | str) -> Framework | None:
    """Safely converts string or enum to Framework enum, or returns None."""
    if isinstance(framework, Framework):
        return framework
    if isinstance(framework, str):
        normalized = framework.strip().lower()
        for member in Framework:
            if member.value == normalized or member.name.lower() == normalized:
                return member
    return None


def _parse_language(language: Language | str) -> Language | None:
    """Safely converts string or enum to Language enum, or returns None."""
    if isinstance(language, Language):
        return language
    if isinstance(language, str):
        normalized = language.strip().lower()
        for member in Language:
            if member.value == normalized or member.name.lower() == normalized:
                return member
    return None


def _format_language_name(language: Language) -> str:
    """Formats Language enum to proper capitalization."""
    if language == Language.JAVASCRIPT:
        return "JavaScript"
    if language == Language.TYPESCRIPT:
        return "TypeScript"
    return "Python"


def get_supported_languages(framework: Framework | str) -> list[Language]:
    """
    Returns the list of supported languages for the specified framework.
    Returns an empty list if the framework is unknown.
    """
    parsed_framework = _parse_framework(framework)
    if not parsed_framework:
        return []
    return sorted(
        SUPPORTED_COMBINATIONS.get(parsed_framework, set()),
        key=lambda lang: lang.value,
    )


def validate_framework_and_language(
    framework: Framework | str,
    language: Language | str,
) -> ValidationResult:
    """
    Validates whether the selected framework and language combination is supported.

    Supported Combinations:
    - Selenium: Python
    - Playwright: Python, JavaScript, TypeScript
    - Cypress: JavaScript, TypeScript

    Returns:
        ValidationResult with is_valid=True if supported,
        or is_valid=False with a descriptive error message.
    """
    parsed_framework = _parse_framework(framework)
    if parsed_framework is None:
        valid_frameworks = ", ".join(f.value.capitalize() for f in Framework)
        return ValidationResult(
            is_valid=False,
            error_message=f"Unsupported framework '{framework}'. Supported frameworks are: {valid_frameworks}.",
        )

    parsed_language = _parse_language(language)
    if parsed_language is None:
        valid_languages = ", ".join(_format_language_name(lang) for lang in Language)
        return ValidationResult(
            is_valid=False,
            error_message=f"Unsupported language '{language}'. Supported languages are: {valid_languages}.",
        )

    supported_languages = SUPPORTED_COMBINATIONS.get(parsed_framework, set())
    if parsed_language in supported_languages:
        return ValidationResult(is_valid=True)

    # Format human-friendly error messages
    fw_name = parsed_framework.value.capitalize()
    # Sort order: JavaScript, TypeScript, Python (or natural display order)
    display_order = [Language.JAVASCRIPT, Language.TYPESCRIPT, Language.PYTHON]
    sorted_langs = [l for l in display_order if l in supported_languages]
    lang_names = [_format_language_name(lang) for lang in sorted_langs]

    if len(lang_names) == 1:
        lang_str = lang_names[0]
    elif len(lang_names) == 2:
        lang_str = f"{lang_names[0]} and {lang_names[1]}"
    else:
        lang_str = f"{', '.join(lang_names[:-1])}, and {lang_names[-1]}"

    return ValidationResult(
        is_valid=False,
        error_message=f"{fw_name} is supported only with {lang_str}.",
    )
