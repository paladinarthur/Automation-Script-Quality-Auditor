"""
Unit tests for AP09 — Hardcoded Secrets Detector.

Verifies:
1. Python password assignment -> flagged (Severity.HIGH, Confidence.HIGH).
2. Python API key assignment -> flagged.
3. Python access token assignment -> flagged.
4. JavaScript password assignment -> flagged.
5. TypeScript clientSecret assignment -> flagged.
6. Cypress secret/token assignment -> flagged.
7. JWT-like token with suspicious name -> flagged.
8. Private-key material -> flagged.
9. Environment variable retrieval -> NOT flagged.
10. process.env retrieval -> NOT flagged.
11. Configuration reference -> NOT flagged.
12. Obvious placeholder/dummy credential -> NOT flagged.
13. Ordinary test data -> NOT flagged.
14. Comment/docstring mentioning password/API key -> NOT flagged.
15. Actual secret value must NOT appear in the returned Finding.
16. Finding code_snippet contains [REDACTED].
17. Correct line references and metadata.
18. Empty/clean input -> no findings.
19. Unsupported framework/language -> no findings.
20. Multiple secrets -> multiple appropriate findings.
"""

import pytest
from src.detectors import detect_ap09
from src.models import Confidence, Framework, Language, Severity


class TestAP09Python:
    """Tests for Python (Selenium, Playwright)."""

    def test_python_password_assignment_flagged(self):
        secret_val = "SuperSecretP@ssw0rd!2026"
        script = (
            'def test_login(driver):\n'
            f'    password = "{secret_val}"\n'
            '    driver.get("https://example.com/login")\n'
            '    driver.find_element("id", "pwd").send_keys(password)\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        f = findings[0]
        assert f.anti_pattern_id == "AP09"
        assert f.anti_pattern_name == "Hardcoded Secrets"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 2
        assert f.line_end == 2
        assert "password" in f.reason.lower()
        # Security: actual secret value must NEVER appear in the finding
        assert secret_val not in f.code_snippet
        assert secret_val not in f.reason
        assert secret_val not in f.explanation
        assert secret_val not in f.suggested_fix
        assert "[REDACTED]" in f.code_snippet

    def test_python_api_key_assignment_flagged(self):
        secret_key = "prod_api_key_value_abc123456789"
        script = (
            'def test_api_client():\n'
            f'    API_KEY = "{secret_key}"\n'
            '    client = Client(api_key=API_KEY)\n'
        )
        findings = detect_ap09(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 2
        assert secret_key not in findings[0].code_snippet
        assert "[REDACTED]" in findings[0].code_snippet

    def test_python_access_token_assignment_flagged(self):
        secret_token = "auth_access_token_val_1234567890"
        script = (
            'def test_auth_header():\n'
            f'    access_token = "{secret_token}"\n'
            '    headers = {"Authorization": f"Bearer {access_token}"}\n'
        )
        findings = detect_ap09(script, Framework.PLAYWRIGHT, Language.PYTHON)
        assert len(findings) == 1
        assert secret_token not in findings[0].code_snippet
        assert "[REDACTED]" in findings[0].code_snippet

    def test_python_private_key_flagged(self):
        script = (
            'def test_crypto():\n'
            '    private_key = "-----BEGIN RSA PRIVATE KEY-----\\nMIIEowIBAAKCAQEA0..."\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        assert findings[0].line_start == 2
        assert "private key" in findings[0].reason.lower()
        assert "[REDACTED]" in findings[0].code_snippet


class TestAP09JavaScriptTypeScript:
    """Tests for JavaScript and TypeScript (Playwright, Cypress)."""

    def test_js_password_assignment_flagged(self):
        secret_val = "MyProdSecretPassword#999"
        script = (
            'test("user login", async ({ page }) => {\n'
            f'    const password = "{secret_val}";\n'
            '    await page.goto("/login");\n'
            '    await page.fill("#password", password);\n'
            '});\n'
        )
        findings = detect_ap09(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        f = findings[0]
        assert f.line_start == 2
        assert secret_val not in f.code_snippet
        assert "[REDACTED]" in f.code_snippet

    def test_ts_client_secret_assignment_flagged(self):
        secret_val = "client_secret_val_998877665544"
        script = (
            'test("oauth flow", async () => {\n'
            f'    const clientSecret: string = "{secret_val}";\n'
            '    const token = await fetchToken(clientSecret);\n'
            '});\n'
        )
        findings = detect_ap09(script, Framework.PLAYWRIGHT, Language.TYPESCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 2
        assert secret_val not in findings[0].code_snippet
        assert "[REDACTED]" in findings[0].code_snippet

    def test_cypress_secret_token_flagged(self):
        secret_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        script = (
            'it("authenticates via token", () => {\n'
            f'    const authToken = "{secret_token}";\n'
            '    cy.setCookie("token", authToken);\n'
            '    cy.visit("/dashboard");\n'
            '});\n'
        )
        findings = detect_ap09(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 2
        assert secret_token not in findings[0].code_snippet
        assert "[REDACTED]" in findings[0].code_snippet


class TestAP09Exclusions:
    """Tests for legitimate configuration and placeholder exclusions."""

    def test_os_getenv_not_flagged(self):
        script = (
            'import os\n'
            'def test_login(driver):\n'
            '    password = os.getenv("TEST_PASSWORD")\n'
            '    api_key = os.environ.get("API_KEY")\n'
            '    driver.get("https://example.com")\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_process_env_not_flagged(self):
        script = (
            'test("login via env", async ({ page }) => {\n'
            '    const password = process.env.USER_PASSWORD;\n'
            '    const apiKey = process.env.API_KEY;\n'
            '    await page.goto("/login");\n'
            '});\n'
        )
        findings = detect_ap09(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_cypress_env_not_flagged(self):
        script = (
            'it("loads credentials", () => {\n'
            '    const password = Cypress.env("ADMIN_PASSWORD");\n'
            '    const authToken = Cypress.env("AUTH_TOKEN");\n'
            '    cy.visit("/login");\n'
            '});\n'
        )
        findings = detect_ap09(script, Framework.CYPRESS, Language.JAVASCRIPT)
        assert len(findings) == 0

    def test_config_lookup_not_flagged(self):
        script = (
            'def test_config_usage():\n'
            '    password = config["password"]\n'
            '    api_key = settings.password\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_placeholder_dummy_values_not_flagged(self):
        script = (
            'def test_with_placeholders():\n'
            '    password = "password"\n'
            '    api_key = "YOUR_API_KEY"\n'
            '    secret = "<SECRET_KEY>"\n'
            '    token = "dummy-token"\n'
            '    pwd = "test"\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_ordinary_test_data_not_flagged(self):
        script = (
            'def test_registration(driver):\n'
            '    username = "john_doe"\n'
            '    email = "john@example.com"\n'
            '    url = "https://example.com/api"\n'
            '    headers = {"Content-Type": "application/json"}\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0

    def test_comments_and_docstrings_not_flagged(self):
        script = (
            '"""\n'
            'This test tests the password reset endpoint.\n'
            'API_KEY: abc1234567890abcdef\n'
            '"""\n'
            'def test_reset():\n'
            '    # Enter password = "MySecretPassword123"\n'
            '    driver.get("https://example.com")\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 0


class TestAP09SecurityAndRedaction:
    """Security verification tests ensuring zero secret leakage."""

    def test_security_leak_prevention(self):
        very_sensitive_secret = "UltraConfidentialSecretKey998877"
        script = f'const apiKey = "{very_sensitive_secret}";\n'
        findings = detect_ap09(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)

        assert len(findings) == 1
        f = findings[0]
        # Strict security assertion: original string must not appear anywhere in finding dataclass fields
        finding_dict = vars(f)
        for k, v in finding_dict.items():
            assert very_sensitive_secret not in str(v), f"Secret leaked in field '{k}'"
        assert "[REDACTED]" in f.code_snippet

    def test_multiple_secrets_flagged_and_redacted(self):
        sec1 = "SuperSecretPass1"
        sec2 = "sec_api_val_9876543210"
        script = (
            'def test_multi_secrets():\n'
            f'    password = "{sec1}"\n'
            f'    api_key = "{sec2}"\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 2
        assert findings[0].line_start == 2
        assert findings[1].line_start == 3
        assert sec1 not in findings[0].code_snippet
        assert sec2 not in findings[1].code_snippet
        assert "[REDACTED]" in findings[0].code_snippet
        assert "[REDACTED]" in findings[1].code_snippet

    def test_jwt_like_token_with_suspicious_name(self):
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgN_p_error_signature_example12345"
        script = f'const jwtToken = "{jwt_token}";\n'
        findings = detect_ap09(script, Framework.PLAYWRIGHT, Language.JAVASCRIPT)
        assert len(findings) == 1
        assert findings[0].line_start == 1
        assert jwt_token not in findings[0].code_snippet
        assert "[REDACTED]" in findings[0].code_snippet

    def test_finding_line_references_and_metadata(self):
        script = (
            '\n'
            '# Setup step\n'
            'password = "RealSecretPassword456"\n'
        )
        findings = detect_ap09(script, Framework.SELENIUM, Language.PYTHON)
        assert len(findings) == 1
        f = findings[0]
        assert f.id == "AP09-L3"
        assert f.anti_pattern_id == "AP09"
        assert f.anti_pattern_name == "Hardcoded Secrets"
        assert f.severity == Severity.HIGH
        assert f.confidence == Confidence.HIGH
        assert f.line_start == 3
        assert f.line_end == 3
        assert f.explanation == ""
        assert f.suggested_fix == ""
        assert "RealSecretPassword456" not in f.code_snippet
        assert "[REDACTED]" in f.code_snippet

    def test_empty_and_clean_script(self):
        assert detect_ap09("", Framework.SELENIUM, Language.PYTHON) == []
        assert detect_ap09("   \n\n  ", Framework.PLAYWRIGHT, Language.JAVASCRIPT) == []

    def test_unsupported_framework_or_language(self):
        script = 'password = "SuperSecret123"\n'
        assert detect_ap09(script, "unknown_fw", Language.PYTHON) == []
        assert detect_ap09(script, Framework.SELENIUM, Language.JAVASCRIPT) == []
