"""
Service-level tests for HiringAgentService.

These tests directly test the HiringAgentService methods rather than
the HTTP endpoints, since the current API endpoints all require PDF
file uploads which are difficult to mock in HTTP tests.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.hiring_agent.schemas import (
    ATSScore,
    BonusPoints,
    CategoryScore,
    Deductions,
    EvaluationData,
    ExtractedResume,
    ImprovementItem,
    ResumeBasics,
    ResumeSkill,
    ResumeWork,
    Scores,
)
from app.hiring_agent.service import HiringAgentService
from tests.conftest import TEST_USER_ID

SAMPLE_RESUME_TEXT = (
    "John Doe\nSoftware Engineer\n"
    "Python, JavaScript, React, Node.js\n"
    "Developed APIs, built microservices, deployed on AWS\n"
    "Led team of 5 engineers, managed agile sprints\n"
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    return HiringAgentService(mock_db, TEST_USER_ID)


@pytest.fixture
def sample_resume():
    return ExtractedResume(
        basics=ResumeBasics(name="John Doe", email="john@example.com"),
        skills=[ResumeSkill(name="Python", keywords=["flask", "fastapi"])],
        work=[ResumeWork(name="Acme Corp", position="Engineer")],
        education=[],
        projects=[],
        raw_text=SAMPLE_RESUME_TEXT,
    )


@pytest.fixture
def sample_evaluation():
    return EvaluationData(
        scores=Scores(
            open_source=CategoryScore(score=3, max=5, evidence="some oss work"),
            self_projects=CategoryScore(score=2, max=5, evidence="side projects"),
            production=CategoryScore(score=4, max=5, evidence="prod exp"),
            technical_skills=CategoryScore(score=4, max=10, evidence="strong tech stack"),
        ),
        bonus_points=BonusPoints(total=2.0, breakdown="demos + oss"),
        deductions=Deductions(total=1.0, reasons="no live demos"),
        key_strengths=["Full-stack dev", "Cloud exp"],
        areas_for_improvement=["Add portfolio"],
    )


@pytest.mark.asyncio
async def test_extract_resume(service):
    """Test that extract_resume delegates to pdf_extractor and returns ExtractedResume."""
    with (
        patch("app.hiring_agent.service.extract_pdf_text", return_value=SAMPLE_RESUME_TEXT) as mock_extract,
        patch("app.hiring_agent.service.parse_resume_sections") as mock_parse,
    ):
        mock_parse.return_value = ExtractedResume(
            basics=ResumeBasics(name="John Doe"),
            skills=[ResumeSkill(name="Python", keywords=["flask"])],
            work=[ResumeWork(name="Acme Corp", position="Engineer")],
            education=[],
            projects=[],
            raw_text=SAMPLE_RESUME_TEXT,
        )

        result = await service.extract_resume(b"fake pdf content")

        assert isinstance(result, ExtractedResume)
        assert result.basics.name == "John Doe"
        assert len(result.skills) == 1
        assert result.skills[0].name == "Python"
        assert len(result.work) == 1
        assert result.raw_text == SAMPLE_RESUME_TEXT
        mock_extract.assert_called_once_with(b"fake pdf content")


@pytest.mark.asyncio
async def test_extract_resume_empty_pdf(service):
    """Test that an empty PDF returns a stub ExtractedResume."""
    with (
        patch("app.hiring_agent.service.extract_pdf_text", return_value=""),
        patch("app.hiring_agent.service.parse_resume_sections") as mock_parse,
    ):
        mock_parse.return_value = ExtractedResume(
            basics=ResumeBasics(name=""),
            skills=[],
            work=[],
            education=[],
            projects=[],
            raw_text="",
        )

        result = await service.extract_resume(b"")
        assert isinstance(result, ExtractedResume)
        assert result.basics.name == ""
        assert result.raw_text == ""


@pytest.mark.asyncio
async def test_evaluate_resume_returns_evaluation_data(service, sample_resume):
    """Test evaluate_resume returns EvaluationData when LLM call succeeds."""
    with patch("app.hiring_agent.service.get_completion_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        from langchain_core.messages import HumanMessage

        mock_llm.ainvoke.return_value = HumanMessage(
            content=json.dumps(
                {
                    "scores": {
                        "open_source": {"score": 3, "max": 5, "evidence": "some oss work"},
                        "self_projects": {"score": 2, "max": 5, "evidence": "side projects"},
                        "production": {"score": 4, "max": 5, "evidence": "prod exp"},
                        "technical_skills": {"score": 4, "max": 10, "evidence": "strong tech stack"},
                    },
                    "bonus_points": {"total": 2.0, "breakdown": "demos + oss"},
                    "deductions": {"total": 1.0, "reasons": "no live demos"},
                    "key_strengths": ["Full-stack dev", "Cloud exp"],
                    "areas_for_improvement": ["Add portfolio"],
                }
            )
        )
        mock_get_llm.return_value = mock_llm

        result = await service.evaluate_resume("test resume text")

        assert result is not None
        assert isinstance(result, EvaluationData)
        assert result.scores.open_source.score == 3
        assert result.key_strengths == ["Full-stack dev", "Cloud exp"]


@pytest.mark.asyncio
async def test_compute_ats_analysis(service):
    """Test ATS analysis matches keywords between resume and JD."""
    resume_text = "I know Python, Docker, and AWS"
    jd_text = "Looking for Python developer with Docker and Kubernetes experience"

    result = await service.compute_ats_analysis(resume_text, jd_text)

    assert isinstance(result, ATSScore)
    assert "python" in result.matched_keywords
    assert "docker" in result.matched_keywords
    assert "kubernetes" in result.missing_keywords
    assert result.matched_count >= 2
    assert result.missing_count >= 1
    assert isinstance(result.keyword_coverage_pct, float)


@pytest.mark.asyncio
async def test_compute_ats_analysis_no_match(service):
    """Test ATS analysis with completely different texts."""
    resume_text = "I like cooking and baking"
    jd_text = "Kubernetes, Terraform, Go, Rust"

    result = await service.compute_ats_analysis(resume_text, jd_text)

    assert isinstance(result, ATSScore)
    assert result.matched_count == 0
    assert result.missing_count > 0
    assert result.keyword_coverage_pct == 0.0


@pytest.mark.asyncio
async def test_enrich_github_invalid_url(service):
    """Test github enrichment with invalid URL."""
    result = await service.enrich_github("not-a-url")
    assert "error" in result


@pytest.mark.asyncio
async def test_enrich_portfolio_invalid_url(service):
    """Test portfolio enrichment with invalid URL."""
    result = await service.enrich_portfolio("not-a-url")
    assert "error" in result


@pytest.mark.asyncio
async def test_enrich_portfolio_empty_url(service):
    """Test portfolio enrichment with empty URL."""
    result = await service.enrich_portfolio("")
    assert "error" in result


@pytest.mark.asyncio
async def test_generate_improvements_returns_list(service, sample_evaluation):
    """Test generate_improvements returns a list of ImprovementItem."""
    with patch.object(service, "_llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = None  # Force fallback

        result = await service.generate_improvements(sample_evaluation)

        assert isinstance(result, list)
        # Fallback should generate items for low-scoring categories
        assert len(result) >= 1
        assert all(isinstance(item, ImprovementItem) for item in result)


@pytest.mark.asyncio
async def test_extract_github_username(service):
    """Test GitHub username extraction from URLs."""
    # Private method via name mangling — access through the class method
    result = service._extract_github_username("https://github.com/johndoe")
    assert result == "johndoe"

    result = service._extract_github_username("https://github.com/johndoe/repo")
    assert result == "johndoe"

    result = service._extract_github_username("")
    assert result is None

    result = service._extract_github_username(None)
    assert result is None


@pytest.mark.asyncio
async def test_run_pipeline_no_resume(service):
    """Test pipeline returns None when resume extraction fails."""
    with patch.object(service, "extract_resume", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = None

        result = await service.run_pipeline(b"fake pdf")
        assert result is None
