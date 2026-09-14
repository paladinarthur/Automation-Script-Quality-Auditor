"""
AP07 — Missing Assertions Detector.

Performs conservative static analysis to detect test cases that perform meaningful
browser or test actions but contain no recognizable assertion or verification.

Rules & Boundaries:
- Python:
  - Identifies test functions (standard test_* / *_test, or non-helper functions clearly containing framework-specific browser actions).
  - Excludes setup/teardown functions and helper functions.
  - Recognizes Python `assert` statements, Playwright `expect(...)` calls, and unittest `self.assert*` calls.
  - Does not treat arbitrary `check_*` functions as assertions.
- JavaScript / TypeScript:
  - Identifies test blocks: it('...', ...), test('...', ...).
  - Recognizes Playwright assertions: expect(...).
  - Recognizes Cypress assertions: .should(...), .and(...).
- Requires at least one meaningful framework-specific browser/test action.
- Never flags tests without browser actions.
- High severity, High confidence when test boundaries and actions are clear.
"""

import ast
import re
from dataclasses import dataclass
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

# Framework-specific browser action patterns
_SELENIUM_PY_ACTIONS = re.compile(
    r"\b(?:driver\s*\.\s*(?:get|find_element|find_elements|execute_script)|find_element(?:s)?\s*\(|\.(?:send_keys|click|clear|submit)\s*\()",
    re.IGNORECASE,
)

_PLAYWRIGHT_PY_ACTIONS = re.compile(
    r"\bpage\s*\.\s*(?:goto|locator|get_by_[a-z_]+|click|fill|type|press|check|uncheck|select_option|wait_for_selector)\b",
    re.IGNORECASE,
)

_GENERIC_BROWSER_ACTIONS = re.compile(
    r"\b(?:click|fill|type|send_keys|goto|visit|press|select_option|check|uncheck|submit|find_element|find_elements)\b"
    r"|\bpage\.(?:locator|\$|\$\$|waitForSelector|wait_for_selector)\b"
    r"|\bcy\.(?:get|find|contains)\b",
    re.IGNORECASE,
)

# Cypress assertions
_CYPRESS_ASSERTION = re.compile(r"\.(?:should|and)\s*\(", re.IGNORECASE)

# Playwright / generic JS test assertions
_PLAYWRIGHT_JS_ASSERTION = re.compile(r"\bexpect\s*\(", re.IGNORECASE)

# Known setup / teardown / helper prefixes to exclude from being flagged as tests
_NON_TEST_FUNCTION_PREFIXES = {
    "setup",
    "teardown",
    "before",
    "after",
    "fixture",
    "helper",
    "util",
    "login_helper",
    "navigate_to",
    "fill_form",
    "open_browser",
    "close_browser",
    "init",
    "check",
    "verify",
    "assert",
}

_JS_TEST_START_REGEX = re.compile(
    r"""\b(?:it|test)(?:\.[a-zA-Z0-9_$]+)?\s*\(\s*['"`](.*?)['"`]|\bfunction\s+([a-zA-Z0-9_$]*test[a-zA-Z0-9_$]*)\s*\("""
)


def _is_comment_line(stripped_line: str, language: Language) -> bool:
    """Checks if a stripped line is purely a comment."""
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


def _strip_js_strings_and_comments(line: str, in_block_comment: bool) -> tuple[str, bool]:
    """Removes string literals and comments from JS line."""
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
                i += 1
                continue
            if ch == '"':
                in_double_quote = True
                i += 1
                continue
            if ch == "`":
                in_backtick = True
                i += 1
                continue
            cleaned.append(ch)
            i += 1
        elif in_single_quote:
            if ch == "\\" and i + 1 < n:
                i += 2
            elif ch == "'":
                in_single_quote = False
                i += 1
            else:
                i += 1
        elif in_double_quote:
            if ch == "\\" and i + 1 < n:
                i += 2
            elif ch == '"':
                in_double_quote = False
                i += 1
            else:
                i += 1
        elif in_backtick:
            if ch == "\\" and i + 1 < n:
                i += 2
            elif ch == "`":
                in_backtick = False
                i += 1
            else:
                i += 1

    return "".join(cleaned), in_block_comment


# --- Python AST Analysis ---

class _PythonTestVisitor(ast.NodeVisitor):
    """Inspects a Python function to check for browser actions and assertions."""

    def __init__(self, framework: Framework) -> None:
        self.framework = framework
        self.has_assert = False
        self.has_browser_action = False

    def visit_Assert(self, node: ast.Assert) -> None:
        self.has_assert = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = ""
        full_call_str = ""

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            full_call_str = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            # Reconstruct attr like driver.find_element or self.assertEqual
            val_name = ""
            if isinstance(node.func.value, ast.Name):
                val_name = node.func.value.id
            full_call_str = f"{val_name}.{func_name}" if val_name else func_name

        # 1. Playwright Python assertion: expect(...)
        if func_name == "expect":
            self.has_assert = True

        # 2. Unittest-style assertion: self.assertEqual, self.assertTrue, assert_*
        if full_call_str.startswith("self.assert") or func_name.startswith("assert_") or func_name == "assert":
            self.has_assert = True

        # 3. Check for framework-specific browser actions
        if self.framework == Framework.SELENIUM:
            if _SELENIUM_PY_ACTIONS.search(full_call_str) or _SELENIUM_PY_ACTIONS.search(func_name):
                self.has_browser_action = True
        elif self.framework == Framework.PLAYWRIGHT:
            if _PLAYWRIGHT_PY_ACTIONS.search(full_call_str) or _PLAYWRIGHT_PY_ACTIONS.search(func_name):
                self.has_browser_action = True
        else:
            if _GENERIC_BROWSER_ACTIONS.search(full_call_str) or _GENERIC_BROWSER_ACTIONS.search(func_name):
                self.has_browser_action = True

        self.generic_visit(node)


def _is_python_test_function(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    raw_lines: list[str],
    framework: Framework,
) -> bool:
    """
    Determines whether a Python function is a recognizable test function.
    
    Rules:
    - Standard naming: test_* or *_test.
    - Excludes setup/teardown/helper/util prefixes.
    - Alternatively, allows a non-helper function if it clearly contains
      framework-specific browser actions.
    """
    name_lower = func_node.name.lower()

    # Exclude known setup / teardown / helper functions unless function is explicitly test_*
    is_test_named = name_lower.startswith("test") or name_lower.endswith("test")
    if not is_test_named:
        if any(name_lower.startswith(prefix) or name_lower.endswith(prefix) or f"_{prefix}_" in name_lower for prefix in _NON_TEST_FUNCTION_PREFIXES):
            return False
    else:
        # If named test_*, still exclude obvious setup/teardown/fixture
        if any(name_lower.startswith(prefix) for prefix in ("setup", "teardown", "fixture", "before", "after")):
            return False
        return True

    # If not named test_*, only consider if it clearly contains framework-specific browser actions
    start_line = func_node.lineno
    end_line = getattr(func_node, "end_lineno", start_line)
    body_text = "\n".join(raw_lines[start_line - 1 : end_line])

    if framework == Framework.SELENIUM:
        return bool(_SELENIUM_PY_ACTIONS.search(body_text))
    if framework == Framework.PLAYWRIGHT:
        return bool(_PLAYWRIGHT_PY_ACTIONS.search(body_text))

    return False


@dataclass
class _TestBlock:
    name: str
    line_start: int
    line_end: int
    has_browser_action: bool
    has_assertion: bool
    code_snippet: str


def _analyze_python_script(script_content: str, framework: Framework) -> list[_TestBlock]:
    """Analyzes Python script using AST to detect test functions."""
    test_blocks: list[_TestBlock] = []
    raw_lines = script_content.splitlines()

    try:
        tree = ast.parse(script_content)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_python_test_function(node, raw_lines, framework):
                continue

            visitor = _PythonTestVisitor(framework)
            visitor.visit(node)

            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)
            body_lines = raw_lines[start_line - 1 : end_line]
            snippet = "\n".join(body_lines)

            has_browser_act = visitor.has_browser_action
            if not has_browser_act:
                for bl in body_lines:
                    s = bl.strip()
                    if s and not s.startswith("#"):
                        if framework == Framework.SELENIUM and _SELENIUM_PY_ACTIONS.search(s):
                            has_browser_act = True
                            break
                        elif framework == Framework.PLAYWRIGHT and _PLAYWRIGHT_PY_ACTIONS.search(s):
                            has_browser_act = True
                            break

            test_blocks.append(
                _TestBlock(
                    name=node.name,
                    line_start=start_line,
                    line_end=end_line,
                    has_browser_action=has_browser_act,
                    has_assertion=visitor.has_assert,
                    code_snippet=snippet,
                )
            )

    return test_blocks


# --- JavaScript / TypeScript Analysis ---

def _analyze_js_script(
    script_content: str,
    framework: Framework,
    language: Language,
) -> list[_TestBlock]:
    """Analyzes JS/TS script to detect it(...) / test(...) blocks and their verification."""
    raw_lines = script_content.splitlines()
    blocks: list[_TestBlock] = []
    line_count = len(raw_lines)
    i = 0
    in_block_comment = False

    while i < line_count:
        raw_line = raw_lines[i]
        line_num = i + 1
        match = _JS_TEST_START_REGEX.search(raw_line)

        if match:
            test_name = match.group(1) or match.group(2) or "anonymous test"
            start_line = line_num

            brace_level = 0
            has_browser_action = False
            has_assertion = False
            end_line = start_line
            entered_body = False

            j = i
            test_block_comment = in_block_comment

            while j < line_count:
                cur_line = raw_lines[j]
                code_only, test_block_comment = _strip_js_strings_and_comments(cur_line, test_block_comment)

                if not entered_body:
                    # Find opening brace of the test callback / function
                    # Look for => or function keyword, or first { on or after start line
                    arrow_idx = code_only.find("=>")
                    func_idx = code_only.find("function")
                    search_from = 0
                    if arrow_idx != -1:
                        search_from = arrow_idx + 2
                    elif func_idx != -1:
                        search_from = func_idx + 8

                    open_brace_idx = code_only.find("{", search_from)
                    if open_brace_idx == -1 and search_from > 0:
                        open_brace_idx = code_only.find("{")

                    if open_brace_idx != -1:
                        entered_body = True
                        brace_level = 1
                        # Scan remaining characters after the opening { on this line
                        chars_after = code_only[open_brace_idx + 1 :]
                        if chars_after:
                            if _GENERIC_BROWSER_ACTIONS.search(chars_after):
                                has_browser_action = True
                            if framework == Framework.CYPRESS:
                                if _CYPRESS_ASSERTION.search(chars_after) or _PLAYWRIGHT_JS_ASSERTION.search(chars_after):
                                    has_assertion = True
                            else:
                                if _PLAYWRIGHT_JS_ASSERTION.search(chars_after):
                                    has_assertion = True

                            for ch in chars_after:
                                if ch == "{":
                                    brace_level += 1
                                elif ch == "}":
                                    brace_level -= 1
                                    if brace_level == 0:
                                        end_line = j + 1
                                        break

                        if brace_level == 0:
                            end_line = j + 1
                            break
                else:
                    # Inside the test body
                    if code_only:
                        if _GENERIC_BROWSER_ACTIONS.search(code_only):
                            has_browser_action = True

                        if framework == Framework.CYPRESS:
                            if _CYPRESS_ASSERTION.search(code_only) or _PLAYWRIGHT_JS_ASSERTION.search(code_only):
                                has_assertion = True
                        else:
                            if _PLAYWRIGHT_JS_ASSERTION.search(code_only):
                                has_assertion = True

                        for ch in code_only:
                            if ch == "{":
                                brace_level += 1
                            elif ch == "}":
                                brace_level -= 1
                                if brace_level == 0:
                                    end_line = j + 1
                                    break

                    if brace_level == 0:
                        break

                j += 1

            snippet = "\n".join(raw_lines[start_line - 1 : end_line])
            blocks.append(
                _TestBlock(
                    name=test_name,
                    line_start=start_line,
                    line_end=end_line,
                    has_browser_action=has_browser_action,
                    has_assertion=has_assertion,
                    code_snippet=snippet,
                )
            )
            i = end_line
            continue

        _, in_block_comment = _strip_js_strings_and_comments(raw_line, in_block_comment)
        i += 1

    return blocks


def detect_ap07(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP07 (Missing Assertions) in the provided script content.

    Flags recognizable test functions/blocks that perform meaningful browser actions
    but contain no recognizable assertion or verification.

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

    if parsed_language == Language.PYTHON:
        test_blocks = _analyze_python_script(script_content, parsed_framework)
    else:
        test_blocks = _analyze_js_script(script_content, parsed_framework, parsed_language)

    findings: list[Finding] = []

    for block in test_blocks:
        if block.has_browser_action and not block.has_assertion:
            findings.append(
                Finding(
                    id=f"AP07-L{block.line_start}",
                    anti_pattern_id="AP07",
                    anti_pattern_name="Missing Assertions",
                    severity=Severity.HIGH,
                    confidence=Confidence.HIGH,
                    line_start=block.line_start,
                    line_end=block.line_end,
                    code_snippet=block.code_snippet,
                    reason=(
                        f"Test '{block.name}' performs meaningful browser actions without any "
                        f"recognizable assertion or verification."
                    ),
                    explanation="",
                    suggested_fix="",
                )
            )

    findings.sort(key=lambda f: (f.line_start, f.line_end))
    return findings
