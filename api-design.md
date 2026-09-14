# Automation Script Quality Auditor — Gemini API Integration Design

**Project:** Automation Script Quality Auditor  
**STLC Phase:** Phase 2 — System & Software Design  
**Document Reference:** `api-design.md`  
**Status:** Authoritative API Design Specification  

---

## 1. Purpose

This document defines the architectural and operational design of the **Google Gemini API integration** within the Automation Script Quality Auditor.

In traditional static analysis tools, rule violations are often accompanied by generic, static error messages that fail to account for the unique context or modern idiomatic conventions of the framework in use. The Automation Script Quality Auditor integrates Gemini to solve this specific usability problem:

* **Contextual Explanations:** Provide a clear, human-understandable explanation of *why* an already-confirmed anti-pattern is problematic in the specific script context.
* **Actionable Suggested Fixes:** Provide a concise, tailored remediation snippet demonstrating modern, framework-compliant best practices (e.g., migrating a brittle XPath locator to a Playwright `getByRole` locator).

### Core Architectural Principle
> **Gemini is an advisory layer only.**

The auditor is built on a strict division of authority: **deterministic static analysis remains the single source of truth** for rule detection, line referencing, severity weighting, deduplication, and score calculation. Gemini operates downstream purely as an advisory enhancement service.

---

## 2. Design Principles

The Gemini API integration is governed by nine fundamental design principles:

1. **Deterministic Detection First:** Every finding must be discovered, classified, and confirmed by deterministic or heuristic rules before any AI call is initiated.
2. **Zero AI-Driven Detection:** Gemini does not scan scripts, discover anti-patterns, or flag violations.
3. **Immutable Severity:** Issue severity (`High` or `Medium`) is determined strictly by `anti-pattern-checklist.md` and cannot be modified by Gemini.
4. **Immutable Confidence:** Detection confidence (`High`, `Medium`, or `Low`) is set by detector heuristics and cannot be altered by Gemini.
5. **Score Isolation:** The quality score (0–100) is calculated mathematically prior to AI invocation; Gemini never calculates, influences, or modifies the score.
6. **Fixed Finding Count:** Gemini cannot invent new findings, hallucinate additional issues, or dismiss confirmed findings.
7. **Advisory Scope Only:** Gemini output is strictly confined to: (1) a short explanation, and (2) a concise suggested fix.
8. **Resilient Failure Shielding:** The deterministic audit remains fully usable even when Gemini enrichment is unavailable. Confirmed findings, line references, severity, confidence, and the quality score remain completely accessible.
9. **Simplicity Over Sophistication:** Consistent with a v1 student/learning application, the integration uses straightforward synchronous requests without multi-agent frameworks, vector databases, fine-tuning, or background task queues.

---

## 3. Gemini Responsibility Boundary

To maintain complete architectural integrity, the boundary between the internal auditor components and the external Gemini API is strictly enforced:

| Responsibility | Responsible Owner | Can Gemini Modify or Override? |
| :--- | :--- | :--- |
| **Anti-pattern detection** | Detection Engine (`src/detectors/`) | **NO** — Never evaluated by Gemini |
| **Finding normalization** | Finding Normalizer (`src/detectors/deduplication.py`) | **NO** — Managed purely by code |
| **Deduplication / overlap resolution** | Finding Normalizer (`src/detectors/deduplication.py`) | **NO** — Managed purely by code |
| **Severity assignment** | Checklist Rules (`anti-pattern-checklist.md`) | **NO** — Fixed specification |
| **Confidence assignment** | Detector Heuristics (`src/detectors/`) | **NO** — Fixed detector metadata |
| **Score calculation (0–100)** | Scoring Engine (`src/scoring/calculator.py`) | **NO** — Deterministic math only |
| **Rating band assignment** | Scoring Engine (`src/scoring/calculator.py`) | **NO** — Fixed mathematical bands |
| **Secret detection & redaction** | Redaction Layer (`src/gemini/redaction.py`) | **NO** — Redacted prior to AI call |
| **Finding explanation** | **Google Gemini API** (via `GeminiService`) | **YES** — Advisory generation |
| **Remediation / suggested fix** | **Google Gemini API** (via `GeminiService`) | **YES** — Advisory generation |
| **Final report compilation** | Report Generator (`src/reporting/builder.py`) | **NO** — Deterministic templating |

> [!IMPORTANT]
> **Authoritative Invariant:** Gemini output must **never** override, reclassify, or mutate deterministic findings, severity ratings, line numbers, or score results.

---

## 4. Request Data Contract

To maximize response relevance, minimize latency, and prevent accidental data exposure, the auditor sends **only focused context** for confirmed findings, rather than transmitting the entire script.

### 4.1 Request Payload Fields

For each confirmed finding requiring AI enrichment, the following data context is assembled:

```python
# Conceptual Outbound Request Context
{
    "framework": "playwright",            # "selenium" | "playwright" | "cypress"
    "language": "typescript",             # "python" | "javascript" | "typescript"
    "anti_pattern_id": "AP06",            # "AP01" through "AP10"
    "anti_pattern_title": "Fragile Locators",
    "severity": "Medium",                 # "High" | "Medium"
    "confidence": "High",                 # "High" | "Medium" | "Low"
    "detection_reason": "Positional selector and deep DOM hierarchy detected.",
    "line_range": "Line 24",              # Single line or range (e.g., "Lines 12-15")
    "code_snippet": "await page.locator('div > div:nth-child(2) > button').click();",
    "surrounding_context": ""             # Optional: 1-2 lines before/after if needed
}
```

### 4.2 Request Metadata Authority & Non-Interpretation
* **Informational Context Only:** `severity` and `confidence` are supplied to Gemini strictly as informational background so the model understands the predetermined classification of the finding.
* **Contextual Reference:** `line_range` is provided solely as situational reference for the code location.
* **Non-Authoritative for AI:** Gemini must not validate, reinterpret, modify, or return these fields.
* **Authoritative Determinism:** These values remain authoritative from the deterministic auditor; supplying this metadata does not give Gemini any authority over detection, severity, confidence, line numbers, or scoring.

### 4.3 Why Focused Context is Preferred
1. **Simplicity:** A compact payload eliminates complex AST serialization and token management.
2. **Minimal Data Exposure:** Users' broader proprietary test suites and business logic remain strictly local; only the isolated offending syntax line is transmitted.
3. **Small Prompt Footprint:** Minimizes token usage, keeping requests well within standard free/starter API rate limits.
4. **Focused AI Output:** Directing the model to an isolated construct prevents rambling commentary on unrelated code.
5. **Traceable Reasoning:** Makes prompts deterministic, auditable, and easy for developers to inspect and debug.

---

## 5. Secret Redaction Architecture (AP09)

User security and data confidentiality are paramount. All source code must undergo automated sanitization **prior** to any outbound API transmission.

### 5.1 Pre-Transmission Redaction Guarantee
Whenever **AP09 (Hardcoded Secrets)** detects sensitive credentials, or when regex heuristics discover credential-like variable assignments in context snippets, the values are replaced with `[REDACTED]`.

Examples of targeted patterns include:
* Passwords (`password = "...", passwd, pwd`)
* API Keys (`api_key = "...", apikey`)
* Authentication Tokens (`token = "...", access_token, bearer_token`)
* Private Keys (`client_secret, private_key`)

### 5.2 Redaction Flow
```text
Raw Source Line:
password = "SuperSecretPassword123!"

        ↓  [ Redaction Filter: src/gemini/redaction.py ]

Sanitized Context Sent to Gemini:
password = "[REDACTED]"
```

### 5.3 Credential Protection Invariants
* **Zero Real Secrets to AI:** The actual secret string is never embedded in prompts, logs, or external network requests.
* **API Key Safety:** The application’s own `GEMINI_API_KEY` is retrieved from environment variables at runtime and is never hardcoded, written to Git, rendered in the UI, or passed into prompts.

---

## 6. Gemini Request Example

Below is a conceptual trace of the request prepared for Gemini:

### Context Assembled by Auditor
```text
Framework: Playwright
Language: TypeScript
Anti-Pattern: AP06 — Fragile Locators
Severity: Medium
Confidence: High

Detection Reason:
The locator relies on structural position (nth-child) and deeply nested DOM elements.

Relevant Code:
await page.locator("div.container > div:nth-child(2) > button").click();
```

### Prompt Task Directive
```text
Task:
1. Explain concisely (1-2 sentences) why this specific locator pattern is fragile and prone to failure.
2. Provide a single, clean, idiomatic Playwright TypeScript replacement (e.g., using getByRole or getByTestId).
```

---

## 7. Response Contract

Gemini returns structured advice formatted to map directly into the finding view model:

```json
{
  "explanation": "This locator relies on rigid DOM hierarchy and positional nth-child indexes, which break whenever layout wrappers change. It also targets implementation structure rather than accessible user-facing elements.",
  "suggested_fix": "await page.getByRole('button', { name: 'Submit' }).click();"
}
```

### 7.1 Field Definitions
* **`explanation` (string):** A short, objective summary (1–3 sentences) explaining why the identified code smell harms test maintainability, resilience, or execution stability.
* **`suggested_fix` (string):** A concise, concrete code snippet or one-line recommendation demonstrating the idiomatic modern alternative for the active framework.

### 7.2 Explicit Negative Constraints (What Gemini Must NOT Return)
To preserve system determinism, the model must **NOT** return:
* Modified severity levels (e.g., proposing "High" instead of "Medium").
* Score deductions or penalty points.
* Additional or hallucinated anti-pattern findings.
* Full-file script rewrites or complete refactored modules.
* Automated patching instructions or arbitrary shell commands.

---

## 8. Gemini Prompt Design Requirements

The prompt construction template inside `src/gemini/prompts.py` must enforce strict operational constraints:

### 8.1 Required Prompt Directives
The prompt template must explicitly instruct Gemini to:
1. **Accept Finding as Given:** Treat the supplied anti-pattern classification as an established fact; do not debate whether it is an anti-pattern.
2. **Context Fidelity:** Evaluate only the provided code snippet and framework/language context; do not assume unseen architecture.
3. **Conciseness:** Restrict explanations to 2–3 sentences and suggested fixes to 1–2 lines of code.
4. **Framework Idioms:** Suggest fixes adhering to modern best practices (e.g., explicit waits over `time.sleep` in Selenium, web-first `expect` in Playwright, `.should()` in Cypress).
5. **Output Structure:** Return cleanly delimited text or JSON matching the `explanation` and `suggested_fix` contract.
6. **No Boundary Creep:** Refrain from inventing new issues or offering unrequested general programming critiques.

---

## 9. Error Handling & Graceful Degradation

The Gemini API is an external dependency subject to network latency, outages, quota exhaustion, and invalid inputs. The application is architected to degrade gracefully under all failure modes:

```
+------------------------------------+---------------------------------------------------------------+
| Failure Scenario                   | Fallback Behavior & User Experience                           |
+------------------------------------+---------------------------------------------------------------+
| Missing GEMINI_API_KEY             | Static Fallback: The deterministic audit remains fully usable |
|                                    | even when Gemini enrichment is unavailable. Findings, line   |
|                                    | references, and scores render normally.                       |
+------------------------------------+---------------------------------------------------------------+
| Network Outage / DNS Failure       | System catches connection error; displays static fallback text|
|                                    | ("AI suggestion temporarily unavailable"). Report succeeds.   |
+------------------------------------+---------------------------------------------------------------+
| Request Timeout (> 5s)             | Bounded timeout aborts HTTP call; logs warning; continues     |
|                                    | report assembly with static explanation.                      |
+------------------------------------+---------------------------------------------------------------+
| Rate Limit / Quota Exceeded (429)  | Displays clean notice: "Rate limit reached. AI fix disabled." |
|                                    | Deterministic audit score remains fully intact.               |
+------------------------------------+---------------------------------------------------------------+
| Malformed / Invalid JSON Response  | If the response cannot be parsed or does not contain the      |
|                                    | required fields, discard the invalid AI response and use the  |
|                                    | static fallback state.                                        |
+------------------------------------+---------------------------------------------------------------+
| Empty Response from Model          | Mark AI enrichment as unavailable and retain the              |
|                                    | deterministic finding explanation.                            |
+------------------------------------+---------------------------------------------------------------+
```

### The "Core Audit Primacy" Rule
Under **no circumstances** does a Gemini failure prevent the generation of the scorecard, findings list, line references, or final quality score. The deterministic audit remains fully usable even when Gemini enrichment is unavailable.

---

## 10. API Configuration & Secret Management

Configuration management is intentionally kept lightweight and environment-driven:

```text
Host Environment / .env:
  GEMINI_API_KEY="AIzaSy..."
         │
         ▼
  os.getenv("GEMINI_API_KEY")
         │
         ▼
  GeminiClient Initialization
```

### Security & Privacy Rules
* **Environment Sourced:** The API key is loaded strictly via `os.getenv("GEMINI_API_KEY")`.
* **Zero Persistence:** No database, credentials file, or cloud vault is required for v1.
* **Exclusion from Artifacts:** The key must never be logged, printed to `stdout`, stored in session state, displayed in the Streamlit UI, or committed to Git (`.gitignore` must protect `.env` files).

---

## 11. End-to-End Integration Flow

The complete linear data flow demonstrates that scoring is finalized **before** Gemini is ever invoked:

```text
1. User submits script & selects framework
       ↓
2. Framework validation confirms supported language
       ↓
3. Static Detection Engine flags raw anti-patterns
       ↓
4. Finding Normalizer resolves overlaps & deduplicates
       ↓
5. Deterministic Scoring Engine computes 0-100 score and rating band
       ↓
6. Redaction Layer sanitizes sensitive tokens ([REDACTED])
       ↓
7. Gemini Service dispatches sanitized context for confirmed findings
       ↓
8. Gemini returns short explanation and suggested fix
       ↓
9. Report Generator merges findings, advice, and score into final report
       ↓
10. Streamlit renders visual scorecard and interactive audit findings
```

---

## 12. Component Interface Design

The Gemini service is encapsulated within a modular Python class interface in `src/gemini/client.py`:

```python
# Conceptual Interface (Design Only - Not Implementation Code)
class GeminiService:
    def __init__(self, api_key: str | None = None):
        """Initializes client with environment API key; sets availability flag."""
        pass

    def is_available(self) -> bool:
        """Returns True if API key is present and service is ready."""
        pass

    def enrich_finding(self, finding: Finding, context: dict) -> Finding:
        """
        Takes a confirmed Finding, applies redaction, prompts Gemini,
        and returns the Finding with explanation and suggested_fix attached.
        Degrades gracefully if call fails.
        """
        pass
```

---

## 13. Architectural Trade-offs

| Design Choice | Alternative Considered | Chosen Approach | Rationale & Trade-off |
| :--- | :--- | :--- | :--- |
| **Generative AI Role** | Hardcoded Static Fix Templates | Gemini Advisory Enhancement | Generative text provides natural, contextual explanations tailored to specific variable names and locator types, rather than generic textbook blurbs. Incurs API latency and external dependency. |
| **Detection Authority** | LLM Autonomous Code Auditor | Rule-Based Static Matching | LLM detection causes non-deterministic scores, hallucinated lines, and high token costs. Deterministic matching guarantees 100% reproducible scoring. |
| **Context Scope** | Full Script Transmission | Focused Snippet + Reason | Full scripts increase token cost, expose proprietary code, and risk hallucinations. Focused snippets keep prompts small, fast, and safe. |
| **Service Execution** | Async Celery / Redis Worker Pool | Bounded Synchronous Request | Distributed queues add severe infrastructure overhead for a student v1 tool. Synchronous bounded requests are trivial to implement and maintain. |
| **Session Memory** | Multi-Turn Conversational Memory | Stateless Per-Finding Calls | Multi-turn chat carries context bloat and state management complexity. Stateless calls are independent, idempotent, and simple. |
| **Remediation Action** | Autonomous Code Refactoring | Advisory Suggested Snippet | Autonomous script rewriting risks introducing syntax regressions or altered test logic. Advisory snippets empower the QA engineer to apply fixes intentionally. |

---

## 14. Known Limitations

1. **Advisory Non-Authoritative Nature:** AI-suggested fixes are advisory recommendations; they should be reviewed by an automation engineer prior to being copied into production test suites.
2. **External Availability Dependency:** If the user has no internet access or lacks a Gemini API key, AI features are omitted (though static scoring remains functional).
3. **Context Truncation:** For complex anti-patterns involving widely separated methods (e.g., setup spread across multiple fixtures), an isolated snippet may occasionally provide incomplete context to the model.
4. **Rate Limit Throttling:** Rapid repeated auditing of long scripts with numerous findings may encounter API quota rate limits on free-tier keys.

---

## 15. Implementation Notes

When advancing to STLC Phase 3 (Implementation), developers must observe the following constraints:
* **SDK Selection:** Use the appropriate official Google GenAI Python SDK.
* **Module Encapsulation:** Keep all Gemini client logic contained entirely within `src/gemini/`; no direct Gemini API calls from `app.py` or `detectors/`.
* **Prompt Isolation:** Store prompt templates in `src/gemini/prompts.py` to enable rapid iteration without altering client logic.
* **Pre-Flight Redaction:** Always execute `redact_secrets(snippet)` before calling the Gemini SDK.
* **Non-Mutating Integration:** Ensure the enrichment step attaches only to `finding.explanation` and `finding.suggested_fix`; it must never mutate `finding.severity`, `finding.line_start`, or scoring weights.

---

## 16. Design Decision Summary

| Decision | Selected Approach | Core Rationale |
| :--- | :--- | :--- |
| **Gemini Role** | Advisory Only (Post-Detection) | Protects scoring determinism, repeatability, and objectivity. |
| **Detection Authority** | Static AST and Regex Rules | Eliminates AI hallucinations and non-deterministic scoring variance. |
| **Request Scope** | Focused Code Snippet + Finding Context | Maximizes privacy, minimizes token costs, and keeps advice targeted. |
| **Secret Sanitization** | Pre-transmission `[REDACTED]` Replacement | Absolute prevention of credential leakage to external AI endpoints. |
| **Response Format** | Two Fields: `explanation` and `suggested_fix` | Clean, predictable UI integration without conversational filler. |
| **Failure Strategy** | Graceful Degradation to Static State | The deterministic audit remains fully usable even when Gemini enrichment is unavailable. |
| **Configuration** | Environment Variable (`GEMINI_API_KEY`) | Standard, secure 12-factor configuration; zero hardcoded secrets. |
| **Execution Pattern** | Bounded Synchronous Requests | Simplicity, zero infrastructure overhead, and easy local debugging. |

---

## 17. Design Completion Criteria

The Gemini API Integration Design milestone is complete upon verifying that:
* [x] Gemini’s responsibility is firmly bounded to advisory explanation and suggested fix generation.
* [x] Deterministic primacy is enforced (detection, severity, line numbers, and scoring remain 100% rule-based).
* [x] Request payload schema and focused snippet strategy are documented.
* [x] Mandatory secret redaction (`[REDACTED]`) before API dispatch is architecturally required.
* [x] Two-field response contract (`explanation`, `suggested_fix`) and negative constraints are defined.
* [x] Resilient failure handling and graceful degradation fallbacks are established.
* [x] Environment-driven API key configuration (`GEMINI_API_KEY`) is specified.
* [x] End-to-end integration flow proves scoring precedes AI enrichment.
* [x] Design trade-offs, limitations, and implementation notes are comprehensively detailed.
* [x] No application implementation code was created.
* [x] Existing specifications (`requirements.md`, `framework-support.md`, `anti-pattern-checklist.md`, `scoring-system.md`, `architecture.md`) remain untouched and consistent.
