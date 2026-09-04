"""Tests for social signals + hireability scoring (deterministic, no network)."""

from app.services.social_signals import (
    _normalize_medium_handle,
    compute_hireability,
)


def _rich_github():
    return {
        "github_profile": {
            "profile": {
                "followers": 120,
                "public_repos": 24,
                "bio": "ML engineer",
                "avatar_url": "https://x/y.png",
            },
            "total_stars": 320,
            "languages": {"Python": 10, "TypeScript": 5, "Go": 3, "Rust": 1},
        },
        "github_analysis": {"skills": ["python", "react", "docker", "aws", "sql"], "experience_level": "senior"},
        "social_links": {"blog_url": "https://alice.dev", "linkedin_url": "https://linkedin.com/in/alice", "twitter_handle": "alice"},
        "github_oss": {"total_prs": 12},
        "github_contributions": {"longest_streak": 45},
        "github_commit_analysis": {"consistency_score": 80},
    }


def test_empty_signals_scores_zero_pass():
    report = compute_hireability()
    assert report["score"] == 0
    assert report["band"] == "pass"
    assert report["confidence"] == 0
    assert len(report["dimensions"]) == 5
    assert sum(d["max"] for d in report["dimensions"]) == 100


def test_rich_profile_scores_strong_hire():
    report = compute_hireability(
        github=_rich_github(),
        portfolio={"projects": [{}, {}, {}, {}], "technologies_detected": ["react", "node", "aws", "docker", "ts", "go"]},
        medium={"posts": [{"has_code": True}, {"has_code": False}], "tech_posts": 6},
        blog={"posts": []},
    )
    assert report["score"] >= 80
    assert report["band"] == "strong_hire"
    assert report["confidence"] >= 0.75
    assert any("320 total stars" in e for d in report["dimensions"] for e in d["evidence"])


def test_partial_signals_consider_band():
    report = compute_hireability(github=_rich_github())
    assert report["band"] in ("hire", "consider")
    assert report["confidence"] == 0.25


def test_resume_eval_feeds_production_dimension():
    report = compute_hireability(
        resume_eval={"scores": {"production": {"score": 20}}, "key_strengths": ["Shipped X"]}
    )
    prod = next(d for d in report["dimensions"] if d["name"] == "production_experience")
    assert prod["score"] == 12.0  # 20 * 0.6
    assert report["sources_loaded"] == 1


def test_medium_handle_normalization():
    assert _normalize_medium_handle("@alice") == "alice"
    assert _normalize_medium_handle("alice") == "alice"
    assert _normalize_medium_handle("https://medium.com/@alice/latest") == "alice"
    assert _normalize_medium_handle("") is None
    assert _normalize_medium_handle("not a handle!!") is None
