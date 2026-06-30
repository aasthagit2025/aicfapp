from __future__ import annotations

import pandas as pd
import streamlit as st

from aicf_framework import DIMENSIONS, REQUIRED_COLUMNS, score_insight, validate_columns


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
st.caption("Upload AI-generated market research insights. AICF will auto-estimate confidence and flag human review needs.")

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

uploaded_file = st.file_uploader("Upload insights CSV", type=["csv"])

if uploaded_file is None:
    st.info("Upload a CSV with only `insight_id` and `insight_text`. You may add `evidence_note` for better scoring.")
    st.dataframe(make_template(), use_container_width=True)
    st.stop()

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

with st.expander("How AICF auto-scoring works"):
    st.write(
        "This version uses transparent rule-based checks. It looks for evidence markers "
        "such as sample size, percentages, ratings, cautious language, action wording, "
        "overclaims, unsupported causal claims, and validation warnings. For academic "
        "validation, you can later compare these auto-scores with human evaluator scores."
    )

csv = report.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Scored Report",
    data=csv,
    file_name="aicf_scored_report.csv",
    mime="text/csv",
)
