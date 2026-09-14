# Automation Script Quality Auditor — Anti-Pattern Checklist

## Purpose

Define the fixed v1 anti-pattern checklist that the auditor will use when statically analyzing Selenium, Playwright, and Cypress automation scripts.

The auditor performs static analysis only. It does not execute scripts, launch browsers, connect to websites, or run test runners.

Gemini must NOT decide whether an anti-pattern exists. Detection is performed by deterministic/static-analysis rules. Gemini is used later only to generate a short explanation and suggested fix for detected issues.

---

## Supported Frameworks

| Framework  | Languages                      |
| ---------- | ------------------------------ |
| Selenium   | Python                         |
| Playwright | Python, JavaScript, TypeScript |
| Cypress    | JavaScript, TypeScript         |

---

# AP01 — Hardcoded Waits

### Definition

A fixed amount of time is used instead of waiting for a specific application condition or event.

### Detection Rules

* Selenium/Python: `time.sleep(number)`
* Playwright/Python: `time.sleep(number)`
* Playwright/Python: `page.wait_for_timeout(number)`
* Playwright/JavaScript/TypeScript: `page.waitForTimeout(number)`
* Cypress/JavaScript/TypeScript: `cy.wait(number)`

### Do Not Flag

* Selenium condition-based waits such as `WebDriverWait(...).until(...)`
* Cypress alias waits such as `cy.wait('@alias')`
* Other condition/state-based synchronization

### Severity

High

### Confidence

High when an exact supported pattern is detected.

### Detection

Deterministic/static.

### Example

```python
time.sleep(5)
```

Finding:

* Anti-pattern: AP01 — Hardcoded Wait
* Line: line containing the wait
* Reason: Fixed delay is used instead of waiting for a specific application condition.
* Suggested fix: Generated later by Gemini.

---

# AP02 — Magic Numbers / Hardcoded Values

### Definition

A numeric value is used directly in logic without meaningful context or explanation.

### Detection Rules

Potentially flag:

* Numeric loop limits with unclear meaning
* Numeric indexes/positions with unclear meaning
* Unexplained numeric thresholds
* Repeated unexplained numeric values
* Configuration-like numeric values

### Do Not Flag

Do not blindly flag every number.

Examples that should generally not be flagged:

```python
if count == 0:
```

```python
assert response.status_code == 200
```

Normal test data such as:

```python
age = 25
```

Hardcoded waits such as:

```python
time.sleep(5)
```

These belong to AP01.

### Detection

Heuristic/static analysis.

The analyzer should consider surrounding context and exclude obvious legitimate values.

### Severity

Medium

### Confidence

Medium.

### Example

```python
for i in range(3):
    submit_form()
```

Potential finding:

* Anti-pattern: AP02 — Magic Number
* Line: line containing the numeric value
* Reason: Loop uses an unexplained numeric limit.
* Suggested fix: Generated later by Gemini.

---

# AP03 — Copy-Paste / Duplicated Code

### Definition

The same or highly similar block of meaningful automation code is repeated within a script.

### Detection Rules

* Detect repeated sequences of multiple statements.
* Detect identical or highly similar browser interaction blocks.
* Use normalization for insignificant whitespace, indentation, and comments.
* For v1, a duplicate block should contain at least 3 consecutive meaningful statements.
* Report both locations of the duplicated blocks.

### Do Not Flag

* A single repeated statement
* Common imports
* Common setup statements
* Unrelated code that happens to contain similar individual actions
* Duplication across different files in v1

### Detection

Static code similarity analysis.

### Severity

Medium

### Confidence

High for exact duplicates; Medium for highly similar blocks.

### Example

If lines 12–15 and 28–31 contain essentially the same multi-statement browser interaction sequence:

Finding:

* Anti-pattern: AP03 — Duplicated Code
* Lines: 12–15 and 28–31
* Reason: Same browser interaction sequence is implemented twice.
* Suggested fix: Extract the repeated workflow into a reusable function/helper.

---

# AP04 — Poor Test Structure

### Definition

A test is structured in a way that makes it unnecessarily difficult to understand, maintain, or isolate failures.

### Detection Rules

Use conservative measurable heuristics:

* Test function/spec with 30+ statements → potential large test.
* Nesting depth of 4 or more → potential excessive nesting.
* Multiple clearly distinct workflows within one test → potential poor structure.
* Large amounts of setup mixed directly into the test flow → potential poor structure.

### Important Limitation

Length alone does not prove poor structure.

A long but logically coherent test should not automatically be considered an anti-pattern.

### Detection

Heuristic/static analysis.

### Severity

Medium

### Confidence

Medium.

### Example

A single test containing login, search, checkout, profile management, and logout may be flagged as potentially containing multiple unrelated workflows.

Finding:

* Anti-pattern: AP04 — Poor Test Structure
* Reason: Test combines multiple workflows, making failures harder to isolate.
* Suggested fix: Split the workflow into smaller focused test cases.

---

# AP05 — Missing Abstractions

### Definition

A reusable logical browser workflow is repeated in multiple locations instead of being represented by a helper/function/page-object method.

### Detection Rules

* Repeated multi-statement browser workflows
* Repeated setup/action patterns representing one logical operation
* Repeated workflows already identified through AP03
* Strong evidence that repeated code represents one reusable operation

### Do Not Flag

* One-off workflows
* Single repeated browser actions
* Arbitrary code that could theoretically be extracted
* Code where abstraction would make the test less clear

### Important Relationship With AP03

AP03 identifies the duplication.

AP05 identifies the likely missing reusable abstraction.

AP05 should NOT automatically trigger for every AP03 finding. There should be evidence that the duplicated code represents a meaningful logical workflow.

### Detection

Heuristic/static analysis using duplication results where appropriate.

### Severity

Medium

### Confidence

Medium–High when the logical workflow is clear.

### Example

Repeated login sequence:

```python
page.fill("#username", username)
page.fill("#password", password)
page.click("#login")
```

Finding:

* Anti-pattern: AP05 — Missing Abstraction
* Lines: both repeated workflow locations
* Reason: Same multi-step login workflow is implemented in multiple locations.
* Suggested fix: Extract the workflow into a reusable helper or page-object method.

---

# AP06 — Fragile Locators

### Definition

A locator relies heavily on UI structure, positional information, or likely dynamic values that are likely to change.

### Detection Rules

Potentially flag:

* Absolute XPath beginning with `/html` or `/body`
* Very deeply nested XPath selectors
* Very deeply nested CSS selectors
* Positional selectors such as `nth-child()`
* Locators using clearly generated/dynamic CSS class names
* Locators heavily dependent on DOM hierarchy

### Initial Thresholds

* XPath with 4+ hierarchical levels → potential concern
* CSS with 4+ descendant/child relationships → potential concern
* `nth-child()` / positional selection → potential concern

### Do Not Flag

Preferably stable selectors such as:

* IDs
* Names
* Test IDs
* Accessible roles
* Meaningful stable attributes

Examples:

```python
By.ID, "login-button"
```

```python
page.get_by_role("button", name="Login")
```

```python
page.get_by_test_id("login-button")
```

```javascript
cy.get("[data-testid='login-button']")
```

Do not assume every XPath is fragile.

### Detection

Framework-aware static pattern analysis.

### Severity

Medium

### Confidence

Medium–High depending on the pattern.

### Example

```python
driver.find_element(
    By.XPATH,
    "/html/body/div[2]/div[1]/div[3]/button"
)
```

Finding:

* Anti-pattern: AP06 — Fragile Locator
* Reason: Locator depends heavily on DOM structure.
* Suggested fix: Prefer a stable test ID, accessible role, ID, or meaningful attribute.

---

# AP07 — Missing Assertions

### Definition

A test performs meaningful browser/test actions but contains no recognizable verification of the expected result.

### Detection Rules

Recognize test boundaries and assertion mechanisms for the supported frameworks.

#### Selenium/Python

Recognize normal Python assertions and supported verification patterns such as:

```python
assert ...
```

#### Playwright

Recognize Playwright assertion patterns such as:

```python
expect(...)
```

and JavaScript/TypeScript equivalents.

#### Cypress

Recognize verification patterns such as:

```javascript
.should(...)
```

```javascript
.and(...)
```

and other explicitly supported assertion patterns.

### Do Not Flag

* Setup/helper functions
* Tests containing recognized assertions
* Tests that clearly call a recognized verification helper
* Unknown/custom functions should not automatically be considered missing assertions

### Important Limitation

Absence of a recognized assertion does not prove that no assertion exists.

When verification is unclear, prefer not to flag.

### Detection

Framework-aware static analysis.

### Severity

High

### Confidence

High when test boundaries and assertion patterns are clear.

### Example

A login test performs username entry, password entry, and clicking Login but contains no recognizable verification.

Finding:

* Anti-pattern: AP07 — Missing Assertion
* Reason: Test performs browser actions without recognizable verification of the expected result.
* Suggested fix: Add an assertion that verifies the expected application state.

---

# AP08 — Testing Implementation Details

### Definition

The test verifies internal application implementation rather than observable behavior.

### Detection Rules

Conservatively detect:

* Assertions/verifications of internal application method calls
* Direct testing of application internals
* Assertions against internal implementation state
* Mocking internal application methods when used as the primary verification

### Do Not Flag

* Assertions of user-visible behavior
* Normal framework APIs
* Legitimate API/network-level verification
* Mocking used only for legitimate test isolation
* Every occurrence of a mock

### Important Limitation

The analyzer cannot fully understand an application's architecture from the test script alone.

Only clear recognizable patterns should be flagged.

When uncertain, do not flag.

### Detection

Framework/language-aware heuristic analysis.

### Severity

Medium

### Confidence

Medium.

### Example

```python
mock_authenticate.assert_called_once()
```

Finding:

* Anti-pattern: AP08 — Testing Implementation Details
* Reason: Test verifies an internal method call rather than observable behavior.
* Suggested fix: Prefer asserting the observable outcome.

---

# AP09 — Hardcoded Secrets

### Definition

Credentials or secret values are directly embedded in the automation script.

### Detection Rules

Use variable-name/context heuristics and recognizable secret formats.

Suspicious names include:

* password
* passwd
* pwd
* api_key
* apikey
* secret
* access_token
* refresh_token
* auth_token
* bearer_token
* client_secret
* private_key

Detect likely hardcoded secret/token values where evidence is strong.

### Do Not Flag

Environment/configuration retrieval such as:

```python
password = os.getenv("TEST_PASSWORD")
```

```python
api_key = config["API_KEY"]
```

```javascript
const token = Cypress.env("TOKEN");
```

Do not automatically flag ordinary test data.

### Critical Security Rule

If a secret is detected:

**NEVER send the actual secret value to Gemini.**

Redact it first:

```text
[REDACTED]
```

### Detection

Pattern + heuristic analysis.

### Severity

High

### Confidence

High when the secret pattern is clear.

### Example

```python
password = "SuperSecret123!"
```

Finding:

* Anti-pattern: AP09 — Hardcoded Secret
* Reason: Credential appears to be embedded directly in source code.
* Suggested fix: Store credential in an environment variable or secure configuration.

---

# AP10 — Potentially Flaky Patterns

### Definition

A recognizable coding pattern that may cause inconsistent test behavior.

This rule must remain conservative.

### Detection Rules

#### AP10-R1 — Unsynchronized interaction

Potentially flag interactions immediately following navigation when there is no recognizable synchronization or state check.

Do not flag when an appropriate condition-based synchronization is present.

#### AP10-R2 — Uncontrolled randomness

Potentially flag random test data when it affects expected results or makes verification unpredictable.

Do not flag harmless or intentionally isolated randomness.

#### AP10-R3 — Test-order dependency

Potentially flag clear dependencies where one test relies on state created by another test.

Do not assume every shared helper or fixture creates an order dependency.

#### AP10-R4 — Retry logic hiding failures

Potentially flag manual/repeated retry logic that catches failures and retries without addressing the underlying condition.

Do not automatically flag legitimate framework retry configuration.

#### AP10-R5 — Timing-sensitive patterns

Potentially flag concrete timing-sensitive polling or manual timing logic not already covered by AP01.

### AP01 Exclusion

Do NOT duplicate AP01 findings.

For example:

```python
time.sleep(5)
```

is AP01 only.

It should not also produce AP10.

### Detection

Heuristic/static analysis.

### Severity

Medium

### Confidence

Low–Medium.

### Important Limitation

If the analyzer cannot confidently identify a concrete flaky pattern, it should NOT create an AP10 finding.

### Example

A test performs an interaction immediately after navigation with no recognizable synchronization.

Finding:

* Anti-pattern: AP10 — Potentially Flaky Pattern
* Reason: Interaction may occur before the application is ready.
* Suggested fix: Synchronize with a specific application state or condition.

---

# Cross-Cutting Implementation Rules

## 1. Static Analysis Only

The auditor must never:

* Execute submitted automation scripts
* Launch a browser
* Connect to the tested website
* Run Selenium, Playwright, or Cypress
* Execute JavaScript from submitted scripts
* Run arbitrary user code

## 2. Rule-Based Detection

The anti-pattern detector is responsible for determining whether an issue exists.

Gemini must NOT determine:

* Whether an anti-pattern exists
* Whether a line should be flagged
* The final quality score

## 3. Gemini Responsibilities

For a confirmed finding, Gemini may generate:

1. A short explanation.
2. A concise suggested fix.

Gemini should generally receive:

* Anti-pattern type
* Framework
* Language
* Relevant code/line context

Secrets must be redacted before sending context to Gemini.

## 4. Line References

Every detected issue must contain the relevant source line number or line range.

For duplication, include both relevant ranges.

## 5. Avoid Duplicate Findings

The detector should avoid reporting the same underlying issue multiple times when two anti-patterns overlap.

Known example:

* `time.sleep(5)` → AP01, not AP02 or AP10.

AP03 and AP05 may both apply only when they represent genuinely distinct findings.

## 6. Conservative Detection

False positives should be minimized.

When a pattern is ambiguous, prefer:

**No finding**

over an unsupported claim that the code is an anti-pattern.

## 7. Severity Does Not Equal Final Score

Severity is metadata describing the potential impact of an issue.

The actual scoring formula will be defined separately in **T04 — Define Scoring System**.

Do not implement scoring logic in this document.

---

# Checklist Summary

| ID   | Anti-Pattern                     | Detection Type      | Severity | Confidence  |
| ---- | -------------------------------- | ------------------- | -------- | ----------- |
| AP01 | Hardcoded Waits                  | Deterministic       | High     | High        |
| AP02 | Magic Numbers / Hardcoded Values | Heuristic           | Medium   | Medium      |
| AP03 | Copy-Paste / Duplicated Code     | Static similarity   | Medium   | High/Medium |
| AP04 | Poor Test Structure              | Heuristic           | Medium   | Medium      |
| AP05 | Missing Abstractions             | Heuristic           | Medium   | Medium–High |
| AP06 | Fragile Locators                 | Framework-aware     | Medium   | Medium–High |
| AP07 | Missing Assertions               | Framework-aware     | High     | High        |
| AP08 | Testing Implementation Details   | Heuristic           | Medium   | Medium      |
| AP09 | Hardcoded Secrets                | Pattern + heuristic | High     | High        |
| AP10 | Potentially Flaky Patterns       | Heuristic           | Medium   | Low–Medium  |
