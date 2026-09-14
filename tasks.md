# Planned Work Breakdown

**Project:** Automation Script Quality Auditor  
**STLC Phase:** Phase 1 — Requirement Analysis & Planning  

---

## Task Matrix

| ID | Task | Area | Description | Status |
| :--- | :--- | :--- | :--- | :--- |
| **T01** | Document project requirements | Requirements | Produce comprehensive SRS covering objectives, user persona, features, NFRs, scope, and user stories. | **DONE** |
| **T02** | Define supported frameworks | Requirements | Detail language bindings and conventions for Selenium, Playwright, and Cypress. | **DONE** |
| **T03** | Define anti-pattern checklist | Analysis | Formalize detection rules and patterns for the initial 7 anti-pattern categories. | **DONE** |
| **T04** | Define scoring system | Scoring | Formulate the mathematical deduction and weighting algorithm for quality scoring (0–100). | **DONE** |
| **T05** | Design simple Streamlit UI | UI | Wireframe and plan the Streamlit layout (input panels, scorecard, and issue lists). | **TODO** |
| **T06** | Implement script input | Input | Build text-area paste mechanism and file uploader component in Streamlit. | **BACKLOG** |
| **T07** | Implement framework selection | Input | Implement framework picker (Selenium, Playwright, Cypress) to drive active rules. | **BACKLOG** |
| **T08** | Implement anti-pattern detection | Analysis | Code the rule evaluation engine to detect anti-patterns against the script text. | **BACKLOG** |
| **T09** | Implement line number tracking | Analysis | Map detected anti-pattern occurrences to precise script line numbers and extract snippets. | **BACKLOG** |
| **T10** | Implement score calculation | Scoring | Code the scoring logic and integrate results into the scorecard view. | **BACKLOG** |
| **T11** | Generate issue report | Reporting | Present categorized issues with offending lines and code snippets in the UI. | **BACKLOG** |
| **T12** | Integrate Gemini for fix suggestions | Reporting | Attach AI-generated explanations and one-line remediation advice to each detected violation using Gemini. | **BACKLOG** |
| **T13** | Add sample scripts | Testing | Create test automation scripts demonstrating clean patterns and specific anti-patterns. | **BACKLOG** |
| **T14** | Test auditor against sample scripts | Testing | Execute system tests verifying detection accuracy and scoring correctness. | **BACKLOG** |
| **T15** | Improve UI based on testing | UI | Refine UI usability, visual hierarchy, and feedback messages based on test findings. | **BACKLOG** |
| **T16** | Complete project documentation | Documentation | Finalize user instructions, code documentation, and STLC summary report. | **BACKLOG** |

---

## Traceability to User Stories

| User Story | Associated Tasks |
| :--- | :--- |
| **US-01: Submit Script** | T01, T05, T06 |
| **US-02: Select Framework** | T01, T02, T05, T07 |
| **US-03: Analyze Script** | T01, T03, T08 |
| **US-04: View Score** | T01, T04, T10 |
| **US-05: View Issues** | T01, T03, T09, T11 |
| **US-06: Get Fix Suggestions** | T01, T03, T12 |
| **US-07: Understand Results** | T01, T05, T11, T15 |

---

*Refer to [kanban.md](kanban.md) for current workflow progression and [requirements.md](requirements.md) for requirements specification.*
