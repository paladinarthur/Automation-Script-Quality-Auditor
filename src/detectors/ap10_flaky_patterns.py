"""
AP10 — Potentially Flaky Patterns Detector.

Performs static analysis to detect coding patterns that can introduce flakiness,
non-determinism, or order/timing instability in automation test scripts.

Approved Signals:
- R1: Unsynchronized interaction after navigation (Selenium Python navigation without synchronization).
- R2: Uncontrolled randomness affecting test behavior, branching, or assertions.
- R3: Test-order dependency (shared mutable global state written in one test and read in another).
- R4: Manual/custom retry loops around browser actions catching exceptions.
- R5: Manual timestamp-based polling loops (while time.time() - start < timeout).

Exclusions:
- Standalone fixed delays (time.sleep(5), page.waitForTimeout(5000), cy.wait(5000)) -> AP01 only.
- Normal test fixtures, setup/teardown hooks, and test parameters.
- Built-in framework retry configuration (e.g. @pytest.mark.flaky, retries: 2).
- Normal data-driven test loops (for item in items: ...).
- Isolated test data generation (e.g. unique username with uuid.uuid4()).
"""

import ast
import re
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

# Retry identifier keywords indicating a retry counter or attempt loop
_RETRY_KEYWORDS = {
    "retry",
    "retries",
    "attempt",
    "attempts",
    "max_attempts",
    "max_retries",
    "retry_count",
    "try_count",
    "retry_limit",
}

# Regex for manual timestamp polling in JS/TS (handles multiline while conditions)
_JS_TIMING_POLLING = re.compile(
    r"""\bwhile\s*\([^)]*?(?:Date\.now\(\)|performance\.now\(\)|\+new Date\(\)|Date\.parse\(\)|startTime|start_time|start)[^)]*?<[^)]*?\)""",
    re.IGNORECASE | re.DOTALL,
)

# Regex for JS/TS random in assertions or control flow
_JS_RANDOM_FLOW = re.compile(
    r"""\bif\s*\([^)]*Math\.random\(\)[^)]*\)"""
    r"""|\bexpect\s*\([^)]*\)\s*\.\s*(?:toBe|toEqual|toStrictEqual|to\.(?:equal|be))\s*\([^)]*Math\.random\(\)""",
    re.IGNORECASE,
)

# Regex for JS/TS retry loops around browser actions with try/catch
_JS_RETRY_LOOP = re.compile(
    r"""(?:for|while)\s*\([^)]*?(?:retries|attempt|retry|max_retries|max_attempts)[^)]*?\)\s*\{[^}]*?try\s*\{[^}]*?(?:page\.|cy\.|driver\.)[^}]*?\}\s*catch""",
    re.IGNORECASE | re.DOTALL,
)


def _is_retry_loop_name(name_or_code: str) -> bool:
    """Checks whether a loop variable or expression indicates a retry mechanism."""
    cleaned = name_or_code.lower()
    return any(k in cleaned for k in _RETRY_KEYWORDS)


# --- Python AST Analysis ---

class _PythonFlakyVisitor(ast.NodeVisitor):
    """AST visitor to detect AP10 flaky patterns in Python scripts."""

    def __init__(self, raw_lines: list[str], framework: Framework, tree: ast.AST) -> None:
        self.raw_lines = raw_lines
        self.framework = framework
        self.tree = tree
        self.findings: list[Finding] = []
        self.seen_lines: set[int] = set()

    def _add_finding(
        self,
        line_start: int,
        line_end: int,
        reason: str,
        confidence: Confidence = Confidence.MEDIUM,
    ) -> None:
        if line_start in self.seen_lines:
            return
        self.seen_lines.add(line_start)
        snippet = "\n".join(self.raw_lines[line_start - 1 : line_end]).strip()
        self.findings.append(
            Finding(
                id=f"AP10-L{line_start}",
                anti_pattern_id="AP10",
                anti_pattern_name="Potentially Flaky Patterns",
                severity=Severity.MEDIUM,
                confidence=confidence,
                line_start=line_start,
                line_end=line_end,
                code_snippet=snippet,
                reason=reason,
                explanation="",
                suggested_fix="",
            )
        )

    def visit_For(self, node: ast.For) -> None:
        self._check_retry_loop(node)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        # Check R5: Manual timestamp-based polling loop
        test_str = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
        if "time.time()" in test_str or "time.monotonic()" in test_str or "perf_counter()" in test_str:
            self._add_finding(
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                reason="Manual timestamp-based polling loop detected instead of framework-native synchronization.",
                confidence=Confidence.MEDIUM,
            )
        self._check_retry_loop(node)
        self.generic_visit(node)

    def _check_retry_loop(self, loop_node: ast.For | ast.While) -> None:
        """R4: Detect manual retry loops wrapping browser actions with try/except."""
        loop_header = ast.unparse(loop_node.target) if isinstance(loop_node, ast.For) and hasattr(ast, "unparse") else (
            ast.unparse(loop_node.test) if isinstance(loop_node, ast.While) and hasattr(ast, "unparse") else ""
        )
        if not _is_retry_loop_name(loop_header):
            return

        has_try_except = False
        has_browser_action = False

        for stmt in loop_node.body:
            if isinstance(stmt, ast.Try):
                has_try_except = True
                try_str = ast.unparse(stmt) if hasattr(ast, "unparse") else ""
                if any(
                    kw in try_str
                    for kw in ("driver.", "page.", ".click(", ".send_keys(", ".fill(", "find_element")
                ):
                    has_browser_action = True

        if has_try_except and has_browser_action:
            self._add_finding(
                line_start=loop_node.lineno,
                line_end=getattr(loop_node, "end_lineno", loop_node.lineno),
                reason="Manual retry loop around browser action detected, which may mask underlying timing or stability failures.",
                confidence=Confidence.MEDIUM,
            )

    def visit_If(self, node: ast.If) -> None:
        # R2: Randomness in conditional control flow within test
        test_str = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
        if any(kw in test_str for kw in ("random.random()", "random.randint(", "random.choice(", "random.sample(")):
            self._add_finding(
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                reason="Uncontrolled randomness in test conditional flow creates non-deterministic execution paths.",
                confidence=Confidence.MEDIUM,
            )
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        # R2: Randomness in assertions
        test_str = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
        if any(kw in test_str for kw in ("random.choice", "random.randint", "random.random()", "random.sample")):
            self._add_finding(
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                reason="Uncontrolled randomness used in assertion creates non-deterministic test expectations.",
                confidence=Confidence.MEDIUM,
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_unsynchronized_navigation(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_unsynchronized_navigation(node)
        self.generic_visit(node)

    def _check_unsynchronized_navigation(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """R1: Detect Selenium navigation followed by element interaction without synchronization."""
        if self.framework != Framework.SELENIUM:
            return

        body = func_node.body
        n = len(body)
        for i in range(n):
            stmt = body[i]
            stmt_code = ast.unparse(stmt) if hasattr(ast, "unparse") else ""

            if "driver.get(" in stmt_code or "driver.navigate" in stmt_code:
                # Walk subsequent statements until a browser interaction or synchronization is encountered
                for j in range(i + 1, n):
                    next_stmt = body[j]
                    next_code = ast.unparse(next_stmt) if hasattr(ast, "unparse") else ""

                    # If an explicit synchronization or wait is encountered, it is synchronized!
                    if any(w in next_code for w in ("WebDriverWait", "expected_conditions", "wait.until", "time.sleep", "wait_for_")):
                        break

                    # If browser element interaction is reached without synchronization -> flag R1
                    if any(action in next_code for action in (".click()", ".send_keys(", ".clear()", ".submit()")):
                        self._add_finding(
                            line_start=next_stmt.lineno,
                            line_end=getattr(next_stmt, "end_lineno", next_stmt.lineno),
                            reason="Unsynchronized browser interaction immediately following navigation without explicit synchronization.",
                            confidence=Confidence.LOW,
                        )
                        break

    def check_module_shared_state(self) -> None:
        """R3: Detect global mutable state written in one test function and read in another."""
        test_functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Exclude fixtures and setup/teardown methods
                name_lower = node.name.lower()
                if any(name_lower.startswith(p) for p in ("setup", "teardown", "fixture", "before", "after")):
                    continue
                # Exclude decorator fixtures
                is_fixture = False
                for dec in getattr(node, "decorator_list", []):
                    dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
                    if "fixture" in dec_str:
                        is_fixture = True
                        break
                if not is_fixture:
                    test_functions.append(node)

        if len(test_functions) < 2:
            return

        # Track which variables are modified (via global statement or module-level reassignment)
        # and read across different test functions
        written_globals: dict[str, int] = {}  # var_name -> line_num of first write
        read_globals: dict[str, int] = {}     # var_name -> line_num of first read

        for func in test_functions:
            func_name = func.name
            func_written = set()

            for subnode in ast.walk(func):
                if isinstance(subnode, ast.Global):
                    for name in subnode.names:
                        if not name.isupper():  # Ignore UPPER_CASE constants
                            func_written.add(name)
                            if name not in written_globals:
                                written_globals[name] = subnode.lineno

                elif isinstance(subnode, ast.Name) and isinstance(subnode.ctx, ast.Store):
                    if subnode.id in written_globals and subnode.id not in func_written:
                        func_written.add(subnode.id)

                elif isinstance(subnode, ast.Name) and isinstance(subnode.ctx, ast.Load):
                    name = subnode.id
                    if name in written_globals and name not in func_written:
                        if name not in read_globals:
                            read_globals[name] = subnode.lineno

        for var_name, read_line in read_globals.items():
            write_line = written_globals[var_name]
            self._add_finding(
                line_start=read_line,
                line_end=read_line,
                reason=f"Test depends on shared mutable state '{var_name}' written in another test (line {write_line}), introducing test-order dependency.",
                confidence=Confidence.MEDIUM,
            )


# --- JavaScript / TypeScript Scanner ---

def _analyze_js_script(
    script_content: str,
    framework: Framework,
    language: Language,
) -> list[Finding]:
    """Analyzes JS/TS scripts for AP10 flaky patterns."""
    findings: list[Finding] = []
    raw_lines = script_content.splitlines()
    seen_lines: set[int] = set()

    # R2: Random in test condition or expect
    for idx, raw_line in enumerate(raw_lines):
        line_num = idx + 1
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        if _JS_RANDOM_FLOW.search(stripped):
            if line_num not in seen_lines:
                seen_lines.add(line_num)
                findings.append(
                    Finding(
                        id=f"AP10-L{line_num}",
                        anti_pattern_id="AP10",
                        anti_pattern_name="Potentially Flaky Patterns",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                        reason="Uncontrolled randomness in test assertion or control flow creates non-deterministic behavior.",
                        explanation="",
                        suggested_fix="",
                    )
                )

    # R5: Manual timestamp polling in JS/TS (multiline support)
    for match in _JS_TIMING_POLLING.finditer(script_content):
        match_start = match.start()
        line_start = script_content.count("\n", 0, match_start) + 1
        if line_start not in seen_lines:
            seen_lines.add(line_start)
            match_lines = match.group(0).splitlines()
            snippet = match_lines[0].strip()
            findings.append(
                Finding(
                    id=f"AP10-L{line_start}",
                    anti_pattern_id="AP10",
                    anti_pattern_name="Potentially Flaky Patterns",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    line_start=line_start,
                    line_end=line_start + len(match_lines) - 1,
                    code_snippet=snippet,
                    reason="Manual timing/timestamp polling loop detected instead of framework-native waiting.",
                    explanation="",
                    suggested_fix="",
                )
            )

    # R4: Multiline JS manual retry loops
    for match in _JS_RETRY_LOOP.finditer(script_content):
        match_start = match.start()
        line_start = script_content.count("\n", 0, match_start) + 1
        if line_start not in seen_lines:
            seen_lines.add(line_start)
            match_lines = match.group(0).splitlines()
            snippet = "\n".join(match_lines[:3]).strip()
            findings.append(
                Finding(
                    id=f"AP10-L{line_start}",
                    anti_pattern_id="AP10",
                    anti_pattern_name="Potentially Flaky Patterns",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    line_start=line_start,
                    line_end=line_start + len(match_lines) - 1,
                    code_snippet=snippet,
                    reason="Manual retry loop around browser action detected, which may mask underlying timing or stability failures.",
                    explanation="",
                    suggested_fix="",
                )
            )

    # R3: JS/TS shared mutable state written in one test and read in another
    # Look for top-level `let sharedVar;` that is written in test 1 and read in test 2
    top_level_vars = re.findall(r"^(?:let|var)\s+([a-zA-Z0-9_$]+)\s*(?:=\s*null|;\s*$|;)", script_content, re.MULTILINE)
    test_blocks = list(re.finditer(r"""\b(?:it|test)\s*\(\s*['"`](.*?)['"`]\s*,\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_$,\s{}():]+)?\s*=>\s*\{([^}]*)\}""", script_content, re.DOTALL))

    if len(test_blocks) >= 2:
        for var_name in top_level_vars:
            if var_name.isupper():
                continue  # Constants
            first_write_test_idx = None
            first_read_test_idx = None
            read_match_pos = None

            for t_idx, t_match in enumerate(test_blocks):
                body = t_match.group(2)
                # Check for write: var_name = ...
                if re.search(rf"\b{var_name}\s*=", body) and first_write_test_idx is None:
                    first_write_test_idx = t_idx
                # Check for read: expect(var_name), cy.wrap(var_name), or using var_name
                elif re.search(rf"\b{var_name}\b", body) and first_write_test_idx is not None and t_idx > first_write_test_idx:
                    first_read_test_idx = t_idx
                    read_match_pos = t_match.start()
                    break

            if first_read_test_idx is not None and read_match_pos is not None:
                line_start = script_content.count("\n", 0, read_match_pos) + 1
                if line_start not in seen_lines:
                    seen_lines.add(line_start)
                    findings.append(
                        Finding(
                            id=f"AP10-L{line_start}",
                            anti_pattern_id="AP10",
                            anti_pattern_name="Potentially Flaky Patterns",
                            severity=Severity.MEDIUM,
                            confidence=Confidence.MEDIUM,
                            line_start=line_start,
                            line_end=line_start,
                            code_snippet=f"let {var_name}",
                            reason=f"Test block depends on shared mutable state '{var_name}' modified by a preceding test, introducing test-order dependency.",
                            explanation="",
                            suggested_fix="",
                        )
                    )

    return findings


def detect_ap10(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP10 (Potentially Flaky Patterns) in the provided automation script.

    Identifies unsynchronized post-navigation interactions, uncontrolled randomness,
    test-order dependencies, manual retry loops, and timestamp polling.

    Returns:
        List of Finding objects with severity MEDIUM and confidence LOW/MEDIUM.
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

        visitor = _PythonFlakyVisitor(raw_lines, parsed_framework, tree)
        visitor.visit(tree)
        visitor.check_module_shared_state()
        findings = visitor.findings
    else:
        findings = _analyze_js_script(script_content, parsed_framework, parsed_language)

    findings.sort(key=lambda f: (f.line_start, f.line_end))
    seen_lines = set()
    unique_findings = []
    for f in findings:
        if f.line_start not in seen_lines:
            seen_lines.add(f.line_start)
            unique_findings.append(f)

    return unique_findings
