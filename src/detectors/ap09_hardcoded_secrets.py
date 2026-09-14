"""
AP09 — Hardcoded Secrets Detector.

Performs static analysis to detect embedded credentials and secrets in automation scripts
across Selenium (Python), Playwright (Python, JS, TS), and Cypress (JS, TS).

Critical Security Requirement:
The actual secret value is NEVER stored in the Finding object (code_snippet, reason,
explanation, suggested_fix, etc.). The code_snippet is deterministically redacted
replacing secret literals with '[REDACTED]'.

Approved Signals:
1. Suspicious secret/credential variable names (password, api_key, secret, access_token, etc.)
   assigned literal string values.
2. Recognizable secret/token formats (JWT tokens, Private Keys, Bearer tokens).

Exclusions:
- Environment variable retrieval (os.getenv, os.environ, process.env, Cypress.env)
- Configuration lookups (config["..."], settings.password)
- Obvious placeholder/test values ("password", "<PASSWORD>", "YOUR_API_KEY", "dummy-token")
- Comments / docstrings
- Ordinary usernames and test data
"""

import re
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

# Suspicious credential variable name patterns (snake_case, camelCase, PascalCase, UPPER_CASE)
_SECRET_VAR_NAME_PATTERN = re.compile(
    r"^(?:.*_)?(?:password|passwd|pwd|api_?key|api_?secret|client_?secret|access_?token|"
    r"refresh_?token|auth_?token|bearer_?token|private_?key|secret_?key|secret|jwt_?token|"
    r"session_?token)(?:_.*)?$",
    re.IGNORECASE,
)

# Suffixes that indicate a UI element/locator rather than credential value
_LOCATOR_VAR_SUFFIXES = (
    "field",
    "input",
    "locator",
    "selector",
    "element",
    "button",
    "btn",
    "box",
    "by",
    "label",
    "text",
    "xpath",
    "id",
    "class",
)

# Recognizable standalone secret formats
_JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
)
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN\s+(?:[A-Z0-9_-]+\s+)?PRIVATE\s+KEY-----"
)
_BEARER_TOKEN_PATTERN = re.compile(
    r"\bBearer\s+([a-zA-Z0-9_\-\.]{25,})\b",
    re.IGNORECASE,
)

# Common env/config access patterns that indicate externalized configuration (DO NOT FLAG)
_ENV_OR_CONFIG_PATTERNS = re.compile(
    r"\b(?:os\.getenv|os\.environ|process\.env|Cypress\.env|System\.getenv|config\s*\[|config\.get|settings\.)",
    re.IGNORECASE,
)

# Excluded placeholder and dummy values that are not real secrets
_EXCLUDED_PLACEHOLDERS = {
    "",
    "password",
    "pass",
    "pwd",
    "test",
    "example",
    "admin",
    "user",
    "dummy",
    "dummy-token",
    "dummy_token",
    "fake-token",
    "fake_token",
    "fake",
    "placeholder",
    "changeme",
    "change_me",
    "replace_me",
    "todo",
    "sample",
    "demo",
    "none",
    "null",
    "undefined",
    "123456",
    "12345678",
    "test123",
    "password123",
    "secret",
    "mysecret",
    "my_secret",
    "your_api_key",
    "your_password",
    "your_token",
    "your_secret",
    "api_key",
    "apikey",
    "token",
    "your-api-key",
    "your-token",
    "your_key",
    "your-key",
    "xxx",
    "xxxx",
    "xxxxx",
    "******",
}

# Regex to detect variable assignments with string literals:
# Covers:
# - const apiKey: string = "..." / let password = "..." / var secret = "..."
# - password = "..."
# - apiKey: "..." / "apiKey": "..."
# - password="...", api_key="..."
_ASSIGNMENT_PATTERN = re.compile(
    r"""(?:(?:const|let|var)\s+)?['"]?([a-zA-Z0-9_$]+)['"]?\s*(?::\s*[a-zA-Z0-9_$<>\[\]]+\s*)?(?:=|:)\s*(?:['"`]([^'"`\\]*(?:\\.[^'"`\\]*)*)['"`])"""
)

_KWARG_ASSIGNMENT_PATTERN = re.compile(
    r"""\b([a-zA-Z0-9_$]+)\s*=\s*(?:['"`]([^'"`\\]*(?:\\.[^'"`\\]*)*)['"`])"""
)


def _is_comment_line(stripped_line: str, language: Language) -> bool:
    """Checks if a stripped line is purely a comment or docstring boundary."""
    if language == Language.PYTHON:
        return (
            stripped_line.startswith("#")
            or (stripped_line.startswith('"""') and stripped_line.endswith('"""') and len(stripped_line) >= 6)
            or (stripped_line.startswith("'''") and stripped_line.endswith("'''") and len(stripped_line) >= 6)
        )
    return (
        stripped_line.startswith("//")
        or stripped_line.startswith("/*")
        or stripped_line.startswith("*")
    )


def _is_excluded_placeholder(val: str) -> bool:
    """Checks if a string value is an obvious placeholder or non-secret test string."""
    v_clean = val.strip()
    v_lower = v_clean.lower()

    if len(v_clean) == 0 or v_lower in _EXCLUDED_PLACEHOLDERS:
        return True

    # Template / placeholder formats: <PASSWORD>, {API_KEY}, [SECRET], ${TOKEN}, etc.
    if (
        (v_clean.startswith("<") and v_clean.endswith(">"))
        or (v_clean.startswith("{") and v_clean.endswith("}"))
        or (v_clean.startswith("[") and v_clean.endswith("]"))
        or (v_clean.startswith("${") and v_clean.endswith("}"))
        or (v_clean.startswith("{{") and v_clean.endswith("}}"))
        or (v_clean.startswith("%") and v_clean.endswith("%"))
    ):
        return True

    # Obvious placeholder indicators
    for indicator in (
        "placeholder",
        "your_",
        "your-",
        "example",
        "dummy",
        "fake",
        "mock",
        "enter_",
        "enter-",
        "sample",
        "replace_me",
        "changeme",
    ):
        if indicator in v_lower:
            return True

    # URLs
    if v_lower.startswith("http://") or v_lower.startswith("https://") or v_lower.startswith("ws://") or v_lower.startswith("wss://"):
        return True

    # Email addresses
    if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v_clean):
        return True

    # Selectors / XPath
    if v_clean.startswith(("#", ".", "/", "//", "input[", "button[", "[data-", "text=")):
        return True

    # Short trivial numbers/strings
    if len(v_clean) < 4:
        return True

    return False


def _is_suspicious_var_name(name: str) -> bool:
    """Checks if variable name strongly suggests a credential/secret."""
    if not name:
        return False
    name_lower = name.lower()
    for suffix in _LOCATOR_VAR_SUFFIXES:
        if name_lower.endswith(suffix):
            return False
    return bool(_SECRET_VAR_NAME_PATTERN.match(name))


def _redact_snippet(line: str, secret_val: str) -> str:
    """Safely redacts the detected secret value from the code snippet line."""
    if not secret_val:
        return line
    # Replace literal quoted forms first
    line = line.replace(f'"{secret_val}"', '"[REDACTED]"')
    line = line.replace(f"'{secret_val}'", "'[REDACTED]'")
    line = line.replace(f"`{secret_val}`", "`[REDACTED]`")
    # If unquoted or raw match remains
    if secret_val in line:
        line = line.replace(secret_val, "[REDACTED]")
    return line


def detect_ap09(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP09 (Hardcoded Secrets) in the provided automation script.

    Identifies embedded credentials, passwords, tokens, API keys, and private keys.
    Redacts all secret values in the returned Finding objects.

    Returns:
        List of Finding objects with severity HIGH and confidence HIGH.
    """
    if not script_content or not script_content.strip():
        return []

    validation = validate_framework_and_language(framework, language)
    if not validation.is_valid:
        return []

    parsed_framework = Framework.SELENIUM if "selenium" in str(framework).lower() else (
        Framework.PLAYWRIGHT if "playwright" in str(framework).lower() else (
            Framework.CYPRESS if "cypress" in str(framework).lower() else None
        )
    )
    parsed_language = Language.PYTHON if "python" in str(language).lower() else (
        Language.TYPESCRIPT if "typescript" in str(language).lower() else (
            Language.JAVASCRIPT if "javascript" in str(language).lower() else None
        )
    )

    if parsed_framework is None or parsed_language is None:
        return []

    raw_lines = script_content.splitlines()
    findings: list[Finding] = []
    in_block_comment = False
    in_multiline_docstring = False

    for idx, raw_line in enumerate(raw_lines):
        line_num = idx + 1
        stripped = raw_line.strip()
        if not stripped:
            continue

        # Handle Python multiline docstrings
        if parsed_language == Language.PYTHON:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                delimiter = stripped[:3]
                if stripped.count(delimiter) >= 2 and len(stripped) >= 6:
                    continue  # Single-line docstring
                in_multiline_docstring = not in_multiline_docstring
                continue
            if in_multiline_docstring:
                if '"""' in stripped or "'''" in stripped:
                    in_multiline_docstring = False
                continue
        else:
            # Handle JS/TS multiline comments
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith("/*"):
                if "*/" not in stripped:
                    in_block_comment = True
                continue

        # Skip comment lines
        if _is_comment_line(stripped, parsed_language):
            continue

        # Skip externalized configuration or environment retrieval
        if _ENV_OR_CONFIG_PATTERNS.search(stripped):
            continue

        # Check 1: Private Key Material (HIGH confidence)
        if _PRIVATE_KEY_PATTERN.search(stripped):
            redacted_line = _PRIVATE_KEY_PATTERN.sub("-----BEGIN [REDACTED] PRIVATE KEY-----", stripped)
            findings.append(
                Finding(
                    id=f"AP09-L{line_num}",
                    anti_pattern_id="AP09",
                    anti_pattern_name="Hardcoded Secrets",
                    severity=Severity.HIGH,
                    confidence=Confidence.HIGH,
                    line_start=line_num,
                    line_end=line_num,
                    code_snippet=redacted_line,
                    reason="Hardcoded private key material detected.",
                    explanation="",
                    suggested_fix="",
                )
            )
            continue

        # Check 2: Standalone JWT token
        jwt_match = _JWT_PATTERN.search(stripped)
        if jwt_match:
            secret_val = jwt_match.group(0)
            redacted_line = _redact_snippet(stripped, secret_val)
            findings.append(
                Finding(
                    id=f"AP09-L{line_num}",
                    anti_pattern_id="AP09",
                    anti_pattern_name="Hardcoded Secrets",
                    severity=Severity.HIGH,
                    confidence=Confidence.HIGH,
                    line_start=line_num,
                    line_end=line_num,
                    code_snippet=redacted_line,
                    reason="Hardcoded JWT token detected.",
                    explanation="",
                    suggested_fix="",
                )
            )
            continue

        # Check 3: Suspicious variable assignments & object properties
        matched_secret = False
        for pattern in (_ASSIGNMENT_PATTERN, _KWARG_ASSIGNMENT_PATTERN):
            for match in pattern.finditer(stripped):
                var_name = match.group(1)
                val = match.group(2)

                if _is_suspicious_var_name(var_name) and not _is_excluded_placeholder(val):
                    redacted_line = _redact_snippet(stripped, val)
                    findings.append(
                        Finding(
                            id=f"AP09-L{line_num}",
                            anti_pattern_id="AP09",
                            anti_pattern_name="Hardcoded Secrets",
                            severity=Severity.HIGH,
                            confidence=Confidence.HIGH,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=redacted_line,
                            reason=f"Hardcoded secret/credential detected for variable '{var_name}'.",
                            explanation="",
                            suggested_fix="",
                        )
                    )
                    matched_secret = True
                    break
            if matched_secret:
                break

    # Sort and deduplicate findings by line
    findings.sort(key=lambda f: (f.line_start, f.line_end))
    seen_lines = set()
    unique_findings = []
    for f in findings:
        if f.line_start not in seen_lines:
            seen_lines.add(f.line_start)
            unique_findings.append(f)

    return unique_findings
