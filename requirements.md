# Software Requirements Specification (SRS)
## Automation Script Quality Auditor

**STLC Phase:** Phase 1 — Requirement Analysis & Planning  
**Status:** Approved / Baselined for Phase 1  
**Project Type:** Educational & Practical QA Project (Non-Enterprise / Non-Production)

---

## 1. Project Overview

The **Automation Script Quality Auditor** is a lightweight, educational utility designed to assess the code quality of test automation scripts. Automation engineers often encounter anti-patterns such as brittle locators, hardcoded delays, or missing assertions that lead to flaky and unmaintainable test suites. 

This application provides a simple, interactive interface where a user can supply an automation script, choose the corresponding automation framework (Selenium, Playwright, or Cypress), and evaluate the script against a curated set of quality checks. The tool produces an actionable report highlighting detected anti-patterns, precise line references, one-line remediation suggestions, and a composite quality score.

---

## 2. Objective

The primary objectives of the application are:
* To provide automation testers and QA engineers with immediate feedback on common script-level anti-patterns.
* To encourage best practices in automated testing across Selenium, Playwright, and Cypress suites.
* To present quality findings in an accessible scorecard format featuring line numbers and straightforward fix suggestions.
* To maintain an uncomplicated, educational architecture prioritizing readability and simplicity over enterprise-grade complexity.

---

## 3. Target User

* **Primary Persona:** Automation Tester / QA Engineer.
* **User Context:** The user wants to inspect their automated test scripts quickly for bad practices and maintainability issues before committing code or while learning framework best practices.
* **User Tenancy & Access:** A single user operating locally. There are no multi-user roles, access control levels, or authentication requirements.

---

## 4. Core Features

### 4.1 Script Input
* The user can input an automation script into the tool.
* Supported input methods:
  * Direct code paste into an interactive text area.
  * File upload (uploading `.py`, `.js`, `.ts`, or related script files).

### 4.2 Framework Selection
* The user can explicitly select the automation framework corresponding to the script:
  * **Selenium** (e.g., Python / JS bindings)
  * **Playwright** (e.g., Python / JS / TS bindings)
  * **Cypress** (e.g., JS / TS)
* The selected framework determines the active rule set and anti-pattern definitions applied during analysis.

### 4.3 Anti-pattern Analysis
* The engine evaluates the provided script against a predefined rule checklist tailored to automation testing.
* The analysis parses lines, identifies matching anti-pattern signatures, and flags violations.

### 4.4 Quality Scorecard
* An aggregated summary displaying:
  * Overall Quality Score (e.g., `72/100`).
  * Total checks executed and passed.
  * Total issues and warnings detected.
  * Quick visual status indicator (e.g., Good / Needs Attention / Poor).

### 4.5 Issue Report & Actionable Suggestions
* A detailed breakdown of all detected anti-patterns containing:
  * **Anti-Pattern Name:** Clear identifier (e.g., "Hardcoded Wait").
  * **Line Reference:** Specific line number(s) in the script where the violation occurs.
  * **Issue Snippet / Explanation:** Short explanation of why the line represents a problem.
  * **One-Line Suggested Fix:** A concise, practical remediation statement (e.g., "Replace the fixed delay with an explicit wait for the required element/state.").

---

## 5. Initial Anti-Pattern Categories

The analysis engine evaluates scripts against seven initial anti-pattern categories:

| Category | Description | Representative Example |
| :--- | :--- | :--- |
| **Hardcoded Waits** | Arbitrary time sleeps pausing execution unconditionally. | `time.sleep(5)`, `cy.wait(5000)`, `page.waitForTimeout(5000)` |
| **Fragile Locators** | Brittle locators prone to breaking upon UI restructuring. | Absolute XPaths (`/html/body/div[1]/...`), index-based DOM paths |
| **Missing Assertions** | Test blocks or test scripts performing actions without verification. | Scripts with navigation and click steps but no `assert`, `expect()`, or `should()` |
| **Duplicated Code** | Repeated sequences of setup, teardown, or selector actions without re-use. | Duplicated login sequences or repetitive selector queries |
| **Hardcoded Test Data** | Sensitive or environment-specific data embedded directly into code. | Inline passwords, raw credentials, or hardcoded environment URLs |
| **Poor Test Structure** | Lack of standardized test hooks, test runners, or block structuring. | Flat, unstructured scripts lacking setup/teardown encapsulation |
| **Missing Error Handling** | Actions vulnerable to transient failures without graceful recovery or context. | Unhandled dialogs, missing step failure diagnostics, or blank catches |

*(Note: The exact checklist, syntax regexes, and AST/string rules will be finalized during STLC Phase 2.)*

---

## 6. Expected Output

Upon triggering an analysis, the auditor presents two primary outputs:

### 6.1 Quality Scorecard
```text
Score: 72/100
Passed Checks: 4/7
Detected Issues: 3
Warnings: 1
```

### 6.2 Detailed Issue Report
For each flagged violation:
* **Anti-Pattern:** Hardcoded Wait
* **Location:** Line 12
* **Code:** `time.sleep(5)`
* **Explanation:** Hardcoded pauses introduce test flakiness and slow down execution.
* **Suggested Fix:** Replace the fixed delay with an explicit wait for the required element/state.

---

## 7. Non-Functional Requirements (NFR)

* **NFR-01: Simplicity & Readability** — Codebase architecture must remain lightweight, linear, and straightforward to serve as an educational reference.
* **NFR-02: Rapid Feedback** — Analysis execution must complete within 2 seconds for typical automation scripts (up to 500 lines of code).
* **NFR-03: Zero External Infrastructure** — Operates fully offline without databases, cloud services, external APIs, or external daemons.
* **NFR-04: Portability** — Runs on any standard Python environment using straightforward pip dependencies.
* **NFR-05: Usability** — Interface must be intuitive, requiring zero user onboarding or documentation reading to perform an audit.

---

## 8. Technology Direction

* **Core Programming Language:** Python (>= 3.9)
* **User Interface Framework:** Streamlit
* **Analysis Mechanism:** Python-based rule parsing (regex pattern matching / line-by-line static inspection)
* **Architecture Philosophy:** Simple → Understandable → Effective. No microservices, no databases, no external AI/LLM dependencies, and no enterprise scaffolding.

---

## 9. Project Scope

### In-Scope
* Single-page Streamlit web application.
* Script ingestion through copy-pasting or file upload.
* Framework-specific rule targeting (Selenium, Playwright, Cypress).
* Detection of the 7 initial anti-pattern categories.
* Line number tracking and code snippet extraction.
* Scoring algorithm translating rule compliance into a numerical quality score (0–100).
* Clean reporting table and suggestion cards in the Streamlit UI.
* Curated sample scripts (both clean and anti-pattern laden) for demonstration and validation.

### Out-of-Scope
* User accounts, login, roles, permissions, or session management.
* Persistent database storage (PostgreSQL, SQLite, Firebase, etc.).
* Historical trend analysis or historical audit logs.
* Dynamic test execution or sandbox execution (scripts are analyzed statically, never executed).
* Automated code refactoring or auto-fixing of user files.
* Support for non-web automation frameworks (e.g., Appium, Robot Framework, RestAssured).
* Enterprise reporting formats (e.g., PDF generation, JIRA ticket integration, CI/CD webhook notifications).
* Cloud hosting or multi-tenant deployment architecture.

---

## 10. User Stories

### US-01 — Submit Script
* **As an** automation tester,  
* **I want to** paste or upload an automation script,  
* **So that I can** evaluate its quality.  
* **Acceptance Criteria:**
  * User can paste raw script code into a multiline text area.
  * User can upload a script file from their local file system.
  * System alerts the user if the input is empty upon submission.

### US-02 — Select Framework
* **As an** automation tester,  
* **I want to** select the automation framework,  
* **So that the auditor can** apply relevant checks.  
* **Acceptance Criteria:**
  * User can select from Selenium, Playwright, or Cypress via a dropdown or radio button.
  * Changing the framework updates the active rules applied during analysis.

### US-03 — Analyze Script
* **As an** automation tester,  
* **I want the application to** analyze my script against predefined anti-patterns,  
* **So that I can** identify quality issues.  
* **Acceptance Criteria:**
  * Clicking an "Analyze Script" button initiates evaluation.
  * The script is evaluated against the selected framework's checklist.
  * Analysis finishes in near real-time.

### US-04 — View Score
* **As an** automation tester,  
* **I want to** see a quality score,  
* **So that I can** quickly understand the overall quality of my script.  
* **Acceptance Criteria:**
  * Scorecard displays a normalized score out of 100.
  * Displays counts of passed checks, detected issues, and warnings.

### US-05 — View Issues
* **As an** automation tester,  
* **I want to** see detected issues with line references,  
* **So that I can** locate problems in my script.  
* **Acceptance Criteria:**
  * Issues list the anti-pattern name, offending line number, and offending code snippet.
  * Issues are sorted in chronological order of line occurrence.

### US-06 — Get Fix Suggestions
* **As an** automation tester,  
* **I want a** suggested fix for each detected issue,  
* **So that I know** how to improve the script.  
* **Acceptance Criteria:**
  * Each reported issue includes a single, clear recommendation line on how to remediate the defect.

### US-07 — Understand Results
* **As an** automation tester,  
* **I want the** results to be presented clearly,  
* **So that I can** easily understand what needs improvement.  
* **Acceptance Criteria:**
  * Results are organized into intuitive visual sections (Scorecard summary, followed by granular Issue cards or table).
  * Clear visual feedback is provided if no issues are detected (perfect score).
