# Automation Script Quality Auditor

A lightweight static analysis tool that inspects Selenium, Playwright, and Cypress test automation scripts to identify anti-patterns, calculate quality scores, and provide AI-assisted remediation advice.

## Current Status

**Implementation Complete / Handover Preparation**
The core application, static detectors, scoring, and UI have been fully implemented and tested.

## Planned Technology Stack

* **Language:** Python 3.10+
* **User Interface:** Streamlit
* **Analysis Engine:** Deterministic rule-based static analysis (AST & Regex)
* **Advisory AI Layer:** Google Gemini API (contextual explanations and suggested fixes only)
* **Testing:** pytest (307 passing tests)

## Setup and Execution

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure Gemini (Optional):**
   Create a `.env` file in the project root and add your API key. (Do NOT commit this file to version control).
   ```text
   GEMINI_API_KEY=your_api_key_here
   ```
3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## Known Limitations

- **Gemini API Availability:** During manual verification, the Gemini API occasionally returned transient `503 UNAVAILABLE` responses due to high demand. The application handles this gracefully: AI Explanation and Suggested Fix are shown when Gemini enrichment succeeds; deterministic audit findings and scoring remain fully available when Gemini is unavailable.
