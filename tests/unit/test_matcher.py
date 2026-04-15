from app.matcher import build_match_profile, compute_match
from app.types import NormalizedVacancy


def _vacancy(title: str, location: str, description: str) -> NormalizedVacancy:
    return NormalizedVacancy(
        canonical_id="abc",
        company="TestCo",
        title=title,
        location=location,
        url="https://example.com/jobs/1",
        posted_at=None,
        description_text=description,
        source_id="test",
        external_id="1",
    )


def test_matcher_accepts_ml_role_with_target_geo():
    vacancy = _vacancy(
        title="Machine Learning Engineer",
        location="London, UK",
        description="Build NLP and recommender systems",
    )
    result = compute_match(vacancy, min_score=0.62, enable_remote_eu=False)

    assert result.decision == "send"
    assert result.geo_pass is True
    assert result.score >= 0.62


def test_matcher_rejects_non_target_geo():
    vacancy = _vacancy(
        title="Data Scientist",
        location="San Francisco, United States",
        description="Strong ML and statistics",
    )
    result = compute_match(vacancy, min_score=0.62, enable_remote_eu=False)

    assert result.decision == "reject_geo"
    assert result.geo_pass is False


def test_matcher_penalizes_intern_roles():
    vacancy = _vacancy(
        title="Machine Learning Intern",
        location="Berlin, Germany",
        description="Internship program for students",
    )
    result = compute_match(vacancy, min_score=0.62, enable_remote_eu=False)

    assert result.decision != "send"


def test_matcher_accepts_applied_scientist_title_only():
    vacancy = _vacancy(
        title="Principal Applied Scientist - ZMS (all genders)",
        location="Berlin, Germany",
        description="Applied Science & Research",
    )
    result = compute_match(vacancy, min_score=0.60, enable_remote_eu=False)

    assert result.decision == "send"


def test_matcher_uses_additive_weighting_across_term_families():
    vacancy = _vacancy(
        title="Research Engineer",
        location="Berlin, Germany",
        description="Own NLP engineer workflows for the LLM platform",
    )
    result = compute_match(vacancy, min_score=0.62, enable_remote_eu=False)

    assert result.decision == "send"
    assert "research engineer" in result.matched_terms
    assert "nlp engineer" in result.matched_terms
    assert result.score > 0.62


def test_matcher_accepts_remote_eu_when_enabled():
    vacancy = _vacancy(
        title="Machine Learning Engineer",
        location="Remote",
        description="Remote within Europe or EMEA",
    )
    result = compute_match(vacancy, min_score=0.60, enable_remote_eu=True)

    assert result.decision == "send"


def test_matcher_applies_source_profile_overrides():
    vacancy = _vacancy(
        title="Recommendation Engineer",
        location="Madrid, Spain",
        description="Remote across Iberia",
    )
    profile = build_match_profile()
    result = compute_match(
        vacancy,
        min_score=0.55,
        enable_remote_eu=False,
        match_profile=profile,
        source_profile={
            "positive_terms": {
                "recommendation_engineer": {
                    "weight": 0.9,
                    "terms": ["recommendation engineer"],
                }
            },
            "geo_terms": ["madrid", "spain"],
        },
    )

    assert result.decision == "send"
    assert "recommendation engineer" in result.matched_terms
