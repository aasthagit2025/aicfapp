from __future__ import annotations

import re
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


REQUIRED_COLUMNS = ["insight_id", "insight_text"]
MANUAL_SCORE_COLUMNS = list(DIMENSIONS.keys())


@dataclass
class AICFResult:
    insight_id: str
    insight_text: str
    evidence_strength: int
    methodological_fit: int
    triangulation: int
    interpretability: int
    business_relevance: int
    actionability: int
    bias_risk: int
    weighted_score: float
    confidence_level: str
    weakest_dimensions: str
    recommendation: str
    scoring_mode: str


def parse_score(value: object, column: str) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{column} must be an integer from 1 to 5.") from exc

    if score < 1 or score > 5:
        raise ValueError(f"{column} score {score} is outside the valid range of 1 to 5.")
    return score


def confidence_level(score: float) -> str:
    if score >= 4.00:
        return "High Confidence"
    if score >= 3.50:
        return "Moderate Confidence"
    if score >= 2.50:
        return "Low-Moderate Confidence"
    return "Low Confidence"


def clamp_score(score: int) -> int:
    return max(1, min(5, score))


def has_numeric_evidence(text: str) -> bool:
    return bool(re.search(r"\b\d+(\.\d+)?\s*(%|/5|/10|respondents?|n=|mean|score|rating|top)", text, re.I))


def contains_any(text: str, words: List[str]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in words)


def auto_dimension_scores(row: Dict[str, object]) -> Dict[str, int]:
    insight = str(row.get("insight_text", "") or "")
    evidence = str(row.get("evidence_note", "") or "")
    combined = f"{insight} {evidence}".strip()
    word_count = len(re.findall(r"\w+", insight))

    high_signal = contains_any(combined, ["relative strength", "strong customer advocacy", "high confidence"])
    review_signal = contains_any(combined, ["needs human attention", "requires validation", "unsupported", "not coded", "does not establish", "weak base", "overstates"])
    risky_claim = contains_any(combined, ["fully satisfied", "all customers", "no improvement", "main reason", "primary cause", "only serious", "exclusive benchmark", "reduce investment"])

    base = 4 if high_signal and not review_signal and not risky_claim else 3
    scores = {key: base for key in DIMENSIONS}

    if has_numeric_evidence(combined):
        scores["evidence_strength"] += 1
    if contains_any(combined, ["n=", "sample", "respondents", "survey", "mean", "top-two", "rating", "score"]):
        scores["evidence_strength"] += 1
    if contains_any(combined, ["requires validation", "needs validation", "unsupported", "not establish", "not yet", "hypothesis"]):
        scores["evidence_strength"] -= 2

    if contains_any(combined, ["customer", "satisfaction", "market", "survey", "respondent", "brand", "product", "service", "business"]):
        scores["methodological_fit"] += 1
    if contains_any(combined, ["caused by", "main reason", "fully satisfied", "only serious", "exclusive benchmark", "no improvement"]):
        scores["methodological_fit"] -= 2

    if contains_any(combined, ["compared", "across", "followed by", "alongside", "linked", "triangulat", "open-ended"]):
        scores["triangulation"] += 1
    if contains_any(combined, ["requires validation", "not coded", "does not establish", "weak base", "unsupported"]):
        scores["triangulation"] -= 2
    if contains_any(combined, ["primary cause", "main reason", "only serious", "all customers"]):
        scores["triangulation"] -= 2

    if 12 <= word_count <= 55:
        scores["interpretability"] += 1
    if contains_any(combined, ["unclear", "vague", "maybe", "somehow"]):
        scores["interpretability"] -= 1

    if contains_any(combined, ["customer", "client", "business", "revenue", "cost", "roi", "satisfaction", "preference", "recommend", "retention"]):
        scores["business_relevance"] += 1

    if contains_any(combined, ["should", "priority", "improve", "focus", "recommend", "action", "opportunity", "strengthen", "investigate"]):
        scores["actionability"] += 1
    if contains_any(combined, ["no improvement", "exclusive benchmark", "reduce investment"]):
        scores["actionability"] -= 2

    if contains_any(combined, ["requires validation", "unsupported", "causal", "fully satisfied", "all customers", "only serious", "primary cause", "reduce investment"]):
        scores["bias_risk"] -= 2
    if contains_any(combined, ["moderate", "suggest", "may", "should be interpreted", "requires validation", "hypothesis"]):
        scores["bias_risk"] += 1

    if risky_claim:
        scores["evidence_strength"] -= 1
        scores["triangulation"] -= 1
        scores["bias_risk"] -= 1

    if review_signal:
        scores["evidence_strength"] -= 1
        scores["triangulation"] -= 1

    if high_signal and not review_signal and not risky_claim:
        scores["business_relevance"] += 1
        scores["interpretability"] += 1

    return {key: clamp_score(value) for key, value in scores.items()}


def score_insight(row: Dict[str, object]) -> AICFResult:
    has_manual_scores = all(row.get(key) not in (None, "") for key in MANUAL_SCORE_COLUMNS)
    if has_manual_scores:
        dimension_scores = {
            key: parse_score(row.get(key), key)
            for key in DIMENSIONS
        }
        scoring_mode = "Manual evaluator scores"
    else:
        dimension_scores = auto_dimension_scores(row)
        scoring_mode = "AICF auto-estimated scores"

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
        evidence_strength=dimension_scores["evidence_strength"],
        methodological_fit=dimension_scores["methodological_fit"],
        triangulation=dimension_scores["triangulation"],
        interpretability=dimension_scores["interpretability"],
        business_relevance=dimension_scores["business_relevance"],
        actionability=dimension_scores["actionability"],
        bias_risk=dimension_scores["bias_risk"],
        weighted_score=round(weighted_score, 2),
        confidence_level=confidence_level(weighted_score),
        weakest_dimensions="; ".join(weakest_labels),
        recommendation=" ".join(recommended_actions),
        scoring_mode=scoring_mode,
    )


def validate_columns(columns: List[str]) -> List[str]:
    return [column for column in REQUIRED_COLUMNS if column not in columns]
