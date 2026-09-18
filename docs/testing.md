# T14: Prove Phase Testing Documentation

## 1. Overview
Scope of PROVE phase testing against the 5 sample scripts and core engine limits.

## 2. Test Execution Requirements
- Environment setup: Python 3.12 / Pytest 9.1
- Verification of test boundaries.

## 3. Test Cases & Execution Log

### 3.1 End-to-End Sample Script Validation
*Verified manually using Streamlit UI and locally via orchestrator pipeline.*

| Test ID | Input file | Intended Patterns | Expected Detector Behavior | Actual Observed Findings | Expected Score | Actual Score | PASS/FAIL | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T14-E2E-01** | `selenium_python/login_test.py` | AP01, AP06, AP07, AP09, AP10 | AP01 (High), AP06 (Med), AP07 (High), AP09 (High), AP10 (2x Med) | AP01, AP06, AP07, AP09, AP10 (2x) | 58 / 100 FAIR | 58 / 100 FAIR | **PASS** | Penalty: 10 + 4 + 8 + 10 + 10 = 42 |
| **T14-E2E-02** | `playwright_python/checkout_test.py` | AP01, AP06, AP07, AP09 | AP01 (2x High), AP06 (Med), AP07 (High) | AP01 (2x), AP06, AP07 | 66 / 100 GOOD | 66 / 100 GOOD | **PASS** | AP09 intentionally excluded ("fake"). AP01 capped at 20. Penalty: 20 + 4 + 10 = 34 |
| **T14-E2E-03** | `playwright_typescript/profile_test.ts` | AP01, AP06, AP07, AP09 | AP06 (Med), AP01 (High), AP07 (High) | AP06, AP01, AP07 | 76 / 100 GOOD | 76 / 100 GOOD | **PASS** | AP09 intentionally excluded ("fake"). Penalty: 4 + 10 + 10 = 24 |
| **T14-E2E-04** | `cypress_javascript/search_test.js` | AP01, AP06, AP07, AP09 | AP01 (High), AP06 (Med), AP07 (High) | AP01, AP06, AP07 | 76 / 100 GOOD | 76 / 100 GOOD | **PASS** | AP09 intentionally excluded ("fake"). Penalty: 10 + 4 + 10 = 24 |
| **T14-E2E-05** | `cypress_typescript/purchase_test.ts` | AP01 | AP01 (High) | AP01 | 90 / 100 EXCELLENT | 90 / 100 EXCELLENT | **PASS** | Penalty: 10 |

### 3.2 Functional & Edge Cases
*Verified via automated pytest suite (`test_validation.py`, `test_audit_service.py`, `test_finding_normalization.py`).*

| Test ID | Description | Result | PASS/FAIL |
| :--- | :--- | :--- | :--- |
| **T14-FUNC-01** | Valid supported framework/language | Code executes | **PASS** |
| **T14-FUNC-02** | Invalid combo (e.g., Cypress/Python) | Validation error | **PASS** |
| **T14-FUNC-03** | Empty script payload | 0 issues, Score 100 | **PASS** |
| **T14-FUNC-04** | Whitespace-only script | 0 issues, Score 100 | **PASS** |
| **T14-FUNC-05** | Malformed source syntax | Parsers fallback/fail gracefully | **PASS** |
| **T14-FUNC-06** | Flawless script (no findings) | 0 issues, Score 100 | **PASS** |
| **T14-FUNC-07** | Duplicate / Overlapping findings | Deduplicated | **PASS** |
| **T14-FUNC-08** | Unsupported file extension input | Gracefully rejected | **PASS** |

### 3.3 Scoring Engine Validation
*Verified via automated pytest suite (`test_scoring_service.py`).*

| Test ID | Description | Result | PASS/FAIL |
| :--- | :--- | :--- | :--- |
| **T14-SCORE-01** | Base Score Verification | Max score is exactly 100 | **PASS** |
| **T14-SCORE-02** | High Severity Penalty | Single High deduction is exactly -10 | **PASS** |
| **T14-SCORE-03** | Medium Severity Penalty | Single Medium deduction is exactly -4 | **PASS** |
| **T14-SCORE-04** | Maximum Penalty Cap | Caps at -20 total deduction | **PASS** |
| **T14-SCORE-05** | Score Floor | Scores bottom out at 0 | **PASS** |
| **T14-SCORE-06** | Excluded Variables | Finding confidence does not modify penalty | **PASS** |

### 3.4 Gemini Integration & Resilience
*Verified via automated pytest suite (`test_gemini_service.py`).*

| Test ID | Description | Result | PASS/FAIL |
| :--- | :--- | :--- | :--- |
| **T14-GEM-01** | Live API Enrichment (Happy Path) | Explanations/fixes generated via UI | **PASS** |
| **T14-GEM-02** | Immutable Metadata | Score metadata unchanged | **PASS** |
| **T14-GEM-03** | Missing API Key Fallback | Mocked absence gracefully handled | **PASS** |
| **T14-GEM-04** | Network/API Failure Fallback | Mocked timeout/network gracefully handled | **PASS** |

### 3.5 Secret Protection & Redaction
*Verified via automated pytest suite (`test_gemini_service.py`, `test_ap09.py`).*

| Test ID | Description | Result | PASS/FAIL |
| :--- | :--- | :--- | :--- |
| **T14-SEC-01** | Detect hardcoded secret | AP09 flags generic secrets | **PASS** |
| **T14-SEC-02** | Exclude known placeholders | Known synthetic placeholders are excluded | **PASS** |
| **T14-SEC-03** | Redact before Gemini transit | Secret scrubbed from `code_snippet` and `reason` | **PASS** |

### 3.6 Automated Regression Baseline
*Full suite execution log.*

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\New Automation Script Auditor
plugins: anyio-4.15.1
collected 307 items

tests\test_ap01.py ..........................                            [  8%]
tests\test_ap02.py .......................                               [ 15%]
tests\test_ap03.py .............                                         [ 20%]
tests\test_ap04.py ..............                                        [ 24%]
tests\test_ap05.py ..........                                            [ 28%]
tests\test_ap06.py ......................                                [ 35%]
tests\test_ap07.py ..................                                    [ 41%]
tests\test_ap08.py ...................                                   [ 47%]
tests\test_ap09.py ....................                                  [ 53%]
tests\test_ap10.py ...................                                   [ 59%]
tests\test_audit_service.py ..................                           [ 65%]
tests\test_finding_normalization.py ............                         [ 69%]
tests\test_gemini_service.py .................                           [ 75%]
tests\test_models.py .......                                             [ 77%]
tests\test_report_service.py ...........                                 [ 81%]
tests\test_scoring_service.py .......................                    [ 88%]
tests\test_ui.py ............                                            [ 92%]
tests\test_validation.py .......................                         [100%]

============================= 307 passed in 6.65s =============================
```

## 4. Known Limitations
- Cypress JavaScript vs TypeScript differentiation uses separate logic but does not parse full AST, meaning some complex syntax could potentially fall back to regex checks.
