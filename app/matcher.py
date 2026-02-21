from __future__ import annotations

from dataclasses import dataclass

from app.types import NormalizedVacancy

POSITIVE_TERMS = {
    "machine learning engineer": 1.0,
    "ml engineer": 1.0,
    "data scientist": 1.0,
    "applied scientist": 1.0,
    "mlops engineer": 1.0,
    "mlops": 0.95,
    "ml ops engineer": 1.0,
    "ml ops": 0.95,
    "research engineer": 0.9,
    "ai engineer": 0.9,
    "ai scientist": 0.95,
    "machine learning scientist": 1.0,
    "deep learning engineer": 0.95,
    "computer vision engineer": 0.9,
    "nlp engineer": 0.9,
    "llm engineer": 0.9,
}

NEGATIVE_TERMS = {
    "intern": 0.35,
    "student": 0.35,
    "sales": 0.25,
    "account executive": 0.35,
}

GEO_TERMS = {
    "london",
    "united kingdom",
    "uk",
    "england",
    "germany",
    "deutschland",
    "berlin",
    "munich",
    "muenchen",
    "hamburg",
    "frankfurt",
    "netherlands",
    "nederland",
    "amsterdam",
    "rotterdam",
    "the hague",
    "utrecht",
    "eindhoven",
}

REMOTE_TERMS = {"remote", "work from home", "distributed"}
REMOTE_EU_TERMS = {"europe", "eu", "emea"}

TITLE_WEIGHT = 0.65
DESCRIPTION_WEIGHT = 0.35


@dataclass(frozen=True)
class MatchComputation:
    score: float
    matched_terms: list[str]
    geo_pass: bool
    decision: str


def compute_match(
    vacancy: NormalizedVacancy,
    min_score: float,
    enable_remote_eu: bool,
) -> MatchComputation:
    title = vacancy.title.lower()
    description = vacancy.description_text.lower()
    location = vacancy.location.lower()

    title_score, title_terms = _score_positive(title)
    description_score, desc_terms = _score_positive(description)

    penalty = _score_negative(title) + _score_negative(description)
    raw_score = TITLE_WEIGHT * title_score + DESCRIPTION_WEIGHT * description_score - penalty
    score = max(0.0, min(1.0, raw_score))
    matched_terms = sorted(set(title_terms + desc_terms))

    geo_pass = _geo_allowed(location, description, enable_remote_eu)
    if not geo_pass:
        return MatchComputation(score=score, matched_terms=matched_terms, geo_pass=False, decision="reject_geo")

    if score < min_score:
        return MatchComputation(score=score, matched_terms=matched_terms, geo_pass=True, decision="reject_score")

    return MatchComputation(score=score, matched_terms=matched_terms, geo_pass=True, decision="send")


def _score_positive(text: str) -> tuple[float, list[str]]:
    hits: list[str] = []
    max_weight = 0.0

    for term, weight in POSITIVE_TERMS.items():
        if term in text:
            hits.append(term)
            if weight > max_weight:
                max_weight = weight

    return max_weight, hits


def _score_negative(text: str) -> float:
    penalty = 0.0
    for term, weight in NEGATIVE_TERMS.items():
        if term in text:
            penalty += weight
    return penalty


def _geo_allowed(location: str, description: str, enable_remote_eu: bool) -> bool:
    haystack = f"{location} {description}"
    if any(term in haystack for term in GEO_TERMS):
        return True

    if enable_remote_eu and any(term in haystack for term in REMOTE_TERMS):
        if any(term in haystack for term in REMOTE_EU_TERMS):
            return True

    return False
