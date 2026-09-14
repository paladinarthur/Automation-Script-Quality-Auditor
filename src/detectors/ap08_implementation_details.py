"""
AP08 — Testing Implementation Details Detector.

Performs conservative static analysis to detect test assertions that primarily verify
internal application implementation details rather than externally observable behavior.

Approved Signals:
1. Assertions against private/internal application state or members:
   - assert app._internal_state == "ready"
   - assert service._cache == expected
   - self.assertEqual(app._internal_state, "ready")
   - expect(component._internalState).toBe(...)
   - expect(app.internalState).toBe(...)

2. Assertions that directly verify internal application methods were called:
   - mock_service.internal_method.assert_called_once()
   - service.process.assert_called_once()
   - expect(mockService.internalMethod).toHaveBeenCalled()
   - expect(mockService.process).toHaveBeenCalledTimes(1)

Exclusions:
- Normal browser actions: page.click(), driver.find_element(), cy.visit(), etc.
- Normal observable UI assertions: assert "Dashboard" in driver.title, expect(page.locator(...)).toBeVisible()
- Normal test setup / mocks by themselves without internal assertion: service = Mock(), cy.intercept()
- Legitimate API/network response verification: response.status_code == 200
- Framework APIs and generic variable assertions: assert result == True, assert status == "active"
"""

import ast
import re
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

# Exclude standard dunder names and common framework attributes from being considered private state
_IGNORED_PRIVATE_ATTRS = {
    "__name__",
    "__doc__",
    "__class__",
    "__dict__",
    "__file__",
    "__version__",
    "__module__",
    "__qualname__",
    "__path__",
    "__package__",
    "__spec__",
    "__loader__",
    "__cached__",
    "__annotations__",
}

_MOCK_ASSERT_METHOD_NAMES = {
    "assert_called",
    "assert_called_once",
    "assert_called_once_with",
    "assert_called_with",
    "assert_has_calls",
    "assert_any_call",
}

# JS/TS Expect mock/spy assertion pattern: expect(target).toHaveBeenCalled*
_JS_MOCK_CALL_ASSERTION = re.compile(
    r"""\bexpect\s*\(\s*([a-zA-Z0-9_$.]+)\s*\)\s*\.\s*(?:toHaveBeenCalled|toHaveBeenCalledTimes|toHaveBeenCalledWith|toHaveBeenLastCalledWith|toHaveBeenNthCalledWith)\s*\(""",
    re.IGNORECASE,
)

# JS/TS Expect private/internal property assertion: expect(target._privateProp).toBe(...)
_JS_INTERNAL_PROPERTY_ASSERTION = re.compile(
    r"""\bexpect\s*\(\s*([a-zA-Z0-9_$.]*?(?:\._[a-zA-Z0-9_$]+|\.internal[a-zA-Z0-9_$]+|[a-zA-Z0-9_$.]*_internal[a-zA-Z0-9_$]*))\s*\)\s*\.\s*(?:toBe|toEqual|toStrictEqual|toMatch|toContain|toBeTruthy|toBeFalsy|toBeDefined|toBeNull|toBeNaN|to\.(?:equal|be|eq))\s*\(""",
    re.IGNORECASE,
)

# Cypress spy / internal member assertions
_CYPRESS_INTERNAL_ASSERTION = re.compile(
    r"""\bcy\s*\.\s*(?:get\s*\(\s*['"]@(mock[a-zA-Z0-9_$]*|spy[a-zA-Z0-9_$]*|[a-zA-Z0-9_$]*mock[a-zA-Z0-9_$]*|[a-zA-Z0-9_$]*spy[a-zA-Z0-9_$]*)['"]|window\s*\(\s*\)\s*\.\s*its\s*\(\s*['"](_[a-zA-Z0-9_$]+|internal[a-zA-Z0-9_$]+)['"])\s*\)\s*\.\s*(?:should|and)\s*\("""
    r"""|\bexpect\s*\(\s*([a-zA-Z0-9_$.]+)\s*\)\s*\.to\.(?:have\.been\.called|be\.called)\b""",
    re.IGNORECASE,
)


def _is_private_or_internal_name(name: str) -> bool:
    """Checks whether an identifier name indicates private or internal state/method."""
    if not name or name in _IGNORED_PRIVATE_ATTRS:
        return False
    if name.startswith("__") and name.endswith("__"):
        return False
    if name.startswith("_"):
        return True
    lower = name.lower()
    if (
        lower.startswith("internal_")
        or lower.startswith("internalstate")
        or lower.startswith("internalmethod")
        or lower == "internalstate"
        or lower == "internalmethod"
        or "internal_state" in lower
        or "internal_method" in lower
    ):
        return True
    if name.startswith("internal") and len(name) > 8 and name[8].isupper():
        return True
    return False


def _extract_private_attribute(node: ast.AST) -> str | None:
    """Recursively checks an AST expression for access to private/internal attributes or names."""
    if isinstance(node, ast.Attribute):
        if _is_private_or_internal_name(node.attr):
            return node.attr
        return _extract_private_attribute(node.value)
    if isinstance(node, ast.Name):
        if _is_private_or_internal_name(node.id):
            return node.id
        return None
    if isinstance(node, ast.Compare):
        left_res = _extract_private_attribute(node.left)
        if left_res:
            return left_res
        for comp in node.comparators:
            comp_res = _extract_private_attribute(comp)
            if comp_res:
                return comp_res
        return None
    if isinstance(node, ast.UnaryOp):
        return _extract_private_attribute(node.operand)
    if isinstance(node, ast.BinOp):
        return _extract_private_attribute(node.left) or _extract_private_attribute(node.right)
    if isinstance(node, ast.Call):
        func_res = _extract_private_attribute(node.func)
        if func_res:
            return func_res
        for arg in node.args:
            arg_res = _extract_private_attribute(arg)
            if arg_res:
                return arg_res
        return None
    return None


def _get_call_full_name(node: ast.AST) -> str:
    """Reconstructs dotted name from AST Attribute / Name chain."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        val = _get_call_full_name(node.value)
        return f"{val}.{node.attr}" if val else node.attr
    return ""


class _PythonImplementationDetailsVisitor(ast.NodeVisitor):
    """AST visitor to detect implementation detail assertions in Python tests."""

    def __init__(self, raw_lines: list[str]) -> None:
        self.raw_lines = raw_lines
        self.findings: list[Finding] = []

    def visit_Assert(self, node: ast.Assert) -> None:
        # Check if the assert test expression targets private or internal state
        private_name = _extract_private_attribute(node.test)
        if private_name:
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)
            snippet = "\n".join(self.raw_lines[start_line - 1 : end_line]).strip()

            self.findings.append(
                Finding(
                    id=f"AP08-L{start_line}",
                    anti_pattern_id="AP08",
                    anti_pattern_name="Testing Implementation Details",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    line_start=start_line,
                    line_end=end_line,
                    code_snippet=snippet,
                    reason=f"Test directly asserts private/internal state or member '{private_name}' rather than observable behavior.",
                    explanation="",
                    suggested_fix="",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # 1. Check for mock assertions: mock.assert_called_once(), service.process.assert_called_once(), etc.
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            if method_name in _MOCK_ASSERT_METHOD_NAMES:
                target_str = _get_call_full_name(node.func.value)
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                snippet = "\n".join(self.raw_lines[start_line - 1 : end_line]).strip()

                self.findings.append(
                    Finding(
                        id=f"AP08-L{start_line}",
                        anti_pattern_id="AP08",
                        anti_pattern_name="Testing Implementation Details",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        line_start=start_line,
                        line_end=end_line,
                        code_snippet=snippet,
                        reason=f"Test asserts mock/internal method call '{target_str}.{method_name}()' rather than observable behavior.",
                        explanation="",
                        suggested_fix="",
                    )
                )

            # 2. Check for unittest assertions: self.assertEqual(app._internal_state, "ready")
            elif method_name.startswith("assert"):
                for arg in node.args:
                    private_name = _extract_private_attribute(arg)
                    if private_name:
                        start_line = node.lineno
                        end_line = getattr(node, "end_lineno", start_line)
                        snippet = "\n".join(self.raw_lines[start_line - 1 : end_line]).strip()

                        self.findings.append(
                            Finding(
                                id=f"AP08-L{start_line}",
                                anti_pattern_id="AP08",
                                anti_pattern_name="Testing Implementation Details",
                                severity=Severity.MEDIUM,
                                confidence=Confidence.MEDIUM,
                                line_start=start_line,
                                line_end=end_line,
                                code_snippet=snippet,
                                reason=f"Test asserts private/internal state or member '{private_name}' rather than observable behavior.",
                                explanation="",
                                suggested_fix="",
                            )
                        )
                        break

        self.generic_visit(node)


def _strip_js_comments(line: str, in_block_comment: bool) -> tuple[str, bool]:
    """Strips comments from a JS/TS line while preserving string literals."""
    cleaned = []
    i = 0
    n = len(line)
    in_single_quote = False
    in_double_quote = False
    in_backtick = False

    while i < n:
        if in_block_comment:
            if i + 1 < n and line[i : i + 2] == "*/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        ch = line[i]

        if not in_single_quote and not in_double_quote and not in_backtick:
            if i + 1 < n and line[i : i + 2] == "//":
                break
            if i + 1 < n and line[i : i + 2] == "/*":
                in_block_comment = True
                i += 2
                continue
            if ch == "'":
                in_single_quote = True
                cleaned.append(ch)
                i += 1
                continue
            if ch == '"':
                in_double_quote = True
                cleaned.append(ch)
                i += 1
                continue
            if ch == "`":
                in_backtick = True
                cleaned.append(ch)
                i += 1
                continue
            cleaned.append(ch)
            i += 1
        elif in_single_quote:
            cleaned.append(ch)
            if ch == "\\" and i + 1 < n:
                i += 1
                cleaned.append(line[i])
                i += 1
            elif ch == "'":
                in_single_quote = False
                i += 1
            else:
                i += 1
        elif in_double_quote:
            cleaned.append(ch)
            if ch == "\\" and i + 1 < n:
                i += 1
                cleaned.append(line[i])
                i += 1
            elif ch == '"':
                in_double_quote = False
                i += 1
            else:
                i += 1
        elif in_backtick:
            cleaned.append(ch)
            if ch == "\\" and i + 1 < n:
                i += 1
                cleaned.append(line[i])
                i += 1
            elif ch == "`":
                in_backtick = False
                i += 1
            else:
                i += 1

    return "".join(cleaned), in_block_comment


def _analyze_js_script(
    script_content: str,
    framework: Framework,
    language: Language,
) -> list[Finding]:
    """Analyzes JS/TS script content for implementation detail assertions."""
    findings: list[Finding] = []
    raw_lines = script_content.splitlines()
    in_block_comment = False

    for idx, raw_line in enumerate(raw_lines):
        line_num = idx + 1
        code_line, in_block_comment = _strip_js_comments(raw_line, in_block_comment)
        stripped = code_line.strip()
        if not stripped:
            continue

        # 1. Playwright / Jest / Vitest expect(...).toHaveBeenCalled*
        m_call = _JS_MOCK_CALL_ASSERTION.search(stripped)
        if m_call:
            target = m_call.group(1).strip()
            findings.append(
                Finding(
                    id=f"AP08-L{line_num}",
                    anti_pattern_id="AP08",
                    anti_pattern_name="Testing Implementation Details",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    line_start=line_num,
                    line_end=line_num,
                    code_snippet=raw_line.strip(),
                    reason=f"Test asserts internal method call '{target}' rather than observable behavior.",
                    explanation="",
                    suggested_fix="",
                )
            )
            continue

        # 2. Expect private / internal property assertions: expect(component._internalState).toBe(...)
        m_prop = _JS_INTERNAL_PROPERTY_ASSERTION.search(stripped)
        if m_prop:
            target = m_prop.group(1).strip()
            findings.append(
                Finding(
                    id=f"AP08-L{line_num}",
                    anti_pattern_id="AP08",
                    anti_pattern_name="Testing Implementation Details",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    line_start=line_num,
                    line_end=line_num,
                    code_snippet=raw_line.strip(),
                    reason=f"Test directly asserts private/internal property '{target}' rather than observable behavior.",
                    explanation="",
                    suggested_fix="",
                )
            )
            continue

        # 3. Cypress spy / internal member assertions
        if framework == Framework.CYPRESS:
            m_cy = _CYPRESS_INTERNAL_ASSERTION.search(stripped)
            if m_cy:
                target = m_cy.group(1) or m_cy.group(2) or m_cy.group(3) or "internal member"
                findings.append(
                    Finding(
                        id=f"AP08-L{line_num}",
                        anti_pattern_id="AP08",
                        anti_pattern_name="Testing Implementation Details",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=raw_line.strip(),
                        reason=f"Test asserts internal mock/member '{target.strip()}' rather than observable behavior.",
                        explanation="",
                        suggested_fix="",
                    )
                )
                continue

    return findings


def detect_ap08(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP08 (Testing Implementation Details) in the provided script content.

    Flags tests that verify internal application implementation details, private state,
    or mock method calls rather than observable user/system behavior.

    Returns:
        List of Finding objects with severity MEDIUM and confidence MEDIUM.
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

    if parsed_language == Language.PYTHON:
        raw_lines = script_content.splitlines()
        try:
            tree = ast.parse(script_content)
        except SyntaxError:
            return []

        visitor = _PythonImplementationDetailsVisitor(raw_lines)
        visitor.visit(tree)
        findings = visitor.findings
    else:
        findings = _analyze_js_script(script_content, parsed_framework, parsed_language)

    # Sort and deduplicate findings by line
    findings.sort(key=lambda f: (f.line_start, f.line_end))
    seen_lines = set()
    unique_findings = []
    for f in findings:
        if f.line_start not in seen_lines:
            seen_lines.add(f.line_start)
            unique_findings.append(f)

    return unique_findings
