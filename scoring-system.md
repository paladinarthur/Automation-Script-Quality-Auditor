# Automation Script Quality Auditor — Scoring System

## 1. Purpose

Define the deterministic v1 scoring system used to convert confirmed anti-pattern findings into an overall automation script quality score.

The score is intended to provide a simple, understandable indication of script quality based on the fixed anti-pattern checklist defined in `anti-pattern-checklist.md`.

The scoring system must remain lightweight and explainable.

---

# 2. Score Range

## What

The auditor uses a score from:

**0 to 100**

Where:

* **100** represents a script with no detected anti-patterns.
* **0** represents a script whose detected issues result in the maximum possible deductions.

The score must never be below 0.

## Why

A 0–100 scale is intuitive and provides enough granularity to distinguish between scripts with different levels of detected issues.

A 0–10 scale was considered but rejected because it provides less granularity and makes individual deductions less natural.

## Design Decision

The score is always represented as:

`X / 100`

Example:

`82 / 100`

---

# 3. Base Score

## What

Every script starts with:

**100 points**

The final score is calculated by deducting penalties associated with confirmed findings.

Conceptually:

`Final Score = 100 - Total Penalty`

The result is clamped to a minimum of 0.

## Why

Starting from a perfect score and deducting for detected problems makes the scoring model easy to understand.

It also means that:

**No detected issues = 100 / 100**

---

# 4. Severity-Based Penalties

The scoring system uses the severity assigned to each anti-pattern finding.

### Penalty table

| Severity | Penalty per finding | Maximum penalty per anti-pattern |
| -------- | ------------------: | -------------------------------: |
| High     |                 −10 |                              −20 |
| Medium   |                  −4 |                              −20 |

There are currently no Low-severity anti-patterns in the v1 checklist.

## Why

Severity-weighted deductions are simpler and more defensible than giving every anti-pattern an arbitrary individual weight.

For example, a High-severity issue should affect the score more than a Medium-severity issue.

The scoring system therefore uses severity as the single factor determining the size of the deduction.

---

# 5. No Individual Anti-Pattern Weights

## What

Different anti-patterns do NOT receive different scoring multipliers.

For example:

* AP01 High → −10
* AP09 High → −10
* AP02 Medium → −4
* AP06 Medium → −4

The anti-pattern's severity determines its score impact.

## Why

Individual weights would introduce additional arbitrary assumptions about which anti-pattern is "more important."

The project is a lightweight v1 auditor, so keeping the model consistent and easy to explain is preferred.

The anti-pattern definitions already communicate their relative importance through severity.

---

# 6. Repeated Findings

## What

Multiple findings of the same anti-pattern use linear deductions until a maximum penalty of 20 points for that anti-pattern is reached.

### High severity

A High-severity anti-pattern:

* 1 finding → −10
* 2 findings → −20
* 3+ findings → −20 maximum

### Medium severity

A Medium-severity anti-pattern:

* 1 finding → −4
* 2 findings → −8
* 3 findings → −12
* 4 findings → −16
* 5+ findings → −20 maximum

## Why

Without a per-anti-pattern cap, a script with many instances of one anti-pattern could have its score dominated by that single category.

The cap keeps the scoring balanced across the 10 anti-pattern categories while remaining simple.

## Design Decision

The cap is applied **per anti-pattern**, not globally.

For example, AP06 can contribute at most −20, while AP07 can independently contribute at most −20.

---

# 7. No Score Normalization by Script Size

## What

The score does NOT use:

* Lines of code
* Issue density
* Issues per 100 lines
* Script length normalization

A finding has the same severity-based score impact regardless of script length.

## Why

The project is a lightweight v1 application.

Normalizing by script size would require additional assumptions about:

* Minimum script length
* Appropriate issue density
* What constitutes a "large" script
* How different frameworks should be compared

Those calculations add complexity without being necessary for the core purpose of the auditor.

## Trade-off

A 20-line script and a 200-line script with the same confirmed findings may receive the same score.

This is an intentional simplification for v1.

---

# 8. Confidence Does Not Affect Score

## What

Detection confidence is displayed as metadata but does NOT change the score.

For example:

* High-confidence Medium issue → −4
* Medium-confidence Medium issue → −4

## Why

Severity and confidence represent different concepts:

**Severity:** How significant is the issue?

**Confidence:** How certain is the analyzer that the detected issue is actually present?

Using confidence as another scoring multiplier would make the score harder to understand.

Therefore:

> Severity determines score impact.
> Confidence communicates detection certainty.

---

# 9. Deduplication Before Scoring

## What

The scoring engine operates on the **final deduplicated finding list**, not raw detector matches.

The processing flow is:

```text
Submitted Script
      ↓
Static Analysis
      ↓
Raw Findings
      ↓
Deduplication / Overlap Resolution
      ↓
Final Findings
      ↓
Score Calculation
      ↓
Final Score
```

## Why

Multiple rules can sometimes identify the same underlying problem.

The auditor should not unfairly penalize the same issue multiple times simply because more than one detector recognized it.

### Known example

```python
time.sleep(5)
```

must produce:

**AP01 — Hardcoded Wait**

It should not additionally produce AP02 or AP10 for the same hardcoded wait.

AP03 and AP05 may both apply only when they represent genuinely distinct findings.

## Design Decision

Score only the final findings presented to the user.

---

# 10. No Findings

## What

If no anti-patterns are detected:

**Score = 100 / 100**

**Rating = Excellent**

## Why

The auditor should not artificially deduct points when no issues from its defined checklist are detected.

## Important Limitation

A score of 100 means:

> No anti-patterns from the auditor's v1 checklist were detected.

It does NOT mean:

> The script is guaranteed to be perfect.

The auditor only evaluates the patterns defined in its checklist.

---

# 11. Rating Bands

The final score is mapped to one of four ratings.

|  Score | Rating    |
| -----: | --------- |
| 80–100 | Excellent |
|  60–79 | Good      |
|  50–59 | Fair      |
|   0–49 | Poor      |

## Why

These bands provide a simple qualitative interpretation of the numeric score.

The bands are intentionally broad because the scoring model itself is lightweight.

They should not be presented as an industry-wide universal standard.

---

# 12. Final Score Calculation

The calculation should conceptually follow:

```text
Base Score = 100

For each anti-pattern:
    Calculate its severity-based penalty
    Apply the maximum −20 cap for that anti-pattern

Total Penalty = sum of all anti-pattern penalties

Final Score = max(0, 100 - Total Penalty)
```

### Example

Suppose a script has:

* AP01 — 1 High finding
* AP02 — 2 Medium findings
* AP06 — 3 Medium findings
* AP07 — 1 High finding

Calculation:

```text
AP01 = −10
AP02 = −8
AP06 = −12
AP07 = −10

Total Penalty = −40

Final Score = 100 − 40
            = 60 / 100
```

Rating:

**60 / 100 — Good**

---

# 13. Scorecard Output

The scorecard should provide enough information for the user to understand the result quickly.

### Required scorecard information

* Overall Score
* Rating
* Total Issues
* High-Severity Issues
* Medium-Severity Issues
* Anti-patterns Detected
* Anti-pattern breakdown

Example:

```text
Quality Score: 72 / 100
Rating: Good

Total Issues: 7
High Severity: 2
Medium Severity: 5

Anti-patterns Detected: 4 / 10
```

### Anti-pattern breakdown

```text
AP01 — Hardcoded Waits           1
AP02 — Magic Numbers             0
AP03 — Duplicated Code           2
AP04 — Poor Test Structure       0
AP05 — Missing Abstractions      1
...
```

## Important

The number of anti-pattern categories detected (`4 / 10`) is informational only.

It is NOT used to calculate the score.

The score is calculated exclusively from confirmed findings and their severity.

---

# 14. Audit Report Structure

The final audit result should use the following structure.

## 14.1 Executive Summary

Show:

* Overall score
* Rating
* Total issues
* High-severity issues
* Medium-severity issues
* Key strengths
* Critical areas for improvement

Example:

```text
Overall Score: 72 / 100 — Good

Total Issues: 7
High Severity: 2
Medium Severity: 5
```

Key strengths and improvement areas should be based on the detected findings.

---

## 14.2 Scorecard

Show:

* Overall score
* Rating
* Issue counts by severity
* Anti-pattern breakdown

---

## 14.3 Findings

Each finding should contain:

* Anti-pattern
* Severity
* Confidence
* Line number or line range
* Relevant code snippet
* Why it matters
* Suggested fix

The suggested fix is generated by Gemini later.

---

## 14.4 Recommendations

Group recommendations by priority:

### High Priority

High-severity findings.

### Medium Priority

Medium-severity findings.

Recommendations should be concise and actionable.

No separate scoring system should be introduced for recommendations.

---

## 14.5 Methodology

The audit report should briefly explain:

* Static-analysis approach
* Fixed 10-pattern checklist
* Scoring formula
* Severity-based deductions
* Deduplication
* Gemini's role
* Secret redaction
* Known limitations

---

# 15. Gemini's Role in Scoring

Gemini must NOT:

* Calculate the score
* Choose the severity
* Decide whether an anti-pattern exists
* Override a detector finding
* Add new findings

Gemini is used only after a finding has been confirmed.

Gemini may generate:

1. A short explanation of the confirmed issue.
2. A concise suggested fix.

The deterministic scoring engine calculates the score independently.

## Why

This makes the score:

* Reproducible
* Explainable
* Consistent
* Independent of AI-generated opinions

It also demonstrates a clear separation between deterministic analysis and generative AI.

---

# 16. Secret Handling

Any secret detected by AP09 must be redacted before relevant code context is sent to Gemini.

For example:

Original:

```python
password = "SuperSecret123!"
```

Context sent to Gemini:

```python
password = "[REDACTED]"
```

## Why

The auditor should not expose credentials or secret values to an external AI service unnecessarily.

This is a deliberate security and privacy measure.

---

# 17. What the Scoring System Does Not Measure

The score should NOT claim to measure:

* Overall software quality
* Application correctness
* Browser compatibility
* Test execution success
* Application performance
* Code security as a whole
* Complete test coverage
* Production readiness
* Maintainability in every possible sense

The score only represents the quality indicated by the auditor's defined v1 anti-pattern checklist.

---

# 18. Trade-offs

The v1 model intentionally prioritizes:

**Simplicity > mathematical sophistication**

Advantages:

* Easy to implement
* Easy to test
* Easy to explain
* Deterministic
* Easy for users to understand
* Suitable for a lightweight Streamlit application

Limitations:

* Does not account for script size
* Does not account for issue density
* Does not distinguish between individual anti-pattern types beyond severity
* Does not use confidence in scoring
* Does not measure quality outside the defined checklist
* Fixed penalty values may need recalibration in a future version

These limitations are intentional rather than accidental.

---

# 19. Design Decision Summary

| Decision                  | Choice          | Reason                            |
| ------------------------- | --------------- | --------------------------------- |
| Score range               | 0–100           | Intuitive and granular            |
| Starting score            | 100             | Simple deduction model            |
| High penalty              | −10             | Higher impact for serious issues  |
| Medium penalty            | −4              | Lower impact for moderate issues  |
| Per-pattern cap           | −20             | Prevents one category dominating  |
| Individual weights        | None            | Avoids arbitrary rule weighting   |
| Script-size normalization | None            | Keeps v1 simple                   |
| Confidence weighting      | None            | Separates severity from certainty |
| Deduplication             | Before scoring  | Prevents duplicate penalties      |
| No findings               | 100 / Excellent | No artificial penalty             |
| Rating bands              | 4 levels        | Simple interpretation             |
| Gemini scoring            | Not allowed     | Keeps score deterministic         |

---

# 20. Implementation Boundary

This document defines the scoring model only.

Do not implement:

* Scoring code
* Streamlit UI
* Gemini integration
* Anti-pattern detection
* Test cases

Those belong to later implementation stages.

The scoring implementation must follow this document when T04 moves into the implementation phase.

---

# 21. Completion Criteria

T04 is complete when:

* `scoring-system.md` exists in the project root.
* The 0–100 score range is documented.
* Starting score is documented.
* Severity penalties are documented.
* Per-anti-pattern caps are documented.
* Rating bands are documented.
* Repeated findings are documented.
* Deduplication before scoring is documented.
* Confidence is explicitly excluded from scoring.
* Script-size normalization is explicitly excluded.
* No-findings behavior is documented.
* Scorecard output is documented.
* Audit report structure is documented.
* Gemini's scoring limitations are documented.
* Secret redaction is documented.
* Trade-offs and limitations are documented.
* No scoring implementation code has been added yet.
