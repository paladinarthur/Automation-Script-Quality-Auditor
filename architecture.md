# Automation Script Quality Auditor — System Architecture

**Project:** Automation Script Quality Auditor  
**STLC Phase:** Phase 2 — System & Software Design  
**Document Reference:** `architecture.md`  
**Status:** Authoritative Architectural Design Specification  

---

## 1. Purpose

This document defines the software architecture, component boundaries, data flow, and external API integration patterns for the **Automation Script Quality Auditor** prior to implementation.

### Why Architecture Before Implementation?
Documenting system architecture before coding ensures that:
* Component responsibilities and isolation boundaries are firmly established, avoiding monolithic or circular dependencies.
* Data structures moving between the detection engine, normalizer, scoring calculator, and AI integration are agreed upon upfront.
* The critical boundary between **deterministic rule-based analysis** and **probabilistic generative AI advice** is strictly maintained.
* Future implementation steps proceed predictably and are easily testable in isolation.

### Guiding Architectural Principle
> **Simplicity > unnecessary sophistication.**

This system is an approachable, lightweight v1 learning and project application. It avoids enterprise microservices, persistent databases, distributed message queues, user authentication, or complex containerization. Clean code, clear modular separation, and reproducible static analysis are prioritized over architectural overhead.

---

## 2. Technology Stack

The proposed technology stack is selected to maximize developer velocity, maintainability, and simplicity for a lightweight Python static auditor:

```
+-------------------------------------------------------------------------+
|                               UI Layer                                  |
|                         Streamlit (Python)                              |
+-------------------------------------------------------------------------+
                                    │
+-------------------------------------------------------------------------+
|                             Core Engine                                 |
|               Python 3.10+ (Standard Library: ast, re)                 |
+-------------------------------------------------------------------------+
                    │                                 │
+-----------------------------------+ +-----------------------------------+
|      Deterministic Scorer         | |         Generative AI             |
|   Pure Python Mathematical Logic  | |    Google Gemini API (Client)     |
+-----------------------------------+ +-----------------------------------+
                                    │
+-------------------------------------------------------------------------+
|                             Quality Gate                                |
|                       pytest (Unit & Integration)                       |
+-------------------------------------------------------------------------+
```

### 2.1 Python (Core Language)
* **What:** Python 3.10+ as the primary programming language for all application logic, static analysis, and scoring.
* **Why:** Python provides industry-standard static analysis primitives (`ast`, `re`, `tokenize`), seamless text processing, and direct support for both Streamlit and the Google GenAI SDK.
* **Why this approach:** Using a single language across the frontend, domain engine, and API integration minimizes tooling friction and eliminates multi-runtime coordination.
* **Trade-offs / Limitations:** Python execution speed is slower than compiled languages (e.g., Go, Rust); however, it is well-suited for the lightweight single-script static analysis workload anticipated for this application.
* **Implementation Notes:** Utilize type hinting (`typing`) across all core data models (`Finding`, `ScoreCard`, `AuditReport`) to maintain interface contracts.

### 2.2 Streamlit (User Interface)
* **What:** Streamlit framework for rendering the interactive web UI and coordinating user inputs.
* **Why:** Streamlit enables rapid creation of data-centric web interfaces using pure Python, eliminating the need for a separate JavaScript/React build chain or REST boilerplate.
* **Why this approach:** Traditional client-server architectures (e.g., FastAPI + React) introduce CORS, state synchronization, and dual deployment overhead that is unwarranted for a single-user auditor tool.
* **Trade-offs / Limitations:** Streamlit re-runs the entire script upon user interaction unless cached via `@st.cache_data`. Page layout flexibility is constrained to Streamlit's widget paradigm.
* **Implementation Notes:** Keep UI rendering code (`app.py`) decoupled from analysis logic; the UI must merely invoke the audit orchestrator service and format results.

### 2.3 Rule-Based Static Analysis (Detection Engine)
* **What:** Regex pattern matching (`re`) and Python Abstract Syntax Trees (`ast`) combined with framework-aware heuristics.
* **Why:** Provides instantaneous, deterministic, and explainable anti-pattern detection without executing submitted scripts.
* **Why this approach:** Parsing code text with dedicated regex and AST matchers is vastly faster, cheaper, safer, and more reproducible than delegating detection to an LLM.
* **Trade-offs / Limitations:** Heuristic rules cannot fully infer dynamic runtime behavior or complex cross-file abstractions.
* **Implementation Notes:** Isolate rule evaluators into discrete detector modules with distinct regex boundaries for Python, JavaScript, and TypeScript syntax.

### 2.4 Google Gemini API (AI Explanation & Fix Advisory)
* **What:** Google Gemini API (via the appropriate official Google GenAI Python SDK) utilized strictly as an advisory service.
* **Why:** Gemini generates contextual explanations and tailored code remediation advice for confirmed anti-pattern findings.
* **Why this approach:** Offloading remediation explanations to generative AI provides human-like advice while keeping the core audit score 100% deterministic and reproducible.
* **Trade-offs / Limitations:** Requires external internet connectivity, API keys, and incurs network latency for remote API calls. Subject to API rate limits.
* **Implementation Notes:** All secrets (AP09) must be redacted (`[REDACTED]`) before context is dispatched to Gemini. If the API fails or is unreachable, the system must degrade gracefully and display deterministic findings without AI text.

### 2.5 Pytest (Testing Framework)
* **What:** `pytest` as the automated test harness for unit, integration, and scoring validation.
* **Why:** Clean assertion syntax, comprehensive fixture support, and native integration with Python development workflows.
* **Why this approach:** Simple, lightweight, and standard across Python projects.
* **Trade-offs / Limitations:** None for this application scope.
* **Implementation Notes:** Maintain dedicated test fixtures containing synthetic script samples for all 10 anti-pattern categories.

### 2.6 Git & GitHub (Version Control)
* **What:** Git version control system with incremental, semantic commits.
* **Why:** Enables transparent STLC progression, traceability, and reversible changes.
* **Why this approach:** Standard practice for modern software engineering.

---

## 3. High-Level Architecture & Components

The application is decomposed into eight distinct components, each strictly adhering to the Single Responsibility Principle:

```
+-----------------------------------------------------------------------------------+
| 1. Streamlit UI (View & Presentation)                                             |
|    - Renders input controls (dropdowns, text area, file uploader).               |
|    - Displays scorecards, severity metrics, finding accordions, and audit report. |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
| 2. Audit Orchestrator / Audit Service (Application Coordinator)                   |
|    - Coordinates the pipeline: Validation -> Detection -> Normalization ->       |
|      Scoring -> AI Enhancement -> Report Compilation.                             |
+-----------------------------------------------------------------------------------+
             │                             │                            │
             ▼                             ▼                            ▼
+-------------------------+   +-------------------------+  +------------------------+
| 3. Framework Config     |   | 4. Static Analysis      |  | 5. Finding Normalizer  |
|    & Validation         |   |    Detection Engine     |  |    & Deduplication     |
| - Validates input.      |   | - Executes active rules.|  | - Deduplicates issues. |
| - Activates framework-  |   | - Flags raw findings.   |  | - Resolves AP01/02/10  |
|   specific rule sets.   |   | - Extracts line ranges. |  |   overlaps.            |
+-------------------------+   +-------------------------+  +------------------------+
                                                                        │
                                                                        ▼
+---------------------------------------------------+      +------------------------+
| 7. Gemini Integration Service                     |      | 6. Scoring Engine      |
| - Mandatory secret redaction ([REDACTED]).        |      | - Deterministic math.  |
| - Requests explanations and 1-line fixes.         |      | - Base 100, -10/-4.    |
| - Graceful error degradation fallback.            |      | - Per-pattern -20 cap. |
+---------------------------------------------------+      | - 4 Rating bands.      |
                         │                                 +------------------------+
                         ▼                                              │
               [ External Gemini API ]                                  │
                         │                                              ▼
                         └───────────────────────┬──────────────────────┘
                                                 │
                                                 ▼
+-----------------------------------------------------------------------------------+
| 8. Report / Scorecard Generator                                                   |
|    - Assembles Executive Summary, Scorecard, Detailed Findings, Recommendations,  |
|      and Methodology into structured view models.                                 |
+-----------------------------------------------------------------------------------+
```

### Component Breakdown
1. **Streamlit UI:** Pure presentation layer. Captures user interactions, passes raw input to the audit service, and renders output view models.
2. **Audit Orchestrator:** The pipeline coordinator. Directs the workflow from raw text to complete report without implementing detection or scoring logic itself.
3. **Framework Configuration / Validation:** Validates that submitted script text is non-empty and maps framework/language selections (e.g., Selenium + Python) to active rule sets.
4. **Static Analysis / Detection Engine:** Evaluates active rules against the script text; produces raw finding objects with line references and snippets.
5. **Finding Normalizer & Deduplication:** Resolves overlapping rules (e.g., ensuring `time.sleep(5)` flags exclusively as AP01 and suppresses AP02/AP10) to produce the final finding list.
6. **Scoring Engine:** Pure mathematical engine. Computes total deductions, enforces category caps, clamps the score (0–100), and assigns rating bands.
7. **Gemini Integration Service:** Redacts secrets, prepares prompts, contacts the Gemini API, parses generated explanations/fixes, and attaches them to findings.
8. **Report / Scorecard Generator:** Formats finalized findings and scoring metrics into the 5-section audit report structure.

---

## 4. User → Application → API Flow

The system maintains a strictly linear, synchronous execution flow:

```text
USER                  APPLICATION (STREAMLIT & AUDIT ENGINE)             EXTERNAL API (GEMINI)
 │                                      │                                          │
 ├─ 1. Selects Framework & Language ───>│                                          │
 ├─ 2. Pastes / Uploads Script ────────>│                                          │
 ├─ 3. Clicks "Analyze Script" ────────>│                                          │
 │                                      │                                          │
 │                                      ├─ 4. Validate Input Non-Empty             │
 │                                      ├─ 5. Route to Active Framework Rules      │
 │                                      ├─ 6. Run Static Detection Engine          │
 │                                      ├─ 7. Normalize & Deduplicate Findings     │
 │                                      ├─ 8. Calculate Deterministic Score        │
 │                                      │                                          │
 │                                      ├─ 9. Redact Secrets (AP09 -> [REDACTED])  │
 │                                      ├─ 10. Dispatch Prompt Context ───────────>│
 │                                      │                                          ├─ 11. Generate Advice
 │                                      │<─ 12. Return Explanations & Fixes ───────┤
 │                                      │                                          │
 │                                      ├─ 13. Assemble Scorecard & Audit Report   │
 │<─ 14. Render Interactive Results ────┤                                          │
```

> [!IMPORTANT]
> **Gemini API Isolation:** Notice that Step 8 (Deterministic Score Calculation) occurs **prior** to and **independent** of Step 10 (Gemini API Dispatch). Gemini never touches or influences the score.

---

## 5. Component Architecture Diagram

The detailed module interaction and call topology are structured as follows:

```text
+---------------------------------------------------------------------------------+
|                                STREAMLIT UI                                     |
|                      (app.py / components / views)                              |
+---------------------------------------------------------------------------------+
                                       │
                                       │ calls analyze(script, framework, lang)
                                       ▼
+---------------------------------------------------------------------------------+
|                              AUDIT SERVICE                                      |
|                       (src/audit/orchestrator.py)                               |
+---------------------------------------------------------------------------------+
       │                      │                      │                   │
       ▼                      ▼                      ▼                   ▼
+--------------+     +------------------+   +-----------------+  +---------------+
|  FRAMEWORK   |     | DETECTION ENGINE |   |     SCORING     |  |    GEMINI     |
|  VALIDATION  |     | (src/detectors/) |   |     ENGINE      |  |    SERVICE    |
| (validation) |     +------------------+   |  (src/scoring/) |  | (src/gemini/) |
+--------------+       │              │     +-----------------+  +---------------+
                       ▼              ▼              │                   │
                +------------+  +------------+       │                   │
                | Universal  |  | Framework- |       │                   ▼
                | Rules      |  | Aware      |       │           +---------------+
                | (Common)   |  | Rules      |       │           |  Gemini API   |
                +------------+  +------------+       │           |  (External)   |
                       │              │              │           +---------------+
                       └───────┬──────┘              │                   │
                               ▼                     │                   │
                     +--------------------+          │                   │
                     |    FINDING         |          │                   │
                     |    NORMALIZER      |──────────┘                   │
                     | (deduplication.py) |                              │
                     +--------------------+                              │
                               │                                         │
                               ▼                                         │
                     +--------------------+                              │
                     | FINAL FINDINGS     |──────────────────────────────┘
                     | (Typed Models)     |
                     +--------------------+
                               │
                               ▼
+---------------------------------------------------------------------------------+
|                       REPORT & SCORECARD BUILDER                                |
|                        (src/reporting/builder.py)                               |
+---------------------------------------------------------------------------------+
                                       │
                                       ▼ returns AuditReport view model
+---------------------------------------------------------------------------------+
|                          RENDERED STREAMLIT UI                                  |
+---------------------------------------------------------------------------------+
```

---

## 6. Data Flow & Data Contracts

Components communicate through strongly-typed, immutable in-memory data structures:

### 6.1 Data Contracts

#### Input Payload
```python
# Provided by User via Streamlit UI
framework: str          # "selenium" | "playwright" | "cypress"
language: str           # "python" | "javascript" | "typescript"
script_text: str        # Raw source code of the automation script
```

#### Raw & Normalized Finding Model
```python
class Finding:
    id: str             # e.g., "AP01"
    title: str          # e.g., "Hardcoded Wait"
    severity: str       # "High" | "Medium"
    confidence: str     # "High" | "Medium" | "Low"
    line_start: int     # 1-indexed start line
    line_end: int       # 1-indexed end line (same as start for single-line)
    code_snippet: str   # Offending source line(s)
    explanation: str    # Filled initially with static reason; augmented by Gemini
    suggested_fix: str  # Filled by Gemini (or fallback template)
```

#### Scoring Result Model
```python
class ScoreCard:
    overall_score: int                 # 0 to 100
    rating: str                        # "Excellent" | "Good" | "Fair" | "Poor"
    total_issues: int                  # Count of confirmed findings
    high_severity_count: int           # Count of High issues
    medium_severity_count: int         # Count of Medium issues
    categories_detected: int           # Distinct anti-patterns detected (0 to 10)
    category_breakdown: dict[str, int] # e.g., {"AP01": 1, "AP02": 0, ...}
```

#### Final Audit Report Model
```python
class AuditReport:
    scorecard: ScoreCard
    findings: list[Finding]
    executive_summary: dict
    recommendations: dict[str, list[str]] # "high_priority", "medium_priority"
    methodology_notes: list[str]
```

### 6.2 Component Ownership Matrix

| Data Structure | Producing Component | Consuming Component |
| :--- | :--- | :--- |
| `ScriptInput` | Streamlit UI | Audit Orchestrator, Framework Validator |
| `RawFindings` | Static Detection Engine | Finding Normalizer |
| `FinalFindings` | Finding Normalizer | Scoring Engine, Gemini Service, Report Builder |
| `ScoreCard` | Scoring Engine | Report Builder, Streamlit UI |
| `AIEnhancement` | Gemini Service | Report Builder (attached to `Finding`) |
| `AuditReport` | Report Builder | Streamlit UI |

---

## 7. Data Flow Diagram

```text
+-------------------+
|    User Input     | (Script text, Framework selection, Language)
+-------------------+
          │
          ▼
+-------------------+
| Input Validation  | (Check non-empty, valid framework/language pair)
+-------------------+
          │ Validated Script
          ▼
+-------------------+
|  Static Analysis  | (Evaluate Common + Framework AST/Regex Rules)
+-------------------+
          │ Raw Findings (contains potential duplicates/overlaps)
          ▼
+-------------------+
| Deduplication &   | (Resolve AP01 vs AP02/AP10; suppress overlapping rules)
| Normalization     |
+-------------------+
          │ Final Confirmed Findings List
          ├───────────────────────────────────────────────────┐
          ▼                                                   ▼
+-------------------+                               +--------------------+
|   Deterministic   |                               |  Secret Redaction  |
|  Scoring Engine   |                               |  (AP09 -> REDACT)  |
+-------------------+                               +--------------------+
          │                                                   │ Sanitized Context
          │ Score & Rating                                    ▼
          │                                         +--------------------+
          │                                         | External Gemini API|
          │                                         +--------------------+
          │                                                   │
          │                                                   ▼ AI Advice
          │                                         +--------------------+
          │                                         | Attach Advice to   |
          │                                         | Findings           |
          │                                         +--------------------+
          │                                                   │
          └─────────────────────────┬─────────────────────────┘
                                    │
                                    ▼
                          +-------------------+
                          | Final Audit Model | (Executive Summary, Scorecard,
                          |    Assembly       |  Enriched Findings, Recs)
                          +-------------------+
                                    │
                                    ▼
                          +-------------------+
                          |   Streamlit UI    | (Visual Scorecard, Accordions,
                          |    Rendering      |  Markdown Reports)
                          +-------------------+
```

---

## 8. Detection Engine Design

The detection engine is **strictly rule-based and deterministic**. It inspects raw script strings and structural syntax patterns.

### 8.1 Rule Classification

```
+-----------------------------------------------------------------------------+
|                               DETECTION RULES                               |
+--------------------------------------+--------------------------------------+
|          Deterministic Rules         |            Heuristic Rules           |
|         (Strict Syntax Match)        |      (Pattern Context & Thresholds)  |
+--------------------------------------+--------------------------------------+
| • AP01: Hardcoded Waits              | • AP02: Magic Numbers / Constants    |
|   (time.sleep, waitForTimeout)       | • AP03: Duplicated Code (>= 3 lines) |
| • AP07: Missing Assertions           | • AP04: Poor Structure (30+ stmts)   |
|   (zero assertions in test block)    | • AP05: Missing Abstractions (POM)   |
| • AP09: Hardcoded Secrets            | • AP06: Fragile Locators (DOM depth) |
|   (password = "...", api_key = "...")| • AP08: Testing Implementation Detail|
|                                      | • AP10: Potentially Flaky Patterns   |
+--------------------------------------+--------------------------------------+
```

### 8.2 Analysis Primitives
1. **Regular Expressions (`re`):** Used for exact method invocation matching (`page.waitForTimeout`, `cy.wait`, `time.sleep`) and secret pattern discovery (`api_key\s*=\s*['"][^'"]+['"]`).
2. **Python AST (`ast` module):** For Selenium Python and Playwright Python scripts, the engine parses code into an Abstract Syntax Tree to accurately traverse functions, count statements, detect loops, and identify assertion nodes without regex fragility.
3. **Line Indexing Buffer:** Tracks character offsets and newlines (`\n`) to ensure every match translates to accurate, 1-indexed line numbers.
4. **Conservatism Principle:** For heuristic rules (AP02, AP04, AP05, AP08, AP10), ambiguous constructs default to **No Finding** to prevent user fatigue from false positives.

---

## 9. Finding Lifecycle

Every detected issue traverses a well-defined state lifecycle before reaching the user:

```text
 [ 1. DETECTED ] ──> Regex/AST rule flags matching pattern on Line X
        │
        ▼
 [ 2. NORMALIZED ] ─> Structured into a Finding model with severity & confidence
        │
        ▼
 [ 3. DEDUPLICATED ]> Overlapping rules resolved (e.g., AP01 takes precedence)
        │
        ▼
 [ 4. SCORED ] ─────> Deterministic scoring engine deducts points (−10 or −4)
        │
        ▼
 [ 5. REDACTED ] ───> Secrets masked ([REDACTED]) before external dispatch
        │
        ▼
 [ 6. AI-ENRICHED ] ─> Gemini explanation and suggested fix attached
        │
        ▼
 [ 7. REPORTED ] ───> Rendered on Streamlit Scorecard and Executive Report
```

### Why Deduplication Precedes Scoring
Multiple rules may superficially recognize the same code token. For example:
`time.sleep(5)` contains a numeric literal (`5`) and causes artificial synchronization delays. Without deduplication, it could trigger **AP01 (Hardcoded Wait)**, **AP02 (Magic Number)**, and **AP10 (Flaky Pattern)** simultaneously, unfairly docking 18 points for a single line of code.

By running deduplication prior to scoring, `time.sleep(5)` is attributed solely to **AP01 (−10 points)**, ensuring fair, mathematically defensible scoring.

---

## 10. Scoring Architecture

The scoring engine is completely decoupled from UI rendering and external APIs:

```
Base Score = 100 Points

Penalties:
  - High-Severity Finding:   -10 Points
  - Medium-Severity Finding:  -4 Points

Category Cap:
  - Maximum deduction per anti-pattern: -20 Points

Floor Clamp:
  - Final Score = max(0, 100 - Total Penalty)
```

### Rating Band Mapping
* **80 – 100:** **Excellent** (High quality, minimal to zero detected issues)
* **60 – 79:** **Good** (Solid test code with minor structural or wait smells)
* **50 – 59:** **Fair** (Noticeable maintainability, locator, or assertion gaps)
* **0 – 49:** **Poor** (Significant anti-patterns; immediate refactoring needed)

### Architectural Invariants
* **Confidence Invariant:** Detection confidence (`High`, `Medium`, `Low`) is preserved purely as diagnostic metadata; it **never** alters numerical penalty weights.
* **Category Count Invariant:** The count of affected categories (e.g., `3 / 10`) is informational; the score is derived strictly from confirmed findings and severity deductions.
* **Independence Invariant:** The scoring engine has zero network dependencies and operates as an in-memory calculation well-suited for immediate interactive feedback.

---

## 11. Gemini API Architecture

Google Gemini is integrated strictly as a bounded synchronous advisory service:

```text
[ Confirmed Finding ]
         │
         ▼
+-----------------------------------------------------------+
| Secret Redaction Filter (AP09 String Masking)             |
| Replaces raw credentials with "[REDACTED]"                |
+-----------------------------------------------------------+
         │ Sanitized Snippet + Anti-Pattern Title + Framework
         ▼
+-----------------------------------------------------------+
| Prompt Template Assembly                                  |
| System: "You are a QA automation expert. Explain why this |
| pattern is bad and provide a 1-line refactored fix."      |
+-----------------------------------------------------------+
         │ HTTP Request Payload
         ▼
+-----------------------------------------------------------+
| Google Gemini API Endpoint (generateContent)              |
+-----------------------------------------------------------+
         │ JSON / Text Response
         ▼
+-----------------------------------------------------------+
| Response Parser & Fallback Guard                          |
| Splits text into (explanation, suggested_fix)             |
+-----------------------------------------------------------+
         │
         ▼
[ Enriched Finding Attached to Audit Report ]
```

### Strict Governance Rules
* **Gemini MAY:** Explain confirmed findings; provide clean, modern, idiomatic suggested code.
* **Gemini MUST NOT:**
  * Determine whether an anti-pattern exists.
  * Add unconfirmed issues to the report.
  * Alter or assign issue severity.
  * Compute or modify the quality score.
  * Override deterministic detector findings.

---

## 12. Secret Handling Architecture (AP09)

The auditor treats user source code privacy with paramount importance:

```python
# Conceptual Redaction Pipeline
def sanitize_context_for_ai(snippet: str, secret_match: str) -> str:
    """
    Guarantees that credentials detected by AP09 are stripped
    prior to any outbound transmission to Google Gemini.
    """
    return snippet.replace(secret_match, "[REDACTED]")
```

### Architecture Policies
1. **In-Memory Volatility:** Submitted scripts are processed exclusively in volatile memory (`RAM`). No script text or detected secrets are ever persisted to disk, local files, or remote databases.
2. **Pre-Transmission Redaction:** Any token identified as a probable secret (passwords, auth tokens, private keys) is replaced with `[REDACTED]` before assembling the Gemini prompt payload.
3. **No Persistent Vault:** To remain lightweight, the auditor does not introduce secret management vaults (e.g., HashiCorp Vault, AWS Secrets Manager).

---

## 13. Error Handling & Fault Isolation

The system enforces resilient error boundaries so that failures in peripheral services never crash the core audit flow:

```
+--------------------------+-------------------------------------------------------------+
| Error Scenario           | Architectural Mitigation / Fallback Behavior                |
+--------------------------+-------------------------------------------------------------+
| Empty Script Input       | UI intercept: Displays warning notification; aborts audit   |
|                          | cleanly without running engine.                             |
+--------------------------+-------------------------------------------------------------+
| Unsupported Language     | Framework validator rejects execution; prompts user to pick |
|                          | a valid binding (e.g., Selenium + Python).                  |
+--------------------------+-------------------------------------------------------------+
| Malformed Script Syntax  | Falls back to regex-only scanning; logs non-fatal parser    |
|                          | warning; evaluates text without crashing.                   |
+--------------------------+-------------------------------------------------------------+
| Gemini API Unavailable / | Graceful degradation: Scorecard, line references, and       |
| Network Failure          | static explanations render normally; AI suggestions display |
|                          | "AI suggestions temporarily unavailable".                   |
+--------------------------+-------------------------------------------------------------+
| Gemini Rate Limit / 429  | Fallback template message; audit report completes cleanly.  |
+--------------------------+-------------------------------------------------------------+
| Zero Anti-Patterns Found | Returns Score 100 / 100 (Excellent); renders clean report   |
|                          | commending high-quality test structure.                     |
+--------------------------+-------------------------------------------------------------+
```

---

## 14. Separation of Responsibilities

| Component | Primary Responsibility | Explicitly Should NOT Do |
| :--- | :--- | :--- |
| **Streamlit UI** | Capture user input; render scorecards, metrics, accordions, and reports. | Contain regex rules, calculate math scores, or call Gemini directly. |
| **Audit Service** | Orchestrate pipeline handoffs from validation to report assembly. | Directly parse syntax or implement individual detection logic. |
| **Framework Validation** | Confirm input presence and validate framework/language compatibility. | Evaluate anti-pattern rules or modify script text. |
| **Detection Engine** | Execute regex/AST pattern matching; extract line numbers and snippets. | Calculate scores, alter severity weights, or filter duplicates across categories. |
| **Finding Normalizer** | Resolve cross-rule overlaps (e.g., AP01 vs AP02/AP10) and de-duplicate. | Change line numbers or modify detector confidence. |
| **Scoring Engine** | Compute deductions, apply category caps (−20), clamp to 0, assign bands. | Invoke AI services, inspect script text, or filter findings. |
| **Gemini Service** | Redact secrets; fetch explanations and suggested fixes for findings. | Evaluate rules, confirm findings, assign severity, or influence scores. |
| **Report Generator** | Aggregate scorecard, findings, recommendations, and methodology models. | Re-calculate scores or re-evaluate detector rules. |

---

## 15. Proposed Project Structure

To maintain modularity and allow independent testing of each component, the project will be organized as follows:

```text
automation-script-quality-auditor/
│
├── app.py                          # Streamlit application entry point
├── requirements.txt                # Project dependencies (streamlit, google-genai, pytest)
├── README.md                       # Project overview, setup, and usage guide
│
├── src/                            # Application Core Source Code
│   ├── __init__.py
│   │
│   ├── audit/                      # Pipeline Orchestration
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Main AuditService coordinating pipeline
│   │   └── models.py               # Shared typed dataclasses (Finding, ScoreCard, Report)
│   │
│   ├── validation/                 # Input & Framework Validation
│   │   ├── __init__.py
│   │   └── validator.py            # Validates script text & language bindings
│   │
│   ├── detectors/                  # Static Analysis Engine & Rules
│   │   ├── __init__.py
│   │   ├── base.py                 # Base detector interface
│   │   ├── common.py               # Framework-agnostic rules (AP02, AP03, AP04, AP05, AP08, AP09)
│   │   ├── selenium.py             # Selenium-specific rules (AP01, AP06, AP07)
│   │   ├── playwright.py           # Playwright-specific rules (AP01, AP06, AP07)
│   │   ├── cypress.py              # Cypress-specific rules (AP01, AP06, AP07)
│   │   └── deduplication.py        # Normalizer resolving rule overlaps
│   │
│   ├── scoring/                    # Deterministic Scoring Engine
│   │   ├── __init__.py
│   │   └── calculator.py           # Deductions, category caps, floor clamping & rating bands
│   │
│   ├── gemini/                     # AI Advisory Service
│   │   ├── __init__.py
│   │   ├── client.py               # Gemini API client wrapper
│   │   ├── prompts.py              # Prompt templates
│   │   └── redaction.py            # AP09 secret sanitization filter
│   │
│   └── reporting/                  # Report & Scorecard Generation
│       ├── __init__.py
│       └── builder.py              # Formats executive summary, tables, and markdown views
│
├── tests/                          # Automated Test Suites
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures & mock objects
│   ├── test_detectors.py           # Unit tests for AP01–AP10 rules
│   ├── test_deduplication.py       # Unit tests for overlap resolution
│   ├── test_scoring.py             # Unit tests for scoring math, caps, and bands
│   ├── test_redaction.py           # Security tests verifying secret redaction
│   └── test_orchestrator.py        # Integration tests for full pipeline
│
└── samples/                        # Synthetic Test Automation Scripts (DS-01 to DS-08)
    ├── clean_selenium.py
    ├── clean_playwright.py
    ├── clean_cypress.js
    ├── bad_waits.py
    ├── fragile_locators.py
    └── hardcoded_secrets.py
```

*Note: This layout is a proposed design specification; directories and code files will be instantiated incrementally during Phase 3 (Implementation).*

---

## 16. Version Control & Incremental Implementation Strategy

Implementation will proceed incrementally across STLC Phase 3, with distinct, testable commits reflecting logical component milestones:

```text
Commit Themes & Phased Roadmap:
-------------------------------------------------------------------------
1. chore: project scaffolding and dependency setup
2. feat(validation): add input validation and framework configuration
3. feat(detectors): implement base detector interface and common rules
4. feat(detectors): add framework-specific rules for Selenium, Playwright, Cypress
5. feat(detectors): implement finding normalizer and deduplication
6. feat(scoring): implement deterministic scoring engine and rating bands
7. feat(gemini): implement secret redaction filter and Gemini client wrapper
8. feat(reporting): implement report and scorecard assembly
9. feat(ui): build Streamlit layout, input widgets, and scorecard rendering
10. test: add comprehensive pytest unit and integration suites
11. docs: update user guide and final architecture walkthrough
```

---

## 17. Architectural Trade-offs

| Architectural Decision | Alternative Considered | Chosen Approach | Key Benefit | Incurred Limitation |
| :--- | :--- | :--- | :--- | :--- |
| **System Packaging** | Microservices Architecture | Single Lightweight App | Zero networking overhead; rapid local execution. | Cannot independently scale analysis workers horizontally. |
| **Data Persistence** | Relational DB (PostgreSQL / SQLite) | In-Memory Processing | Extreme simplicity; zero DB migrations or credential storage. | Historical audit results vanish when session ends or browser refreshes. |
| **Detection Mechanism** | LLM-as-a-Detector | Rule-Based Static Matching | 100% deterministic, well-suited for responsive local analysis, zero API cost for detection. | Cannot detect subtle semantic anti-patterns outside defined checklist. |
| **AI Role** | Autonomous Auditor | Advisory Explanations & Fixes | Scores remain trustworthy, reproducible, and mathematically rigorous. | Explanations require external API call and valid Gemini API key. |
| **Scoring Algorithm** | Statistical Issue Density / LOC | Fixed Severity Deductions | Intuitive and explainable to non-technical stakeholders. | Does not reward or penalize based on total script size (20 vs 200 lines). |
| **Execution Mode** | Runtime Sandbox Testing | Static Code Inspection | Complete safety; no browser drivers, network calls, or malicious code risks. | Cannot detect dynamic elements or runtime race conditions. |

---

## 18. Architectural Boundaries & Limitations

To ensure stakeholder alignment, the system explicitly acknowledges what it does **not** provide:
1. **No Application Correctness Proof:** The auditor evaluates script formatting and structure; it does not verify whether the test accurately asserts the target website's business requirements.
2. **No Dynamic Execution:** The tool cannot detect runtime timing bugs, dynamic layout shifts, or browser-specific rendering discrepancies.
3. **No General SAST / Vulnerability Scanner:** Outside of AP09 (Hardcoded Secrets), the auditor does not scan for OWASP vulnerabilities, SQL injection, or dependency CVEs.
4. **No Full Code Coverage Analysis:** The tool does not calculate execution path coverage or line branch coverage.
5. **No Universal Perfection Guarantee:** A score of `100 / 100` signifies zero detected anti-patterns against the **v1 checklist**; it does not guarantee flawlessness.

---

## 19. Design Decision Summary

| Dimension | Architectural Choice | Primary Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Rich AST/regex tooling; native Streamlit and Google GenAI support. |
| **Frontend Framework** | Streamlit | Rapid interactive Python UI without JavaScript build tooling. |
| **Detection Engine** | Deterministic AST + Regex Rules | Fast, reproducible, safe, offline static analysis. |
| **Scoring System** | 0–100 Scale, Severity Deductions, Caps | Simple deduction math; explainable and balanced across categories. |
| **AI Integration** | Google Gemini API (Advisory Only) | Provides conversational explanations without compromising scoring determinism. |
| **Data Storage** | In-Memory (Zero Persistence) | Privacy-centric; no credential leakage or database overhead. |
| **Testing Strategy** | Pytest + Synthetic Script Fixtures | Reliable automated regression testing without live website dependencies. |
| **Architecture Pattern** | Modular Layered Monolith | Maximum readability, single-developer ergonomics, and zero microservice sprawl. |

---

## 20. Design Completion Criteria

The STLC Design Phase is complete upon meeting the following verification criteria:
* [x] Technology stack is fully justified with documented trade-offs and implementation notes.
* [x] All 8 system components and their isolated responsibilities are formally defined.
* [x] User → Application → API flow is diagrammed with clear synchronous boundaries.
* [x] Data contracts (`Finding`, `ScoreCard`, `AuditReport`) and data flow diagrams are specified.
* [x] Rule-based detection engine is partitioned into deterministic vs. heuristic classifications.
* [x] Scoring boundary and invariants (no confidence scaling, no AI scoring) are enforced.
* [x] Gemini API role is strictly bounded to post-detection explanations and suggested fixes.
* [x] Secret handling and pre-transmission redaction (`[REDACTED]`) are architecturally mandated.
* [x] Fault isolation and graceful degradation pathways for external API failures are documented.
* [x] Modular directory structure and incremental Git commit themes are outlined.
* [x] Architectural limitations and trade-offs are explicitly acknowledged.
* [x] Existing requirement and specification documents (`requirements.md`, `framework-support.md`, `anti-pattern-checklist.md`, `scoring-system.md`) remain untouched.
