from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.types import NormalizedVacancy

DEFAULT_POSITIVE_RULES = {
    "machine_learning_engineer": {
        "weight": 1.0,
        "terms": ["machine learning engineer", "ml engineer"],
    },
    "data_scientist": {
        "weight": 1.0,
        "terms": ["data scientist"],
    },
    "applied_scientist": {
        "weight": 1.0,
        "terms": ["applied scientist", "applied science"],
    },
    "mlops_engineer": {
        "weight": 1.0,
        "terms": ["mlops engineer", "ml ops engineer", "mlops", "ml ops"],
    },
    "research_engineer": {
        "weight": 0.9,
        "terms": ["research engineer"],
    },
    "ai_engineer": {
        "weight": 0.9,
        "terms": ["ai engineer"],
    },
    "ai_scientist": {
        "weight": 0.95,
        "terms": ["ai scientist"],
    },
    "machine_learning_scientist": {
        "weight": 1.0,
        "terms": ["machine learning scientist"],
    },
    "deep_learning_engineer": {
        "weight": 0.95,
        "terms": ["deep learning engineer"],
    },
    "computer_vision_engineer": {
        "weight": 0.9,
        "terms": ["computer vision engineer"],
    },
    "nlp_engineer": {
        "weight": 0.9,
        "terms": ["nlp engineer", "natural language processing engineer"],
    },
    "llm_engineer": {
        "weight": 0.9,
        "terms": ["llm engineer", "large language model engineer"],
    },
}

DEFAULT_NEGATIVE_RULES = {
    "intern": {"weight": 0.35, "terms": ["intern", "internship"]},
    "student": {"weight": 0.35, "terms": ["student"]},
    "sales": {"weight": 0.25, "terms": ["sales"]},
    "account_executive": {"weight": 0.35, "terms": ["account executive"]},
}

DEFAULT_GEO_TERMS = {
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

DEFAULT_REMOTE_TERMS = {"remote", "work from home", "distributed"}
DEFAULT_REMOTE_REGION_TERMS = {"europe", "eu", "emea"}

TITLE_WEIGHT = 0.65
DESCRIPTION_WEIGHT = 0.35


@dataclass(frozen=True)
class MatchComputation:
    score: float
    matched_terms: list[str]
    geo_pass: bool
    decision: str


@dataclass(frozen=True)
class KeywordRule:
    family: str
    weight: float
    terms: tuple[str, ...]


@dataclass(frozen=True)
class MatchProfile:
    positive_rules: tuple[KeywordRule, ...]
    negative_rules: tuple[KeywordRule, ...]
    geo_terms: frozenset[str]
    remote_terms: frozenset[str]
    remote_region_terms: frozenset[str]


def compute_match(
    vacancy: NormalizedVacancy,
    min_score: float,
    enable_remote_eu: bool,
    match_profile: MatchProfile | None = None,
    source_profile: dict[str, Any] | None = None,
) -> MatchComputation:
    profile = merge_match_profile(match_profile or DEFAULT_MATCH_PROFILE, source_profile)
    title = vacancy.title.lower()
    description = vacancy.description_text.lower()
    location = vacancy.location.lower()

    title_score, title_terms = _score_positive(title, profile.positive_rules)
    description_score, desc_terms = _score_positive(description, profile.positive_rules)

    penalty = _score_negative(title, profile.negative_rules) + _score_negative(description, profile.negative_rules)
    raw_score = TITLE_WEIGHT * title_score + DESCRIPTION_WEIGHT * description_score - penalty
    score = max(0.0, min(1.0, raw_score))
    matched_terms = sorted(set(title_terms + desc_terms))

    geo_pass = _geo_allowed(location, description, enable_remote_eu, profile)
    if not geo_pass:
        return MatchComputation(score=score, matched_terms=matched_terms, geo_pass=False, decision="reject_geo")

    if score < min_score:
        return MatchComputation(score=score, matched_terms=matched_terms, geo_pass=True, decision="reject_score")

    return MatchComputation(score=score, matched_terms=matched_terms, geo_pass=True, decision="send")


def build_match_profile(
    positive_terms: dict[str, Any] | None = None,
    negative_terms: dict[str, Any] | None = None,
    geo_terms: set[str] | list[str] | tuple[str, ...] | None = None,
    remote_terms: set[str] | list[str] | tuple[str, ...] | None = None,
    remote_region_terms: set[str] | list[str] | tuple[str, ...] | None = None,
) -> MatchProfile:
    return MatchProfile(
        positive_rules=tuple(_build_rules(positive_terms or DEFAULT_POSITIVE_RULES)),
        negative_rules=tuple(_build_rules(negative_terms or DEFAULT_NEGATIVE_RULES)),
        geo_terms=frozenset(_normalize_term_set(geo_terms or DEFAULT_GEO_TERMS)),
        remote_terms=frozenset(_normalize_term_set(remote_terms or DEFAULT_REMOTE_TERMS)),
        remote_region_terms=frozenset(_normalize_term_set(remote_region_terms or DEFAULT_REMOTE_REGION_TERMS)),
    )


def merge_match_profile(base: MatchProfile, overrides: dict[str, Any] | None) -> MatchProfile:
    if not overrides:
        return base

    positive_raw = _merge_rule_config(base.positive_rules, overrides.get("positive_terms"))
    negative_raw = _merge_rule_config(base.negative_rules, overrides.get("negative_terms"))
    geo_terms = _merge_term_sets(base.geo_terms, overrides.get("geo_terms"))
    remote_terms = _merge_term_sets(base.remote_terms, overrides.get("remote_terms"))
    remote_region_terms = _merge_term_sets(base.remote_region_terms, overrides.get("remote_region_terms"))

    return MatchProfile(
        positive_rules=tuple(_build_rules(positive_raw)),
        negative_rules=tuple(_build_rules(negative_raw)),
        geo_terms=frozenset(geo_terms),
        remote_terms=frozenset(remote_terms),
        remote_region_terms=frozenset(remote_region_terms),
    )


def _score_positive(text: str, rules: tuple[KeywordRule, ...]) -> tuple[float, list[str]]:
    hits: list[str] = []
    total = 0.0

    for rule in rules:
        matched = next((term for term in rule.terms if term in text), None)
        if not matched:
            continue
        total += rule.weight
        hits.append(matched)

    return min(1.0, total), hits


def _score_negative(text: str, rules: tuple[KeywordRule, ...]) -> float:
    penalty = 0.0
    for rule in rules:
        if any(term in text for term in rule.terms):
            penalty += rule.weight
    return penalty


def _geo_allowed(location: str, description: str, enable_remote_eu: bool, profile: MatchProfile) -> bool:
    haystack = f"{location} {description}"
    if any(term in haystack for term in profile.geo_terms):
        return True

    if enable_remote_eu and any(term in haystack for term in profile.remote_terms):
        if any(term in haystack for term in profile.remote_region_terms):
            return True

    return False


def _build_rules(config: dict[str, Any]) -> list[KeywordRule]:
    rules: list[KeywordRule] = []
    for family, raw in config.items():
        normalized_family = str(family).strip().lower()
        if not normalized_family:
            continue

        if isinstance(raw, (int, float)):
            terms = [normalized_family.replace("_", " ")]
            weight = float(raw)
        elif isinstance(raw, dict):
            weight = float(raw.get("weight", 0.0))
            terms = [str(term).strip().lower() for term in raw.get("terms", []) if str(term).strip()]
        else:
            continue

        if not terms or weight <= 0:
            continue
        rules.append(KeywordRule(family=normalized_family, weight=weight, terms=tuple(dict.fromkeys(terms))))

    return rules


def _normalize_term_set(values: set[str] | list[str] | tuple[str, ...]) -> set[str]:
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _merge_rule_config(base_rules: tuple[KeywordRule, ...], override: Any) -> dict[str, Any]:
    merged = {
        rule.family: {
            "weight": rule.weight,
            "terms": list(rule.terms),
        }
        for rule in base_rules
    }
    if isinstance(override, dict):
        for family, raw in override.items():
            normalized_family = str(family).strip().lower()
            if not normalized_family:
                continue
            if isinstance(raw, (int, float)):
                merged[normalized_family] = {
                    "weight": float(raw),
                    "terms": [normalized_family.replace("_", " ")],
                }
                continue
            if not isinstance(raw, dict):
                continue

            existing = merged.get(normalized_family, {"weight": 0.0, "terms": []})
            terms = raw.get("terms", existing["terms"])
            merged[normalized_family] = {
                "weight": float(raw.get("weight", existing["weight"])),
                "terms": list(dict.fromkeys(str(term).strip().lower() for term in terms if str(term).strip())),
            }
    return merged


def _merge_term_sets(base: frozenset[str], override: Any) -> set[str]:
    merged = set(base)
    if isinstance(override, (list, tuple, set, frozenset)):
        merged.update(_normalize_term_set(override))
    return merged


DEFAULT_MATCH_PROFILE = MatchProfile(
    positive_rules=tuple(_build_rules(DEFAULT_POSITIVE_RULES)),
    negative_rules=tuple(_build_rules(DEFAULT_NEGATIVE_RULES)),
    geo_terms=frozenset(DEFAULT_GEO_TERMS),
    remote_terms=frozenset(DEFAULT_REMOTE_TERMS),
    remote_region_terms=frozenset(DEFAULT_REMOTE_REGION_TERMS),
)
