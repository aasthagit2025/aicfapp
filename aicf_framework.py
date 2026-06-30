from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


DIMENSIONS = {
    "evidence_strength": {
        "label": "Evidence Strength",
        "weight": 0.20,
        "low_score_action": "Add stronger source support, sample detail, or verbatim evidence.",
    },
    "methodological_fit": {
        "label": "Methodological Fit",
        "weight": 0.15,
        "low_score_action": "Check whether the insight fits the research objective and method.",
    },
    "triangulation": {
        "label": "Triangulation / Consistency",
        "weight": 0.15,
        "low_score_action": "Compare against another data source, analyst read, or model run.",
    },
    "interpretability": {
        "label": "Interpretability",
        "weight": 0.10,
        "low_score_action": "Make the reasoning path clearer and reduce vague claims.",
    },
    "business_relevance": {
        "label": "Business Relevance",
        "weight": 0.15,
        "low_score_action": "Connect the insight more directly to a decision or market problem.",
    },
    "actionability": {
        "label": "Actionability",
        "weight": 0.15,
        "low_score_action": "Translate the insight into a practical recommendation or next step.",
    },
    "bias_risk": {
        "label": "Bias / Risk Control",
        "weight": 0.10,
        "low_score_action": "Review for hallucination, sampling bias, stereotype, or unsupported causality.",
    },
}


REQUIRED_COLUMNS = ["insight_id", "insight_text", *DIMENSIONS.keys()]


@dataclass
class AICFResult:
    insight_id: str
    insight_text: str
    weighted_score: float
    confidence_level: str
    weakest_dimensions: str
    recommendation: str


def parse_score(value: object, column: str) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{column} must be an integer from 1 to 5.") from exc

    if score < 1 or score > 5:
        raise ValueError(f"{column} score {score} is outside the valid range of 1 to 5.")
    return score


def confidence_level(score: float) -> str:
    if score >= 4.20:
        return "High Confidence"
    if score >= 3.40:
        return "Moderate Confidence"
    if score >= 2.60:
        return "Low-Moderate Confidence"
    return "Low Confidence"


def score_insight(row: Dict[str, object]) -> AICFResult:
    dimension_scores = {
        key: parse_score(row.get(key), key)
        for key in DIMENSIONS
    }

    weighted_score = sum(
        dimension_scores[key] * DIMENSIONS[key]["weight"]
        for key in DIMENSIONS
    )

    weakest = sorted(dimension_scores.items(), key=lambda item: item[1])[:2]
    weakest_labels = [
        f"{DIMENSIONS[key]['label']} ({score}/5)"
        for key, score in weakest
    ]
    recommended_actions = [
        DIMENSIONS[key]["low_score_action"]
        for key, score in weakest
        if score <= 3
    ]

    if not recommended_actions:
        recommended_actions = ["Proceed, while documenting evidence and analyst review notes."]

    return AICFResult(
        insight_id=str(row.get("insight_id", "")).strip(),
        insight_text=str(row.get("insight_text", "")).strip(),
        weighted_score=round(weighted_score, 2),
        confidence_level=confidence_level(weighted_score),
        weakest_dimensions="; ".join(weakest_labels),
        recommendation=" ".join(recommended_actions),
    )


def validate_columns(columns: List[str]) -> List[str]:
    return [column for column in REQUIRED_COLUMNS if column not in columns]
