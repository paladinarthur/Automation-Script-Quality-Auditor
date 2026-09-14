"""
AP04 — Poor Test Structure Detector.

Conservative heuristic detector focusing on two measurable structural signals:
1. Potentially Large Test:
   A test/function containing 30 or more meaningful statements.
2. Excessive Nesting:
   A test/function containing nesting depth >= 4 (if, for, while, try, with, blocks).

Exclusions & Boundaries:
- Blank lines, comments, and imports do not count toward statement counts.
- String literals and comments do not artificially increase nesting depth.
- Top-level code outside test functions is not treated as a test function.
- Does not flag tests with fewer than 30 statements or nesting depth < 4.
"""

import ast
import re
from dataclasses import dataclass
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

LARGE_TEST_THRESHOLD = 30
NESTING_DEPTH_THRESHOLD = 4


@dataclass
class _FunctionBlock:
    name: str
    line_start: int
    line_end: int
    meaningful_statement_count: int
    max_nesting_depth: int
    code_snippet: str


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


def _is_import_line(stripped_line: str, language: Language) -> bool:
    """Checks if a stripped line is an import."""
    if language == Language.PYTHON:
        return stripped_line.startswith("import ") or stripped_line.startswith("from ")
    return (
        stripped_line.startswith("import ")
        or stripped_line.startswith("from ")
        or bool(re.search(r"\brequire\s*\(", stripped_line))
    )


# --- Python Analysis (using standard library AST) ---

class _PythonNestingVisitor(ast.NodeVisitor):
    """Calculates the maximum control-flow nesting depth inside a Python function body."""

    def __init__(self) -> None:
        self.max_depth = 0
        self.current_depth = 0

    def _visit_control_block(self, node: ast.AST) -> None:
        self.current_depth += 1
        if self.current_depth > self.max_depth:
            self.max_depth = self.current_depth
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._visit_control_block(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_control_block(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_control_block(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_control_block(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_control_block(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_control_block(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_control_block(node)


def _is_docstring_node(stmt: ast.AST, func_body: list[ast.stmt]) -> bool:
    """Checks if an AST node is the top-level docstring of a function body."""
    if func_body and stmt is func_body[0]:
        if isinstance(stmt, ast.Expr):
            val = stmt.value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                return True
    return False


def _count_python_ast_statements(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:
    """
    Counts actual meaningful AST statements inside a Python function body.

    Includes:
    - Normal statements (assignments, expressions, assertions, returns)
    - Control-flow statements (if, for, while, try, with) and all nested statements

    Excludes:
    - The enclosing function definition itself
    - Import statements (import ..., from ... import ...)
    - Function docstring
    - Comments and blank lines (naturally excluded by AST)
    """
    count = 0
    func_body = func_node.body

    for node in ast.walk(func_node):
        if node is func_node:
            continue
        if isinstance(node, ast.stmt):
            # Exclude import statements
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            # Exclude function docstring
            if _is_docstring_node(node, func_body):
                continue
            count += 1

    return count


def _analyze_python_functions(script_content: str) -> list[_FunctionBlock]:
    """Extracts function boundaries and computes signals for Python scripts using AST."""
    blocks: list[_FunctionBlock] = []
    raw_lines = script_content.splitlines()

    try:
        tree = ast.parse(script_content)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)

            # Calculate nesting depth inside body
            visitor = _PythonNestingVisitor()
            for stmt in node.body:
                visitor.visit(stmt)

            stmt_count = _count_python_ast_statements(node)
            snippet = "\n".join(raw_lines[start_line - 1 : end_line])

            blocks.append(
                _FunctionBlock(
                    name=node.name,
                    line_start=start_line,
                    line_end=end_line,
                    meaningful_statement_count=stmt_count,
                    max_nesting_depth=visitor.max_depth,
                    code_snippet=snippet,
                )
            )

    return blocks


# --- JavaScript / TypeScript Analysis (Source-based scanner) ---

_JS_TEST_START_REGEX = re.compile(
    r"""\b(?:it|test)\s*\(\s*['"`](.*?)['"`]\s*,\s*(?:async\s*)?(?:(?:\([^)]*\)|[a-zA-Z0-9_$,\s{}]+)?\s*=>\s*\{|function\s*(?:\([^)]*\))?\s*\{)|\bfunction\s+([a-zA-Z0-9_$]+)\s*\([^)]*\)\s*\{"""
)


def _strip_js_strings_and_comments(line: str, in_block_comment: bool) -> tuple[str, bool]:
    """Removes string literals and comments from JS line to prevent false brace matches."""
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


def _analyze_js_functions(script_content: str, language: Language) -> list[_FunctionBlock]:
    """Extracts test function blocks and calculates statements and nesting for JS/TS."""
    raw_lines = script_content.splitlines()
    blocks: list[_FunctionBlock] = []
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

            # Track braces to locate function end and measure nesting
            brace_level = 0
            max_inner_brace_depth = 0
            meaningful_statements = 0
            end_line = start_line

            j = i
            test_block_comment = in_block_comment

            while j < line_count:
                cur_line = raw_lines[j]
                stripped = cur_line.strip()

                # Clean strings & comments for brace counting
                code_only, test_block_comment = _strip_js_strings_and_comments(cur_line, test_block_comment)

                # Count meaningful statements inside body (excluding declaration and closing bracket lines)
                if (
                    j > i
                    and stripped
                    and not _is_comment_line(stripped, language)
                    and not _is_import_line(stripped, language)
                    and not re.match(r"^[\s}\]);]+$", stripped)
                ):
                    meaningful_statements += 1

                for ch in code_only:
                    if ch == "{":
                        brace_level += 1
                        if brace_level > 1:
                            depth = brace_level - 1
                            if depth > max_inner_brace_depth:
                                max_inner_brace_depth = depth
                    elif ch == "}":
                        brace_level -= 1
                        if brace_level == 0:
                            end_line = j + 1
                            break

                if brace_level == 0 and j >= i:
                    break
                j += 1

            snippet = "\n".join(raw_lines[start_line - 1 : end_line])
            blocks.append(
                _FunctionBlock(
                    name=test_name,
                    line_start=start_line,
                    line_end=end_line,
                    meaningful_statement_count=meaningful_statements,
                    max_nesting_depth=max_inner_brace_depth,
                    code_snippet=snippet,
                )
            )
            i = end_line
            continue

        # Keep tracking block comments across file
        _, in_block_comment = _strip_js_strings_and_comments(raw_line, in_block_comment)
        i += 1

    return blocks


def detect_ap04(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP04 (Poor Test Structure) in the provided script content.

    Signals:
    1. Large Test: function with >= 30 meaningful statements.
    2. Excessive Nesting: function with control-flow nesting depth >= 4.

    Returns:
        List of Finding objects with severity MEDIUM and confidence MEDIUM.
    """
    if not script_content or not script_content.strip():
        return []

    validation = validate_framework_and_language(framework, language)
    if not validation.is_valid:
        return []

    parsed_language = Language.PYTHON if "python" in str(language).lower() else (
        Language.TYPESCRIPT if "typescript" in str(language).lower() else Language.JAVASCRIPT
    )

    if parsed_language == Language.PYTHON:
        blocks = _analyze_python_functions(script_content)
    else:
        blocks = _analyze_js_functions(script_content, parsed_language)

    findings: list[Finding] = []

    for block in blocks:
        # Signal 1: Potentially Large Test
        if block.meaningful_statement_count >= LARGE_TEST_THRESHOLD:
            findings.append(
                Finding(
                    id=f"AP04-L{block.line_start}-large",
                    anti_pattern_id="AP04",
                    anti_pattern_name="Poor Test Structure",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    line_start=block.line_start,
                    line_end=block.line_end,
                    code_snippet=block.code_snippet,
                    reason=(
                        f"Test '{block.name}' contains {block.meaningful_statement_count} meaningful statements "
                        f"(threshold is {LARGE_TEST_THRESHOLD}) and may benefit from being split into smaller logical units."
                    ),
                )
            )

        # Signal 2: Excessive Nesting
        if block.max_nesting_depth >= NESTING_DEPTH_THRESHOLD:
            findings.append(
                Finding(
                    id=f"AP04-L{block.line_start}-nesting",
                    anti_pattern_id="AP04",
                    anti_pattern_name="Poor Test Structure",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    line_start=block.line_start,
                    line_end=block.line_end,
                    code_snippet=block.code_snippet,
                    reason=(
                        f"Test '{block.name}' has excessive nesting depth of {block.max_nesting_depth} "
                        f"(threshold is {NESTING_DEPTH_THRESHOLD}), which may indicate overly complex branching or flow control."
                    ),
                )
            )

    findings.sort(key=lambda f: (f.line_start, f.line_end))
    return findings
