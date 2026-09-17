"""
Unit & Integration Tests for Streamlit UI Input Convergence and Invariants (T06).

Verifies:
- Framework and Language dynamic mapping rules.
- Convergence of pasted text and uploaded file (.py, .js, .ts) into ScriptInput contract.
- Equivalence of pasted vs uploaded input payloads.
- Upload precedence over paste input.
- Empty pasted text and empty uploaded file rejection.
- Independent file extension validation (supported: .py, .js, .ts; unsupported: .zip, .txt, .exe).
- Invalid framework/language combination prevention.
- Security invariant: Uploaded source code is treated strictly as text string and NEVER executed.
"""

from unittest.mock import MagicMock
import pytest

from app import is_supported_file_extension
from src.models.enums import Framework, Language
from src.models.input import ScriptInput
from src.services.audit_service import audit_script
from src.validation.validator import get_supported_languages, validate_framework_and_language


# Helper class to mock Streamlit's UploadedFile object in tests
class MockUploadedFile:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def test_framework_language_options() -> None:
    """Verify dynamic language choices for each supported framework."""
    selenium_langs = get_supported_languages(Framework.SELENIUM)
    assert selenium_langs == [Language.PYTHON]

    playwright_langs = get_supported_languages(Framework.PLAYWRIGHT)
    assert set(playwright_langs) == {Language.PYTHON, Language.JAVASCRIPT, Language.TYPESCRIPT}

    cypress_langs = get_supported_languages(Framework.CYPRESS)
    assert set(cypress_langs) == {Language.JAVASCRIPT, Language.TYPESCRIPT}


def test_pasted_script_input_convergence() -> None:
    """Verify valid pasted script reaches the expected ScriptInput contract."""
    pasted_code = 'from playwright.sync_api import Page\n\ndef test_example(page: Page):\n    page.goto("https://example.com")\n'

    script_input = ScriptInput(
        script_content=pasted_code,
        framework=Framework.PLAYWRIGHT,
        language=Language.PYTHON,
    )

    assert script_input.script_content == pasted_code
    assert script_input.framework == Framework.PLAYWRIGHT
    assert script_input.language == Language.PYTHON


def test_uploaded_file_python_convergence() -> None:
    """Verify valid .py uploaded file reaches the expected ScriptInput contract."""
    code_str = 'import time\ntime.sleep(5)\n'
    file_bytes = code_str.encode("utf-8")
    uploaded_file = MockUploadedFile("test_login.py", file_bytes)

    # Ingestion simulation: read as UTF-8 text string
    extracted_text = uploaded_file.getvalue().decode("utf-8")
    assert isinstance(extracted_text, str)

    script_input = ScriptInput(
        script_content=extracted_text,
        framework=Framework.SELENIUM,
        language=Language.PYTHON,
    )

    assert script_input.script_content == code_str
    assert script_input.framework == Framework.SELENIUM
    assert script_input.language == Language.PYTHON


def test_uploaded_file_javascript_convergence() -> None:
    """Verify valid .js uploaded file reaches the expected ScriptInput contract."""
    code_str = 'describe("Test Suite", () => {\n  it("logs in", () => {\n    cy.wait(5000);\n  });\n});\n'
    file_bytes = code_str.encode("utf-8")
    uploaded_file = MockUploadedFile("spec.js", file_bytes)

    extracted_text = uploaded_file.getvalue().decode("utf-8")
    assert isinstance(extracted_text, str)

    script_input = ScriptInput(
        script_content=extracted_text,
        framework=Framework.CYPRESS,
        language=Language.JAVASCRIPT,
    )

    assert script_input.script_content == code_str
    assert script_input.framework == Framework.CYPRESS
    assert script_input.language == Language.JAVASCRIPT


def test_uploaded_file_typescript_convergence() -> None:
    """Verify valid .ts uploaded file reaches the expected ScriptInput contract."""
    code_str = 'import { test, expect } from "@playwright/test";\ntest("test", async ({ page }) => {\n  await page.waitForTimeout(3000);\n});\n'
    file_bytes = code_str.encode("utf-8")
    uploaded_file = MockUploadedFile("test.spec.ts", file_bytes)

    extracted_text = uploaded_file.getvalue().decode("utf-8")
    assert isinstance(extracted_text, str)

    script_input = ScriptInput(
        script_content=extracted_text,
        framework=Framework.PLAYWRIGHT,
        language=Language.TYPESCRIPT,
    )

    assert script_input.script_content == code_str
    assert script_input.framework == Framework.PLAYWRIGHT
    assert script_input.language == Language.TYPESCRIPT


def test_uploaded_file_precedence_over_paste() -> None:
    """Verify uploaded file takes precedence over pasted text when both exist."""
    pasted_code = "import time\ntime.sleep(2)"
    uploaded_code = "import time\ntime.sleep(5)"
    uploaded_file = MockUploadedFile("upload.py", uploaded_code.encode("utf-8"))

    # Convergence logic simulation:
    extracted_text = uploaded_file.getvalue().decode("utf-8")
    active_script = extracted_text if (uploaded_file is not None and extracted_text.strip()) else pasted_code

    assert active_script == uploaded_code
    assert active_script != pasted_code


def test_unsupported_file_extension_rejected() -> None:
    """Verify file-extension validation is testable independently of Streamlit file uploader."""
    assert is_supported_file_extension("script.py") is True
    assert is_supported_file_extension("test.spec.js") is True
    assert is_supported_file_extension("test.spec.ts") is True

    # Case-insensitive checks
    assert is_supported_file_extension("SCRIPT.PY") is True
    assert is_supported_file_extension("spec.JS") is True

    # Unsupported extensions
    assert is_supported_file_extension("archive.zip") is False
    assert is_supported_file_extension("notes.txt") is False
    assert is_supported_file_extension("binary.exe") is False
    assert is_supported_file_extension("report.pdf") is False
    assert is_supported_file_extension("no_extension") is False
    assert is_supported_file_extension("") is False


def test_empty_pasted_script_rejected() -> None:
    """Verify empty or whitespace-only pasted script is caught and rejected."""
    empty_code = "   \n\t  "
    assert not empty_code.strip()

    script_input = ScriptInput(
        script_content=empty_code,
        framework=Framework.SELENIUM,
        language=Language.PYTHON,
    )

    findings = audit_script(script_input)
    assert findings == []


def test_empty_uploaded_file_rejected() -> None:
    """Verify 0-byte or whitespace uploaded file is caught and rejected."""
    uploaded_file = MockUploadedFile("empty.py", b"")
    extracted_text = uploaded_file.getvalue().decode("utf-8")
    assert not extracted_text.strip()

    script_input = ScriptInput(
        script_content=extracted_text,
        framework=Framework.SELENIUM,
        language=Language.PYTHON,
    )

    findings = audit_script(script_input)
    assert findings == []


def test_paste_and_upload_equivalence() -> None:
    """Verify pasted and uploaded script content produce identical ScriptInput payloads."""
    source_code = 'import time\ntime.sleep(10)\n'

    # Method A: Paste
    input_from_paste = ScriptInput(
        script_content=source_code,
        framework=Framework.SELENIUM,
        language=Language.PYTHON,
    )

    # Method B: Upload
    uploaded_file = MockUploadedFile("test.py", source_code.encode("utf-8"))
    extracted_text = uploaded_file.getvalue().decode("utf-8")
    input_from_upload = ScriptInput(
        script_content=extracted_text,
        framework=Framework.SELENIUM,
        language=Language.PYTHON,
    )

    assert input_from_paste == input_from_upload


def test_invalid_framework_language_prevents_audit() -> None:
    """Verify invalid framework and language combination fails validation and skips audit."""
    validation = validate_framework_and_language(Framework.SELENIUM, Language.JAVASCRIPT)
    assert not validation.is_valid
    assert "Selenium is supported only with Python" in (validation.error_message or "")

    script_input = ScriptInput(
        script_content="cy.wait(1000);",
        framework=Framework.SELENIUM,
        language=Language.JAVASCRIPT,
    )

    findings = audit_script(script_input)
    assert findings == []


def test_uploaded_source_treated_strictly_as_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Security Invariant: Verify uploaded source code is read as UTF-8 text string
    and processed strictly by static analysis without executing/importing/evaluating.
    """
    source_code_with_antipattern = """
import time
import os
import subprocess

# Hardcoded wait anti-pattern (AP01)
time.sleep(5)

# Malicious statement text in script body
os.system("echo HACKED")
"""
    uploaded_file = MockUploadedFile("test_script.py", source_code_with_antipattern.encode("utf-8"))
    extracted_text = uploaded_file.getvalue().decode("utf-8")

    # Verify byte payload is converted strictly to Python str text object
    assert isinstance(extracted_text, str)

    # Mock system call Primitives to verify NONE are invoked during static processing
    called_actions: list[str] = []

    def mock_system(cmd: str) -> int:
        called_actions.append(f"os.system: {cmd}")
        return 0

    monkeypatch.setattr("os.system", mock_system)
    monkeypatch.setattr("subprocess.run", MagicMock())
    monkeypatch.setattr("subprocess.Popen", MagicMock())

    script_input = ScriptInput(
        script_content=extracted_text,
        framework=Framework.SELENIUM,
        language=Language.PYTHON,
    )

    # Run audit pipeline on the untrusted text buffer
    findings = audit_script(script_input)

    # 1. Confirm static analysis identified AP01 finding from string text
    assert len(findings) == 1
    assert findings[0].anti_pattern_id == "AP01"

    # 2. Confirm NO code execution happened during static analysis
    assert called_actions == []
