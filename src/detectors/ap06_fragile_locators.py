"""
AP06 — Fragile Locators Detector.

Performs static analysis to detect fragile locator strategies that depend heavily
on DOM structure, positional relationships, or dynamic/generated class names.

Approved Signals:
1. Absolute XPath: begins with /html or /body (Confidence: HIGH)
2. Positional Selectors: uses :nth-child(...) or :nth-of-type(...) (Confidence: HIGH)
3. Deep XPath: 4+ structural hierarchy levels (Confidence: MEDIUM)
4. Deep CSS Selectors: 4+ descendant/child relationships (Confidence: MEDIUM)
5. Generated/Dynamic Class Names: CSS-in-JS hashes like css-abc123, sc-aXZ123 (Confidence: MEDIUM)

Exclusions:
- Stable selectors: #id, [name="..."], [data-testid="..."], [data-cy="..."]
- Semantic locators: get_by_role, get_by_label, get_by_text, contains
- Shallow CSS/XPath (e.g. //button[@id='btn'], div > button)
- Normal meaningful CSS classes (.btn-primary, .card, .nav-item)
- Strings not used as locators (URLs, messages, test data)
"""

import re
from src.models import Confidence, Finding, Framework, Language, Severity
from src.validation.validator import validate_framework_and_language

# Recognizable locator contexts across frameworks:
# Selenium:
#   driver.find_element(By.XPATH, "...")
#   driver.find_elements(By.CSS_SELECTOR, "...")
#   driver.find_element_by_xpath("...")
#   driver.find_element_by_css_selector("...")
_SELENIUM_LOCATOR_CALLS = re.compile(
    r"""\bfind_element(?:s)?(?:_by_[a-z_]+)?\s*\(\s*(?:(?:by\s*=\s*)?By\.[A-Z_]+,\s*(?:value\s*=\s*)?|(?:by\s*=\s*)?['"][a-zA-Z\s_-]+['"],\s*(?:value\s*=\s*)?|(?:value\s*=\s*)?)?(?:"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)')"""
)

# Playwright:
#   page.locator("..."), locator("..."), page.$("..."), page.$$("..."),
#   page.waitForSelector("..."), page.wait_for_selector("...")
#   Excludes get_by_role, get_by_label, get_by_text, get_by_placeholder, etc.
_PLAYWRIGHT_LOCATOR_CALLS = re.compile(
    r"""(?:\bpage|\bframe|\bcontext)?\.(?:locator|\$|\$\$|waitForSelector|wait_for_selector)\s*\(\s*(?:"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)')"""
)

# Cypress:
#   cy.get("..."), cy.find("..."), .find("...")
_CYPRESS_LOCATOR_CALLS = re.compile(
    r"""\b(?:cy\.)?(?:get|find)\s*\(\s*(?:"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)')"""
)

# Signal 1: Absolute XPath (/html/..., /body/...)
_ABSOLUTE_XPATH_PATTERN = re.compile(r"^/(?:html|body)(?:/|$)", re.IGNORECASE)

# Signal 2: Positional Selectors (:nth-child(...), :nth-of-type(...))
_POSITIONAL_SELECTOR_PATTERN = re.compile(r":nth-(?:child|of-type)\s*\(", re.IGNORECASE)


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


def _strip_inline_comment(line: str, language: Language) -> str:
    """Strips inline comments."""
    if language == Language.PYTHON:
        idx = line.find("#")
        return line[:idx] if idx != -1 else line
    idx = line.find("//")
    while idx != -1:
        if idx > 0 and line[idx - 1] == ":":
            idx = line.find("//", idx + 2)
        else:
            return line[:idx]
    return line


def _is_deep_xpath(selector: str) -> bool:
    """
    Checks if an XPath contains 4 or more structural hierarchy levels.
    e.g. //div/div/div/button has 4 levels.
    Attribute predicates (e.g. [@id='btn']) are stripped and do not count as hierarchy levels.
    """
    if not (selector.startswith("/") or selector.startswith(".//")):
        return False
    # Remove attribute predicates to only count structural steps
    clean_xpath = re.sub(r"\[[^\]]*\]", "", selector)
    # Split by / or //
    parts = [p.strip() for p in re.split(r"/+", clean_xpath) if p.strip() and p.strip() != "."]
    return len(parts) >= 4


def _is_deep_css(selector: str) -> bool:
    """
    Checks if a CSS selector contains 4 or more descendant/child relationships.
    e.g. div > div > section > div > button has 4 relationships.
    """
    # Check each comma-separated selector group independently
    sub_selectors = selector.split(",")
    for sub in sub_selectors:
        sub = sub.strip()
        if not sub:
            continue
        # Strip attributes and pseudo arguments to avoid spaces inside them counting as combinators
        clean_css = re.sub(r"\[[^\]]*\]|\([^\)]*\)", "", sub).strip()
        # Direct child combinator count
        if clean_css.count(">") >= 4:
            return True
        # Descendant / child relationship count (tokens separated by >, +, ~, or space)
        tokens = re.split(r"\s*[>+~]\s*|\s+", clean_css)
        tokens = [t for t in tokens if t and t not in (">", "+", "~")]
        if len(tokens) >= 5:
            return True
    return False


def _is_generated_class(selector: str) -> bool:
    """
    Conservative heuristic to detect dynamic/auto-generated CSS class names.
    e.g. .css-abc123, .sc-aXZ123, .header-7f8a9b
    Does NOT flag normal meaningful classes such as .btn-primary, .card, .nav-item, .col-md-6.
    """
    # 1. Emotion / Styled-system (.css-xxxx)
    if re.search(r"(?:\.|\b)css-[a-zA-Z0-9]{5,}", selector):
        return True
    # 2. Styled-components (.sc-xxxx)
    if re.search(r"(?:\.|\b)sc-[a-zA-Z0-9]{5,}", selector):
        return True
    # 3. Dynamic classes with generated hashes (contains both letters and digits, length >= 6)
    for token in re.findall(r"\.([a-zA-Z0-9_-]+)", selector):
        parts = re.split(r"[_-]{1,2}", token)
        if len(parts) >= 2:
            suffix = parts[-1]
            if len(suffix) >= 6 and re.search(r"[0-9]", suffix) and re.search(r"[a-zA-Z]", suffix):
                return True
    return False


def _analyze_selector(selector: str) -> tuple[bool, Confidence, str] | None:
    """
    Analyzes a locator string for fragility signals.
    Returns (is_fragile, confidence, reason) or None if selector is clean/stable.
    """
    sel = selector.strip()
    if not sel:
        return None

    # Exclude stable identifiers
    # Simple ID selector: #login (not deep or combined)
    if sel.startswith("#") and not any(ch in sel for ch in (">", " ", ":", "+", "~")):
        return None
    # Attribute-based stable identifiers: [name="username"], [data-testid="..."], [data-cy="..."]
    if (
        (sel.startswith("[name=") or sel.startswith("[data-testid=") or sel.startswith("[data-cy="))
        and not any(ch in sel for ch in (">", ":"))
    ):
        return None

    # Signal 1: Absolute XPath (High confidence)
    if _ABSOLUTE_XPATH_PATTERN.search(sel):
        return (
            True,
            Confidence.HIGH,
            f"Locator uses an absolute XPath starting from document root ('{sel}'), which breaks easily with layout changes.",
        )

    # Signal 2: Positional selectors (High confidence)
    if _POSITIONAL_SELECTOR_PATTERN.search(sel):
        return (
            True,
            Confidence.HIGH,
            f"Locator relies on positional pseudo-class indexing ('{sel}'), which easily breaks when siblings change.",
        )

    # Signal 3: Deep XPath (Medium confidence)
    if _is_deep_xpath(sel):
        return (
            True,
            Confidence.MEDIUM,
            f"Locator uses a deeply nested XPath with 4+ structural levels ('{sel}'), making it fragile to layout shifts.",
        )

    # Signal 4: Deep CSS Selector (Medium confidence)
    if _is_deep_css(sel):
        return (
            True,
            Confidence.MEDIUM,
            f"Locator uses a deeply nested CSS hierarchy ('{sel}'), creating tight coupling to DOM structure.",
        )

    # Signal 5: Generated/Dynamic CSS class names (Medium confidence)
    if _is_generated_class(sel):
        return (
            True,
            Confidence.MEDIUM,
            f"Locator targets an apparent auto-generated or dynamic class name ('{sel}'), which typically changes across builds.",
        )

    return None


def detect_ap06(
    script_content: str,
    framework: Framework | str,
    language: Language | str,
) -> list[Finding]:
    """
    Detects AP06 (Fragile Locators) in the provided script content.

    Flags locator strategies dependent on absolute/deep paths, positional indexing,
    or auto-generated CSS classes.

    Returns:
        List of Finding objects with severity MEDIUM and appropriate confidence.
    """
    if not script_content or not script_content.strip():
        return []

    validation = validate_framework_and_language(framework, language)
    if not validation.is_valid:
        return []

    parsed_framework = (
        framework
        if isinstance(framework, Framework)
        else next((f for f in Framework if f.value == str(framework).lower()), None)
    )
    parsed_language = (
        language
        if isinstance(language, Language)
        else next((l for l in Language if l.value == str(language).lower()), None)
    )

    if parsed_framework is None or parsed_language is None:
        return []

    findings: list[Finding] = []
    lines = script_content.splitlines()

    for line_num, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or _is_comment_line(stripped, parsed_language):
            continue

        code_line = _strip_inline_comment(raw_line, parsed_language).strip()
        if not code_line:
            continue

        # Extract locators based on framework context
        selectors: list[str] = []
        if parsed_framework == Framework.SELENIUM:
            for m in _SELENIUM_LOCATOR_CALLS.finditer(code_line):
                sel = m.group(1) if m.group(1) is not None else m.group(2)
                if sel:
                    selectors.append(sel)
        elif parsed_framework == Framework.PLAYWRIGHT:
            for m in _PLAYWRIGHT_LOCATOR_CALLS.finditer(code_line):
                sel = m.group(1) if m.group(1) is not None else m.group(2)
                if sel:
                    selectors.append(sel)
        elif parsed_framework == Framework.CYPRESS:
            for m in _CYPRESS_LOCATOR_CALLS.finditer(code_line):
                sel = m.group(1) if m.group(1) is not None else m.group(2)
                if sel:
                    selectors.append(sel)

        # Check extracted selectors
        for sel in selectors:
            analysis = _analyze_selector(sel)
            if analysis is not None:
                _, confidence, reason = analysis
                findings.append(
                    Finding(
                        id=f"AP06-L{line_num}",
                        anti_pattern_id="AP06",
                        anti_pattern_name="Fragile Locators",
                        severity=Severity.MEDIUM,
                        confidence=confidence,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                        reason=reason,
                    )
                )
                # Avoid generating multiple findings for the same line
                break

    findings.sort(key=lambda f: (f.line_start, f.line_end))
    return findings
