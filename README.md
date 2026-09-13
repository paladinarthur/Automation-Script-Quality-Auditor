# Automation Script Quality Auditor

A lightweight web application that reviews **Selenium, Playwright, and Cypress** automation scripts against a fixed checklist of automation anti-patterns.

## What It Does

The auditor takes a script through the following workflow:

```text
Script Upload / Paste
        ↓
Framework Detection
        ↓
Anti-Pattern Analysis
        ↓
Scoring
        ↓
Quality Report
```

For each script, it provides:

- **Overall quality score**
- **Per-category scorecard**
- **Flagged issues**
- **Line references**
- **One-line suggested fix**

## Example Anti-Patterns

The initial checklist includes:

- Hard-coded / arbitrary waits
- Brittle or absolute XPath selectors
- Missing or weak assertions
- Hard-coded test data or credentials
- Duplicated code
- Large/monolithic test cases
- Test dependencies
- Poor exception handling
- Lack of reusable functions
- Poor naming/readability

## Tech Stack

- **Python**
- **Streamlit**
- **pytest**
- Python `ast` / pattern-based analysis
- Optional **Gemini/LLM** layer for improved explanations and fix suggestions

## Project Structure

```text
automation-script-quality-auditor/
├── app.py
├── auditor/
│   ├── analyzer.py
│   ├── detector.py
│   ├── scorer.py
│   └── models.py
├── rules/
│   ├── common_rules.py
│   ├── selenium_rules.py
│   ├── playwright_rules.py
│   └── cypress_rules.py
├── samples/
├── tests/
├── requirements.txt
└── README.md
```

## Output Example

```text
Overall Score: 72 / 100
Grade: C

HIGH   Line 18
Hard-coded wait detected.
Fix: Replace sleep with an explicit wait for the expected condition.

MEDIUM Line 23
Absolute XPath detected.
Fix: Use a stable ID, data attribute, or accessible locator.
```

## Scoring

Example weighting:

```text
Critical → -15
High     → -10
Medium   →  -5
Low      →  -2
```

Scores are mapped to grades from **A (excellent)** to **F (poor)**.

## STLC Alignment

The project will follow the Software Testing Life Cycle:

```text
Requirements
     ↓
Test Planning
     ↓
Test Design
     ↓
Implementation
     ↓
Testing
     ↓
Defect Tracking
     ↓
Test Summary
```

Key artifacts will include:

- Requirements / user stories
- Acceptance criteria
- Test scenarios and test cases
- Traceability matrix
- Defect log
- Test execution report
- Test summary report

## MVP Definition

The MVP is complete when a user can upload/paste a supported automation script and receive a clear, actionable report showing:

**What is wrong → Where it is → How serious it is → How to fix it.**
