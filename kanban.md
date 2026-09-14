# Project Kanban Board

**Project:** Automation Script Quality Auditor  
**Current STLC Phase:** Phase 1 — Requirement Analysis & Planning  
**Last Updated:** Phase 1 Baseline

---

## Kanban Board

| BACKLOG | TODO | IN PROGRESS | TESTING | DONE |
| :--- | :--- | :--- | :--- | :--- |
| **[T06]** Implement script input | **[T05]** Design simple Streamlit UI | *(Empty)* | *(Empty)* | **[T01]** Document project requirements |
| **[T07]** Implement framework selection | | | | **[T02]** Define supported frameworks |
| **[T08]** Implement anti-pattern detection | | | | **[T03]** Define anti-pattern checklist |
| **[T09]** Implement line number tracking | | | | **[T04]** Define scoring system |
| **[T10]** Implement score calculation | | | | |
| **[T11]** Generate issue report | | | | |
| **[T12]** Integrate Gemini for fix suggestions | | | | |
| **[T13]** Add sample scripts | | | | |
| **[T14]** Test auditor against sample scripts | | | | |
| **[T15]** Improve UI based on testing | | | | |
| **[T16]** Complete project documentation | | | | |

---

## Column Descriptions & Transition Rules

1. **BACKLOG**: Identified future tasks scheduled for subsequent STLC phases.
2. **TODO**: Tasks prioritized and ready to be worked on in the active STLC phase.
3. **IN PROGRESS**: Active tasks currently under development or drafting.
4. **TESTING**: Completed implementation undergoing verification, rule evaluation, or user review.
5. **DONE**: Finished and verified tasks fulfilling all acceptance criteria.

---

## Detailed Task Cards by Column

### 📋 TODO
* **[T05] Design simple Streamlit UI**
  * *Area:* UI | *Target Phase:* Phase 2
  * *Description:* Wireframe and plan the Streamlit layout (input panels, scorecard, and issue lists).

---

### 📦 BACKLOG
* **[T06] Implement script input**
  * *Area:* Input | *Target Phase:* Phase 3
* **[T07] Implement framework selection**
  * *Area:* Input | *Target Phase:* Phase 3
* **[T08] Implement anti-pattern detection**
  * *Area:* Analysis | *Target Phase:* Phase 3
* **[T09] Implement line number tracking**
  * *Area:* Analysis | *Target Phase:* Phase 3
* **[T10] Implement score calculation**
  * *Area:* Scoring | *Target Phase:* Phase 3
* **[T11] Generate issue report**
  * *Area:* Reporting | *Target Phase:* Phase 3
* **[T12] Integrate Gemini for fix suggestions**
  * *Area:* Reporting | *Target Phase:* Phase 3
* **[T13] Add sample scripts**
  * *Area:* Testing | *Target Phase:* Phase 4
* **[T14] Test auditor against sample scripts**
  * *Area:* Testing | *Target Phase:* Phase 4
* **[T15] Improve UI based on testing**
  * *Area:* UI | *Target Phase:* Phase 4
* **[T16] Complete project documentation**
  * *Area:* Documentation | *Target Phase:* Phase 5

---

### 🔄 IN PROGRESS
*(No tasks currently in progress)*

---

### 🧪 TESTING
*(No tasks currently in testing)*

---

### ✅ DONE
* **[T01] Document project requirements**
  * *Area:* Requirements
  * *Artifact:* `requirements.md`
  * *Description:* Created comprehensive SRS covering objectives, user persona, features, NFRs, scope, and user stories.
* **[T02] Define supported frameworks**
  * *Area:* Requirements
  * *Artifact:* `framework-support.md`
  * *Description:* Formally defined supported frameworks (Selenium, Playwright, Cypress), supported language bindings, static analysis operational boundaries, and common vs framework-aware rules.
* **[T03] Define anti-pattern checklist**
  * *Area:* Analysis
  * *Artifact:* `anti-pattern-checklist.md`
  * *Description:* Formally defined fixed v1 checklist of 10 anti-patterns (AP01–AP10), detection heuristics, exclusions, severity, confidence, and cross-cutting rules.
* **[T04] Define scoring system**
  * *Area:* Scoring
  * *Artifact:* `scoring-system.md`
  * *Description:* Formulated the deterministic v1 scoring model: 0–100 scale, starting score 100, severity-based deductions (-10 High, -4 Medium), -20 per-pattern cap, 4 rating bands, deduplication, and report structure.

---

*See [tasks.md](tasks.md) for the full tabular Planned Work Breakdown and [requirements.md](requirements.md) for requirements specification.*
