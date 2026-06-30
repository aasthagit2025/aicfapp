# AI Insight Confidence Framework (AICF) Tool

This is a simple Streamlit app for scoring AI-generated market research insights using the AI Insight Confidence Framework.

## What The Tool Does

The tool takes a CSV file of AI-generated insights and scores each insight across seven AICF dimensions:

- Evidence Strength
- Methodological Fit
- Triangulation / Consistency
- Interpretability
- Business Relevance
- Actionability
- Bias / Risk Control

It returns:

- Weighted confidence score
- Confidence level
- Weakest dimensions
- Recommended human review actions

## Required CSV Columns

```text
insight_id, insight_text, evidence_strength, methodological_fit, triangulation, interpretability, business_relevance, actionability, bias_risk
```

Scores should be from `1` to `5`.

For `bias_risk`, use:

- `1` = high risk
- `5` = low risk / well controlled

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy On Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload `app.py`, `aicf_framework.py`, `requirements.txt`, and `README.md`.
3. Go to Streamlit Community Cloud.
4. Select the GitHub repository.
5. Set the main file path as `app.py`.
6. Deploy.

## Suggested Pilot Use

Use this app to evaluate 20 to 30 AI-generated market research insights. Ask 3 to 5 evaluators to score each insight independently, then compare confidence scores and review where human judgment is required.
