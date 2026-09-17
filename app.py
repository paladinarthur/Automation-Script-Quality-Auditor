"""
Automation Script Quality Auditor — Streamlit Application Entry Point

Provides a lightweight, single-page UI workflow:
Select Framework → Select Language → Provide Script → Analyze → Review Results

Deliberate Architecture Constraints:
- Streamlit UI is presentation ONLY.
- Uses existing domain services: audit_service, scoring_service, report_service, gemini_service, validator.
- Supports pasting source text or uploading single .py, .js, .ts source file.
- Script content is treated strictly as untrusted text and never executed.
"""

import streamlit as st

from src.models.enums import Framework, Language, Severity
from src.models.input import ScriptInput
from src.services.audit_service import audit_script
from src.services.gemini_service import GeminiService, enrich_findings
from src.services.report_service import generate_report
from src.services.scoring_service import calculate_score
from src.validation.validator import get_supported_languages, validate_framework_and_language

ALLOWED_EXTENSIONS = {".py", ".js", ".ts"}

# Framework display labels mapping to Framework enum
FRAMEWORK_MAP = {
    "Selenium": Framework.SELENIUM,
    "Playwright": Framework.PLAYWRIGHT,
    "Cypress": Framework.CYPRESS,
}

# Language display labels mapping to Language enum
LANGUAGE_DISPLAY_NAMES = {
    Language.PYTHON: "Python",
    Language.JAVASCRIPT: "JavaScript",
    Language.TYPESCRIPT: "TypeScript",
}

LANGUAGE_MAP = {
    "Python": Language.PYTHON,
    "JavaScript": Language.JAVASCRIPT,
    "TypeScript": Language.TYPESCRIPT,
}


def is_supported_file_extension(filename: str) -> bool:
    """Checks whether the filename has a supported extension (.py, .js, .ts)."""
    if not filename or "." not in filename:
        return False
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def _format_language(lang: Language) -> str:
    return LANGUAGE_DISPLAY_NAMES.get(lang, lang.value.capitalize())


def main() -> None:
    # 1. Page Configuration
    st.set_page_config(
        page_title="Automation Script Quality Auditor",
        page_icon="🔍",
        layout="wide",
    )

    # Header Section
    st.title("Automation Script Quality Auditor")
    st.caption(
        "Static code quality analysis for Selenium, Playwright, and Cypress test scripts."
    )
    st.divider()

    # 2. Framework & Language Selection
    col_fw, col_lang = st.columns(2)

    with col_fw:
        selected_fw_label = st.selectbox(
            "Select Framework",
            options=list(FRAMEWORK_MAP.keys()),
            index=0,
            help="Choose the target test automation framework.",
        )
        selected_fw_enum = FRAMEWORK_MAP[selected_fw_label]

    with col_lang:
        # Dynamically present only valid languages for the chosen framework
        valid_languages = get_supported_languages(selected_fw_enum)
        lang_options = [_format_language(lang) for lang in valid_languages]

        selected_lang_label = st.selectbox(
            "Select Language",
            options=lang_options,
            index=0,
            help="Choose the programming language binding for the selected framework.",
        )
        selected_lang_enum = LANGUAGE_MAP[selected_lang_label]

    st.write("")

    # 3. Script Input Section
    st.subheader("Automation Script Input")

    tab_paste, tab_upload = st.tabs(["Method A: Paste Script", "Method B: Upload Script File"])

    pasted_code = ""
    uploaded_code = ""
    uploaded_file_valid = True

    with tab_paste:
        pasted_code = st.text_area(
            "Paste Source Code",
            height=260,
            placeholder="Paste your automation script here...",
            help="Direct text entry for your test script source code.",
            label_visibility="collapsed",
        )

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Upload Source File",
            type=["py", "js", "ts"],
            accept_multiple_files=False,
            help="Select an individual .py, .js, or .ts automation script file.",
        )
        if uploaded_file is not None:
            if not is_supported_file_extension(uploaded_file.name):
                uploaded_file_valid = False
                st.error("Unsupported file type. Please upload a .py, .js, or .ts file.")
            else:
                try:
                    uploaded_bytes = uploaded_file.getvalue()
                    uploaded_code = uploaded_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    uploaded_file_valid = False
                    st.error("Uploaded file could not be decoded as UTF-8 text.")

    # Input Convergence: Upload takes precedence if provided and valid, otherwise pasted text
    active_script = ""
    active_source = "none"

    if uploaded_file is not None and uploaded_file_valid:
        if uploaded_code.strip():
            active_script = uploaded_code
            active_source = f"Uploaded File ({uploaded_file.name})"
            st.info(f"📁 Active Input: **{active_source}**")
    elif pasted_code and pasted_code.strip():
        active_script = pasted_code
        active_source = "Pasted Script Text"
        st.info(f"📝 Active Input: **{active_source}**")

    # Static Analysis Transparency Notice
    st.info("ℹ️ Static analysis only — script content is evaluated without execution.")

    # 4. Analyze Trigger Button
    st.write("")
    analyze_clicked = st.button("🔍 Analyze Script", type="primary", use_container_width=True)

    if analyze_clicked:
        # Validation checks
        if uploaded_file is not None and not uploaded_file_valid:
            st.error("Unsupported file type. Please upload a .py, .js, or .ts file.")
            return

        if uploaded_file is not None and len(uploaded_file.getvalue()) == 0:
            st.warning("Uploaded file is empty.")
            return

        if not active_script or not active_script.strip():
            st.warning("Please paste an automation script or upload a source file to analyze.")
            return

        validation = validate_framework_and_language(selected_fw_enum, selected_lang_enum)
        if not validation.is_valid:
            st.error(validation.error_message or "Invalid framework and language combination.")
            return

        # Execute Audit Pipeline
        with st.spinner("Performing static analysis and generating audit report..."):
            script_input = ScriptInput(
                script_content=active_script,
                framework=selected_fw_enum,
                language=selected_lang_enum,
            )

            # 1. Deterministic static audit
            raw_findings = audit_script(script_input)

            # 2. Deterministic scoring
            scorecard = calculate_score(raw_findings)

            # 3. Gemini advisory enrichment (graceful fallback if unavailable)
            gemini_svc = GeminiService()
            gemini_available = gemini_svc.is_available()

            if gemini_available:
                final_findings = enrich_findings(
                    raw_findings,
                    selected_fw_enum.value,
                    selected_lang_enum.value,
                    gemini_svc,
                )
            else:
                final_findings = raw_findings

            # 4. Report assembly
            report = generate_report(final_findings, scorecard)

        st.divider()

        # 5. Render Results Hierarchy
        st.header("Audit Results")

        # Non-blocking Gemini warning if unavailable
        if not gemini_available:
            st.warning(
                "Gemini advisory enrichment is currently unavailable. "
                "Deterministic score and findings are fully intact."
            )

        # Executive Summary Banner Cards
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)

        with metric_col1:
            st.metric("Overall Score", f"{scorecard.overall_score} / 100")

        with metric_col2:
            st.metric("Rating", scorecard.rating.value)

        with metric_col3:
            st.metric("Total Issues", scorecard.total_issues)

        with metric_col4:
            st.metric("High Severity", scorecard.high_severity_count)

        with metric_col5:
            st.metric("Medium Severity", scorecard.medium_severity_count)

        st.caption(
            f"**Categories Detected:** {scorecard.anti_patterns_detected} / 10 anti-pattern categories"
        )
        st.write("")

        # Scorecard Breakdown Section
        st.subheader("📊 Scorecard & Deductions")
        if scorecard.category_breakdown:
            table_data = []
            for ap_id, deduction in scorecard.category_breakdown.items():
                table_data.append(
                    {
                        "Category ID": ap_id,
                        "Deduction Points": f"-{deduction}",
                    }
                )
            st.table(table_data)
        else:
            st.success("No penalty deductions applied. Perfect score!")

        st.write("")

        # Confirmed Findings Section
        st.subheader(f"🚨 Confirmed Anti-Pattern Findings ({scorecard.total_issues})")

        if scorecard.total_issues == 0:
            st.success("🎉 No checklist anti-patterns detected. Great job!")
        else:
            for finding in report.findings:
                sev_badge = "🔴 HIGH" if finding.severity == Severity.HIGH else "🟡 MEDIUM"
                expander_title = (
                    f"{sev_badge} · {finding.anti_pattern_id} — {finding.anti_pattern_name} "
                    f"({finding.line_display})"
                )

                with st.expander(expander_title, expanded=True):
                    st.markdown(f"**Line Reference:** `{finding.line_display}`")
                    st.markdown(f"**Severity:** {finding.severity.value} | **Confidence:** {finding.confidence.value}")

                    st.markdown("**Offending Code Snippet:**")
                    st.code(
                        finding.code_snippet,
                        language=selected_lang_enum.value,
                    )

                    st.markdown(f"**Detection Reason:** {finding.reason}")

                    if finding.explanation:
                        st.markdown(f"**AI Explanation (Advisory):** {finding.explanation}")

                    if finding.suggested_fix:
                        st.markdown("**AI Suggested Fix (Advisory):**")
                        st.code(
                            finding.suggested_fix,
                            language=selected_lang_enum.value,
                        )

        st.write("")

        # Actionable Recommendations Section
        st.subheader("💡 Actionable Recommendations")
        recs = report.recommendations
        high_recs = recs.get("high_priority", [])
        med_recs = recs.get("medium_priority", [])
        notes = recs.get("note", [])

        if high_recs:
            st.markdown("**High Priority:**")
            for rec in high_recs:
                st.markdown(f"- {rec}")

        if med_recs:
            st.markdown("**Medium Priority:**")
            for rec in med_recs:
                st.markdown(f"- {rec}")

        if not high_recs and not med_recs and notes:
            for note in notes:
                st.info(note)

        st.write("")

        # Methodology Footer
        st.subheader("ℹ️ Methodology & Audit Boundaries")
        for method_item in report.methodology:
            st.markdown(f"- {method_item}")


if __name__ == "__main__":
    main()
