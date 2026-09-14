# Automation Script Quality Auditor — UI Design Specification

**Project:** Automation Script Quality Auditor  
**STLC Phase:** Phase 2 — System & Software Design  
**Document Reference:** `docs/ui-design.md`  
**Status:** Approved Design Specification  

---

## 1. UI Goal

The primary goal of the Automation Script Quality Auditor User Interface is to provide a simple, linear, and intuitive developer workflow for analyzing automation scripts:

```text
Select Framework → Select Language → Provide Script → Analyze → Review Results
```

### Input Flexibility
To ensure maximum convenience for automation testers and QA engineers, "Provide Script" supports two alternative input methods:
- **Paste Code:** Direct text entry into an interactive multiline code editor/text area.
- **Upload File:** Drag-and-drop or file selector for an individual source file (`.py`, `.js`, `.ts`).

Both input methods converge into the exact same logical `ScriptInput` payload (`script_content`, `framework`, `language`) consumed by the audit application.

### Design Scope
The application is designed as a focused, single-purpose developer utility for single-script static analysis, not a complex enterprise dashboard, project repository scanner, or persistent multi-user application.

---

## 2. Design Principles

1. **Simple & Focused:** Keep the interface clean, clutter-free, and single-page. Avoid complex tabs, multi-step wizards, or unnecessary visual noise.
2. **Obvious Workflow:** The analysis path from selection to script input to triggering audit results must be immediately clear.
3. **UI as Presentation Only:** Streamlit is strictly responsible for rendering controls, capturing user input, and formatting view models. All detection, normalization, scoring, reporting, and Gemini enrichment logic remain inside dedicated domain services.
4. **Static Analysis Transparency:** Clearly inform the user via non-intrusive UI notices that analysis is 100% static and submitted scripts are never executed or run in browsers.
5. **Scannable Results:** Present overall quality scores, rating bands, and severity metrics in high-visibility summary cards before detailed finding breakdowns.
6. **Visual Severity Differentiation:** Distinguish High-severity findings (e.g. red/bold badges) from Medium-severity findings (e.g. orange/yellow badges) using clear typography and icons, not relying exclusively on color.
7. **Advisory AI Boundaries:** Present Gemini explanations and suggested fixes as advisory guidance. The UI must never suggest that AI determines rule violations or quality scores.
8. **Resilient Failure Presentation:** If Gemini enrichment is unavailable (missing API key, rate limit, offline network), the UI gracefully renders deterministic findings, scores, and recommendations with a simple non-blocking notice.
9. **Deliberately Simple v1 Application:** Eliminate unnecessary UI capabilities (user authentication, historical audit logs, multi-file project tree views, PDF exports, or theme customizers).
10. **Unified Input Path:** Treat paste and file upload as alternative paths to populate the same script buffer, not separate audit processing pipelines.

---

## 3. Page Structure

The single-page Streamlit application is organized sequentially in top-to-bottom order:

### A. Header Section
- **Application Title:** "Automation Script Quality Auditor"
- **Short Subtitle / Description:** Concise overview stating that the utility performs static code quality analysis on Selenium, Playwright, and Cypress automation test scripts.

### B. Input Section
- **Framework Selector:** Dropdown / Radio selection (`Selenium`, `Playwright`, `Cypress`).
- **Language Selector:** Dropdown selection dynamically filtered to present only valid language bindings for the chosen framework (e.g. Python for Selenium; Python/JS/TS for Playwright; JS/TS for Cypress).
- **Script Input Area:**
  - **Option 1 (Paste):** Multiline code text area with placeholder prompt ("Paste your automation script here...").
  - **Option 2 (File Upload):** File uploader widget supporting single files with extension `.py`, `.js`, or `.ts`.
- **Supported File Types Notice:** Small caption indicating `.py`, `.js`, `.ts` files are supported.
- **Static Analysis Notice:** Non-intrusive informational notice (`st.info`) stating: *"Static analysis only — your script is evaluated without being executed."*
- **Analyze Button:** Prominent primary action button ("Analyze Script").

#### Upload Security & Execution Invariants
- Uploaded files are read strictly as UTF-8 text strings into volatile RAM.
- Uploaded files are never executed, imported, compiled, or persisted to local disk/databases.
- No support for archives (`.zip`), directories, repositories, or surrounding project scanning.

### C. Results Section (Rendered Post-Analysis)
- **Score Summary Banner:** Large numerical quality score (`X / 100`), qualitative rating badge (`Excellent`, `Good`, `Fair`, `Poor`), total issue count, High severity count, Medium severity count, and category count (`X / 10`).
- **Scorecard Breakdown:** Expandable or tabular view detailing the penalty deduction breakdown by anti-pattern ID (e.g., AP01: -10, AP06: -4).
- **Detailed Findings:** Accordion or card list of confirmed findings ordered by line number:
  - Anti-Pattern ID & Name
  - Severity badge (High vs Medium) & Confidence level
  - Line reference (e.g., `Line 14` or `Lines 20–25`)
  - Offending code snippet (formatted inside a monospace code block)
  - Detection Reason & AI-assisted Explanation
  - Actionable Suggested Fix (formatted as code)
- **Recommendations:** Priority-grouped list of actionable recommendations (High priority followed by Medium priority).
- **Methodology Notes:** Concise explanation of static analysis rules, deduplication, base-100 penalty math, category caps, and Gemini advisory boundaries.

---

## 4. Wireframe Specifications

### Initial / Input State Wireframe

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ AUTOMATION SCRIPT QUALITY AUDITOR                                       │
│ Review Selenium, Playwright & Cypress scripts for quality & anti-patterns│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Select Framework                   Select Language                     │
│  ┌───────────────────────────┐      ┌───────────────────────────┐       │
│  │ Playwright              ▼ │      │ Python                    ▼ │       │
│  └───────────────────────────┘      └───────────────────────────┘       │
│                                                                         │
│  Automation Script                                                      │
│                                                                         │
│  Method A: Paste Script                                                 │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ from playwright.sync_api import Page, expect                      │  │
│  │ def test_login(page: Page):                                       │  │
│  │     page.goto("https://example.com/login")                        │  │
│  │     time.sleep(5)  # Hardcoded wait                               │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  OR                                                                     │
│                                                                         │
│  Method B: Upload Script File                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Drag and drop file here  [ Browse files ]                         │  │
│  │                      • PY, JS, TS                                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ℹ Static analysis only — script content is evaluated without execution.│
│                                                                         │
│                          [ 🔍 Analyze Script ]                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Results State Wireframe

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ AUDIT RESULTS                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌───────────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────┐ │
│ │ OVERALL SCORE     │ │ RATING        │ │ TOTAL ISSUES  │ │ CATEGORIES│ │
│ │     90 / 100      │ │   EXCELLENT   │ │   1 Issue     │ │   1 / 10  │ │
│ └───────────────────┘ └───────────────┘ └───────────────┘ └───────────┘ │
│                                                                         │
│ 📊 Scorecard & Deductions                                               │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ Category                           Severity   Findings    Deduction │ │
│ │ AP01 — Hardcoded Waits             High          1           -10    │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ 🚨 Confirmed Anti-Pattern Findings (1)                                  │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🔴 AP01 · Hardcoded Waits                       HIGH • Line 4        │ │
│ │                                                                     │ │
│ │ Code Snippet:                                                       │ │
│ │   time.sleep(5)                                                     │ │
│ │                                                                     │ │
│ │ Detection Reason:                                                   │ │
│ │   Fixed delay is used instead of waiting for application state.     │ │
│ │                                                                     │ │
│ │ Explanation (AI Advisory):                                          │ │
│ │   Unconditional pauses cause flaky execution and slow test suites.  │ │
│ │                                                                     │ │
│ │ Suggested Fix (AI Advisory):                                        │ │
│ │   expect(page.locator('#submit')).to_be_visible()                   │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ 💡 Actionable Recommendations                                           │
│ • [AP01 - Hardcoded Waits] Replace time.sleep(5) on line 4 with web-  │
│   first assertions or explicit element state waiters.                   │
│                                                                         │
│ ℹ Methodology & Audit Boundaries                                        │
│ • Static Analysis Only • Base Score 100 • High -10 / Medium -4 • Cap -20│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. UI Components Specification

| Component | Purpose | Input / Output | Responsibility |
| :--- | :--- | :--- | :--- |
| **Page Header** | Displays application branding and purpose. | Output: Title & subtitle text. | Rendering application identity. |
| **Framework Selector** | Captures target automation framework. | Input: Dropdown selection (`selenium`, `playwright`, `cypress`). Output: Active framework string. | Control state capturing. |
| **Language Selector** | Captures script language binding. | Input: Dropdown selection filtered by active framework (`python`, `javascript`, `typescript`). Output: Active language string. | Control state capturing & valid combination filtering. |
| **Script Text Area** | Allows direct pasting of automation source code. | Input: Multiline text entry. Output: Script string buffer. | Text input handling. |
| **File Uploader** | Allows uploading an individual source file. | Input: Single `.py`, `.js`, or `.ts` file. Output: Script string buffer extracted from file text. | File text ingestion only. Does NOT execute or import code. |
| **Supported File Indicator** | Informs user of valid upload file extensions. | Output: Small text caption (`.py`, `.js`, `.ts`). | Static UI documentation. |
| **Static Analysis Notice** | Reassures user that code is statically analyzed without execution. | Output: Informational callout banner (`st.info`). | Transparency & security notice. |
| **Analyze Button** | Triggers execution of the audit pipeline. | Input: User button click. Output: Triggers audit orchestrator call. | Event trigger. |
| **Validation Message** | Informs user of invalid inputs or empty scripts. | Output: Warning banner (`st.warning` / `st.error`). | Displaying validation feedback. |
| **Progress Indicator** | Provides visual feedback while analysis runs. | Output: Spinner widget (`st.spinner`). | Indicating active pipeline processing. |
| **Score Summary Banner** | Displays high-level quality metrics. | Input: `ScoreCard` model. Output: Metric boxes for Score, Rating, Total Issues, High/Med counts, Category count. | Visual metric presentation. |
| **Scorecard Display** | Details penalty calculations per category. | Input: `ScoreCard.category_breakdown`. Output: Table showing per-category deductions. | Financial-style score breakdown display. |
| **Finding Card List** | Displays individual confirmed anti-pattern findings. | Input: `list[Finding]`. Output: Styled cards containing line numbers, code snippets, reasons, explanations, and fixes. | Detailed finding visualization. |
| **Recommendation Section** | Displays priority-ordered recommendations. | Input: `AuditReport.recommendations`. Output: High-priority and Medium-priority bulleted lists. | Actionable advice layout. |
| **Methodology Section** | Explains audit rules, scoring formula, and Gemini boundaries. | Input: `AuditReport.methodology`. Output: Bulleted methodology footer. | Audit transparency & disclosure. |
| **Gemini Unavailable Notice** | Notifies user when AI suggestions are omitted. | Output: Non-blocking warning banner (`st.warning`). | Non-intrusive status notification. |

---

## 6. Framework / Language Interactions

To prevent invalid framework/language payloads from reaching the audit orchestrator, the UI dynamically filters the language dropdown choices based on the selected framework:

| Selected Framework | Allowed Language Options | Default Language Selection |
| :--- | :--- | :--- |
| **Selenium** | `Python` | `Python` |
| **Playwright** | `Python`, `JavaScript`, `TypeScript` | `Python` |
| **Cypress** | `JavaScript`, `TypeScript` | `JavaScript` |

### Interaction Rules
1. Changing the **Framework** dropdown automatically resets/filters the **Language** options to valid choices.
2. The UI delegates validation checking to `validate_framework_and_language()` from `src.validation.validator`.
3. The selected framework and language apply identically regardless of whether code was pasted or uploaded.

---

## 7. Script Input Design

The UI provides two equivalent input mechanisms that converge into a single script text buffer:

```text
              ┌───────────────────────────┐
              │   Paste Script Text       │
              └─────────────┬─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │   Script    │
                     │   Content   │ ───> Audit Orchestrator
                     │   Buffer    │      (src/services/audit_service.py)
                     └─────────────▲
                            │
              ┌─────────────┴───────────┐
              │   Upload Source File    │
              │   (.py, .js, .ts)       │
              └─────────────────────────┘
                     Read as UTF-8
```

### Path A: Paste Script
- User pastes code into `st.text_area`.
- If non-empty, the text area content becomes the primary script buffer.

### Path B: File Upload
- User uploads an individual file via `st.file_uploader`.
- Allowed file extensions: `.py`, `.js`, `.ts`.
- The UI reads the uploaded file stream as UTF-8 text (`uploaded_file.getvalue().decode("utf-8")`).
- The resulting text populates the script buffer.
- If both a pasted script and an uploaded file exist, the uploaded file takes precedence (or the UI clearly displays which input is currently active).

### Input Invariants
- Both paths converge prior to calling `ScriptInput(script_content=buffer, framework=framework, language=language)`.
- No separate audit pathways or backend services exist for pasted vs. uploaded scripts.
- Files are treated purely as untrusted text strings.

---

## 8. Application UI States

1. **Initial / Empty State:** UI displays header, framework/language selectors, empty text area, file uploader, and static notice. No audit results rendered.
2. **Empty Script State:** User clicks "Analyze" with empty text and no file. UI displays `st.warning("Please paste an automation script or upload a source file to analyze.")`. Analysis does not execute.
3. **Invalid Combination State:** If an invalid combo is selected, UI displays `st.error("Invalid framework and language combination.")` and disables analysis.
4. **Unsupported File Extension State:** User uploads a file with an unlisted extension (e.g. `.zip` or `.txt`). UI displays `st.error("Unsupported file type. Please upload a .py, .js, or .ts file.")`.
5. **Empty Uploaded File State:** Uploaded file contains 0 bytes or whitespace. UI displays `st.warning("Uploaded file is empty.")`.
6. **Valid Pasted Input State:** Non-empty script pasted. Analyze button active.
7. **Valid Uploaded Input State:** Valid `.py`/`.js`/`.ts` file uploaded. Analyze button active.
8. **Analyzing State:** User clicks "Analyze Script". UI displays `st.spinner("Performing static analysis and generating audit report...")`.
9. **Results Available State:** Analysis completes successfully. UI renders score metrics, scorecard table, detailed finding cards, recommendations, and methodology.
10. **Gemini Unavailable State:** Analysis succeeds but Gemini API is unconfigured/failed. UI renders complete deterministic report plus a warning banner: *"Gemini advisory enrichment is currently unavailable. Deterministic score and findings are fully intact."*
11. **No Findings State (100 / 100):** Script contains zero anti-pattern findings. UI displays `100 / 100`, `EXCELLENT` rating badge, and a success banner: *"No checklist anti-patterns detected. Great job!"*

---

## 9. Results & Hierarchy Design

The results presentation follows a strict informational hierarchy:

1. **Executive Score Summary:** High-level metrics at the very top.
2. **Deduction Scorecard:** Category breakdown detailing severity penalties.
3. **Confirmed Findings List:** Granular cards displaying line numbers, code snippets, and explanations.
4. **Actionable Recommendations:** Priority-ordered recommendations (High before Medium).
5. **Methodology Footer:** Standard audit boundaries and scoring rules.

### Metric Distinctions
- **Quality Score:** `0–100` deterministic score computed exclusively by severity deductions and category caps.
- **Rating Band:** `Excellent` (80–100), `Good` (60–79), `Fair` (50–59), `Poor` (0–49).
- **Anti-Patterns Detected:** Informational count of distinct category IDs (e.g. `2 / 10`). Explicitly documented as non-scoring.

---

## 10. Finding Card Presentation Layout

Each confirmed finding is rendered inside a structured card or expandable box:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔴 AP01 · Hardcoded Waits                            HIGH • Line 14     │
├─────────────────────────────────────────────────────────────────────────┤
│ Code Snippet:                                                           │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ time.sleep(5)                                                       │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ Detection Reason:                                                       │
│   Fixed delay is used instead of waiting for application state.         │
│                                                                         │
│ AI Explanation (Advisory):                                              │
│   Hardcoded pauses introduce execution flakiness and slow down tests.   │
│                                                                         │
│ AI Suggested Fix (Advisory):                                            │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ expect(page.locator('#submit')).to_be_visible()                     │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Presentation Rules
- **Severity Badge:** High severity uses a red indicator (`🔴 HIGH`); Medium severity uses an orange/yellow indicator (`🟡 MEDIUM`).
- **Line Reference:** Displayed prominently in bold (e.g., `Line 14` or `Lines 10–12`).
- **Code Formatting:** Code snippets and suggested fixes are rendered in syntax-highlighted code blocks (`st.code`).
- **Clear Attribution:** AI-generated explanations and suggested fixes are explicitly labelled as `(AI Advisory)` to prevent user confusion regarding detection authority.

---

## 11. Error & Failure UX

- **Empty Input:** User notification via `st.warning()`.
- **Unsupported Upload:** Rejection notification via `st.error()`.
- **Malformed Source Code:** Detectors handle syntax errors gracefully; UI displays findings discovered by robust regex scanning.
- **Gemini API Failure:** Displays static audit findings and scorecard cleanly; renders non-blocking warning banner for missing AI suggestions.
- **User Privacy:** No local file paths, stack traces, or internal credentials are ever displayed in error messages.

---

## 12. Accessibility & Usability

- **Typography & Hierarchy:** Clear heading sizes (`#`, `##`, `###`) to establish visual structure.
- **Dual Visual Indicators:** Severity uses both color badges and explicit text labels (`HIGH`, `MEDIUM`).
- **Code Legibility:** All source code snippets use monospace fonts (`st.code`).
- **Intuitive Controls:** Dropdowns and buttons feature clear, descriptive labels.
- **Single-Page Flow:** Sequential layout eliminates hidden options or confusing tab navigation.

---

## 13. UI → Application Flow Architecture

```text
User selects Framework & Language
               │
               ▼
User pastes script OR uploads file (.py, .js, .ts)
               │
               ▼
Streamlit UI extracts script text buffer
               │
               ▼
UI validates input (non-empty & supported combo)
               │
               ▼
Audit Orchestrator (src/services/audit_service.py)
               │
               ▼
Static Analysis Engine (AP01–AP10 Detectors)
               │
               ▼
Finding Normalizer & Deduplication (src/services/normalization_service.py)
               │
               ▼
Deterministic Scoring Engine (src/services/scoring_service.py)
               │
               ▼
Report Generator (src/services/report_service.py)
               │
               ▼
Gemini Advisory Enrichment (src/services/gemini_service.py)
               │
               ▼
Streamlit UI renders final AuditReport
```

---

## 14. Component Responsibility Boundaries

### The Streamlit UI explicitly DOES NOT:
- Execute anti-pattern detection rules.
- Calculate quality scores or apply severity penalties.
- Assign issue severities or confidence levels.
- Deduplicate or normalize findings.
- Execute, compile, or import submitted automation scripts.
- Execute uploaded source files.
- Open browsers, initiate WebDriver sessions, or perform network automation.
- Directly call the Google Gemini API (all API calls go through `GeminiService`).
- Scan repositories, parent folders, or surrounding file directories.
- Mutate user source code automatically.

---

## 15. Design Trade-Offs

- **What:** A single-page Streamlit web application supporting pasted or uploaded single-file automation scripts.
- **Why:** The utility has one core workflow: inspecting a test script for quality issues and displaying immediate results.
- **Why This Approach:** Supports both common developer habits (copy-pasting a snippet vs uploading a test file) without introducing backend complexity.
- **Trade-offs & Limitations:**
  - No persistent audit history or database storage.
  - No multi-file project/repository folder scanning.
  - No PDF/HTML report file exports.
  - No multi-user authentication or role management.

*Design Rationale:* **"We deliberately kept this simple because this is a lightweight v1 application."**

---

## 16. Implementation Boundary

> [!IMPORTANT]
> **Boundary Notice:** This document (`docs/ui-design.md`) defines the UI design specification for **T05** only.
> 
> - **T06 Implementation** will build the Streamlit UI (`app.py`), integrating script text area input, single-file upload (`.py`, `.js`, `.ts`), validation, and connecting to `audit_service`, `scoring_service`, `report_service`, and `gemini_service`.
> - Uploaded files will reuse the existing `ScriptInput` contract by reading file contents as plain text.
> - No source code modification or UI build execution was performed during this design step.
