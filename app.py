from __future__ import annotations

import pandas as pd
import streamlit as st

from aicf_framework import DIMENSIONS, REQUIRED_COLUMNS, score_insight, validate_columns
from insight_generator import extract_questionnaire_text, generate_insights, read_survey_file


st.set_page_config(
    page_title="AICF Tool",
    page_icon="",
    layout="wide",
)


def make_template() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "insight_id": "I001",
                "insight_text": "Customers show moderate-positive satisfaction, but low-rating shares indicate improvement is still required.",
                "evidence_note": "Survey result: mean rating 3.59/5, top-two-box 59.7%, low ratings 18.4%, n=347.",
            },
            {
                "insight_id": "I002",
                "insight_text": "All customers are fully satisfied, so no improvement is required.",
                "evidence_note": "Requires validation because the claim overstates the survey evidence.",
            }
        ]
    )


def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    results = [score_insight(row.to_dict()).__dict__ for _, row in df.iterrows()]
    return pd.DataFrame(results)


st.title("AI Insight Confidence Framework")
st.caption("Generate insights from survey data or upload existing insights, then let AICF score confidence and flag human review needs.")

with st.sidebar:
    st.header("AICF Dimensions")
    for key, item in DIMENSIONS.items():
        st.write(f"**{item['label']}**")
        st.caption(f"Weight: {item['weight']:.0%}")

    template_csv = make_template().to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV Template",
        data=template_csv,
        file_name="aicf_input_template.csv",
        mime="text/csv",
    )

mode = st.tabs(["Generate From Survey", "Score Existing Insights"])

with mode[0]:
    st.subheader("Generate AI-Style Insights From Survey Data")
    survey_file = st.file_uploader("Upload survey data", type=["csv", "xlsx", "xls", "sav"])
    questionnaire_file = st.file_uploader("Optional: upload questionnaire", type=["docx", "txt"])
    max_insights = st.slider("Maximum insights to generate", min_value=5, max_value=50, value=25)

    if survey_file is None:
        st.info("Upload survey data to generate insights and evidence notes automatically.")
    else:
        try:
            survey_df, labels = read_survey_file(survey_file)
            questionnaire_text = extract_questionnaire_text(questionnaire_file)
            generated_df = generate_insights(survey_df, labels, questionnaire_text, max_insights=max_insights)
        except Exception as exc:
            st.error(f"Could not generate insights: {exc}")
            st.stop()

        if generated_df.empty:
            st.warning("No insights could be generated. Check whether the data contains rating, NPS, binary, or open-ended columns.")
            st.stop()

        st.write(f"Generated {len(generated_df)} insights from {len(survey_df)} survey rows.")
        st.dataframe(generated_df, use_container_width=True)

        generated_report = score_dataframe(generated_df)
        st.subheader("AICF Confidence Summary")
        generated_summary = generated_report["confidence_level"].value_counts().rename_axis("confidence_level").reset_index(name="count")

        col1, col2, col3, col4 = st.columns(4)
        levels = ["High Confidence", "Moderate Confidence", "Low-Moderate Confidence", "Low Confidence"]
        for col, level in zip([col1, col2, col3, col4], levels):
            count = int(generated_summary.loc[generated_summary["confidence_level"] == level, "count"].sum())
            col.metric(level, count)

        st.bar_chart(generated_summary.set_index("confidence_level"))
        st.subheader("Scored Generated Insights")
        st.dataframe(generated_report, use_container_width=True)

        st.download_button(
            "Download Generated Insights",
            data=generated_df.to_csv(index=False).encode("utf-8"),
            file_name="aicf_generated_insights.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download AICF Scored Report",
            data=generated_report.to_csv(index=False).encode("utf-8"),
            file_name="aicf_scored_generated_report.csv",
            mime="text/csv",
        )

with mode[1]:
    uploaded_file = st.file_uploader("Upload insights CSV", type=["csv"])

    if uploaded_file is None:
        st.info("Upload a CSV with only `insight_id` and `insight_text`. You may add `evidence_note` for better scoring.")
        st.dataframe(make_template(), use_container_width=True)
    else:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as exc:
            st.error(f"Could not read the CSV file: {exc}")
            st.stop()

        missing_columns = validate_columns(list(df.columns))
        if missing_columns:
            st.error("Your CSV is missing required columns.")
            st.write(missing_columns)
            st.write("Minimum required columns:")
            st.code(", ".join(REQUIRED_COLUMNS))
            st.stop()

        try:
            report = score_dataframe(df)
        except Exception as exc:
            st.error(f"Could not score the insights: {exc}")
            st.stop()

        st.subheader("Confidence Summary")
        summary = report["confidence_level"].value_counts().rename_axis("confidence_level").reset_index(name="count")

        col1, col2, col3, col4 = st.columns(4)
        levels = ["High Confidence", "Moderate Confidence", "Low-Moderate Confidence", "Low Confidence"]
        for col, level in zip([col1, col2, col3, col4], levels):
            count = int(summary.loc[summary["confidence_level"] == level, "count"].sum())
            col.metric(level, count)

        st.bar_chart(summary.set_index("confidence_level"))

        st.subheader("Scored Insights")
        st.dataframe(report, use_container_width=True)

        csv = report.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Scored Report",
            data=csv,
            file_name="aicf_scored_report.csv",
            mime="text/csv",
        )

with st.expander("How the full AICF workflow works"):
    st.write(
        "The survey module scans numeric rating columns, NPS-like columns, binary selection columns, "
        "and open-ended text columns. It creates an insight plus an evidence note, then passes both "
        "to the AICF scoring engine. This is a prototype for pilot and synopsis use; before client "
        "delivery, generated insights should still be reviewed by a researcher."
    )
