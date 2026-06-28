import io
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import TEST_USER_ID, MockResult, make_memory_entry


SAMPLE_RESUME_TEXT = (
    "John Doe\nSoftware Engineer\n"
    "Python, JavaScript, React, Node.js\n"
    "Developed APIs, built microservices, deployed on AWS\n"
    "Led team of 5 engineers, managed agile sprints\n"
)


def mock_llm_chain(response_text):
    chain = AsyncMock()
    chain.ainvoke.return_value = response_text
    return chain


resume_extraction = {
    "basics": {"name": "John Doe", "email": "john@example.com"},
    "skills": [{"name": "Python", "keywords": ["flask", "fastapi"]}],
    "work": [{"name": "Acme Corp", "position": "Engineer"}],
    "education": [{"institution": "MIT", "area": "CS"}],
    "projects": [{"name": "MyApp", "technologies": ["react", "node"]}],
    "raw_text": SAMPLE_RESUME_TEXT,
}


evaluation_json = json.dumps({
    "scores": {
        "open_source": {"score": 3.0, "max": 5, "evidence": "some oss work"},
        "self_projects": {"score": 2.0, "max": 5, "evidence": "side projects"},
        "production": {"score": 4.0, "max": 5, "evidence": "prod exp"},
        "technical_skills": {"score": 4.0, "max": 5, "evidence": "strong tech stack"},
    },
    "bonus_points": {"total": 2.0, "breakdown": "demos + oss"},
    "deductions": {"total": 1.0, "reasons": "no live demos"},
    "key_strengths": ["Full-stack dev", "Cloud exp"],
    "areas_for_improvement": ["Add portfolio"],
})

ats_json = json.dumps({
    "keyword_coverage_pct": 65.0,
    "matched_keywords": ["python", "aws"],
    "missing_keywords": ["docker"],
    "matched_count": 2,
    "missing_count": 1,
    "suggestions": ["Add docker"],
    "experience_years": 3,
    "resume_experience_years": 5,
})

jd_match_json = json.dumps({
    "skill_match": {"matched": ["python"], "missing": ["java"], "score": 50},
    "experience_match": {"assessment": "good fit", "years": 3},
    "education_match": {"requirement": "BS", "status": "met"},
    "project_relevance": {"relevant": 2, "score": 70},
    "overall_score": 72,
    "overall_assessment": "Strong candidate",
    "gap_analysis": [{"area": "java", "severity": "low"}],
})

cover_letter = "# Cover Letter\n\nDear Hiring Manager..."

github_data = json.dumps({
    "repos": [{"name": "project-x", "stars": 42}],
    "total_stars": 42,
    "languages": {"Python": 5000},
    "summary": "Solid github profile",
})

portfolio_data = json.dumps({
    "url": "https://johndoe.dev",
    "role": "Full Stack Dev",
    "summary": "impressive portfolio",
    "projects": [{"name": "Portfolio Site"}],
})


@pytest.mark.asyncio
async def test_hiring_pipeline_full(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_result.all.return_value = [resume_entry]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.multiple(
        "app.hiring_agent.service.HiringAgentService",
        _summarize_resume=AsyncMock(return_value=resume_extraction),
        _evaluate_candidate=AsyncMock(return_value=json.loads(evaluation_json)),
        _recommend_improvements=AsyncMock(return_value=[
            {"category": "Skills", "suggestion": "Add Docker", "impact": "high", "effort": "low", "priority_score": 8},
        ]),
        _check_live_demos=AsyncMock(return_value=[{"url": "https://demo.dev", "status": "live"}]),
    ):
        payload = {"github_url": "https://github.com/johndoe", "portfolio_url": "https://johndoe.dev"}
        response = await auth_client.post("/api/v1/hiring-agent/pipeline", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["overall_score"] >= 0
    assert "resume" in data
    assert "evaluation" in data
    assert "improvements" in data
    assert "live_demo_status" in data


@pytest.mark.asyncio
async def test_hiring_extract_when_no_resume(auth_client, mock_db):
    mock_result = MockResult(scalar_value=None)
    mock_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/hiring-agent/extract")
    assert response.status_code == 404
    assert "No resume found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_hiring_extract_success(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.hiring_agent.service.HiringAgentService._summarize_resume", new_callable=AsyncMock) as mock_sum:
        mock_sum.return_value = resume_extraction
        response = await auth_client.get("/api/v1/hiring-agent/extract")

    assert response.status_code == 200
    data = response.json()
    assert data["basics"]["name"] == "John Doe"
    assert data["skills"][0]["name"] == "Python"


@pytest.mark.asyncio
async def test_hiring_evaluate_text(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.hiring_agent.service.HiringAgentService._evaluate_candidate", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = json.loads(evaluation_json)
        response = await auth_client.post("/api/v1/hiring-agent/evaluate-text")

    assert response.status_code == 200
    data = response.json()
    assert "scores" in data
    assert data["key_strengths"][0] == "Full-stack dev"


@pytest.mark.asyncio
async def test_hiring_ats(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.hiring_agent.service.HiringAgentService._summarize_resume", new_callable=AsyncMock) as mock_sum:
        mock_sum.return_value = resume_extraction
        with patch("app.hiring_agent.service.HiringAgentService._compute_ats_score", new_callable=AsyncMock) as mock_ats:
            mock_ats.return_value = json.loads(ats_json)
            response = await auth_client.get("/api/v1/hiring-agent/ats")

    assert response.status_code == 200
    data = response.json()
    assert data["keyword_coverage_pct"] == 65.0
    assert "python" in data["matched_keywords"]


@pytest.mark.asyncio
async def test_hiring_match_jd(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.hiring_agent.service.HiringAgentService._summarize_resume", new_callable=AsyncMock) as mock_sum:
        mock_sum.return_value = resume_extraction
        with patch("app.hiring_agent.service.HiringAgentService._match_jd", new_callable=AsyncMock) as mock_jd:
            mock_jd.return_value = json.loads(jd_match_json)
            response = await auth_client.post("/api/v1/hiring-agent/match-jd", json={"job_description": "Looking for a Python developer with Java experience"})

    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 72
    assert data["overall_assessment"] == "Strong candidate"


@pytest.mark.asyncio
async def test_hiring_cover_letter(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.hiring_agent.service.HiringAgentService._generate_cover_letter", new_callable=AsyncMock) as mock_cl:
        mock_cl.return_value = cover_letter
        response = await auth_client.post("/api/v1/hiring-agent/cover-letter", json={
            "job_title": "Software Engineer",
            "company_name": "Acme Corp",
            "job_description": "Building cool stuff",
        })

    assert response.status_code == 200
    assert "# Cover Letter" in response.text


@pytest.mark.asyncio
async def test_hiring_github_enrich(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.hiring_agent.service.HiringAgentService._enrich_github", new_callable=AsyncMock) as mock_gh:
        mock_gh.return_value = json.loads(github_data)
        response = await auth_client.post("/api/v1/hiring-agent/github-enrich", json={"github_url": "https://github.com/johndoe"})

    assert response.status_code == 200
    data = response.json()
    assert data["total_stars"] == 42
    assert data["repos"][0]["name"] == "project-x"


@pytest.mark.asyncio
async def test_hiring_portfolio_enrich(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.hiring_agent.service.HiringAgentService._enrich_portfolio", new_callable=AsyncMock) as mock_pf:
        mock_pf.return_value = json.loads(portfolio_data)
        response = await auth_client.post("/api/v1/hiring-agent/portfolio-enrich", json={"portfolio_url": "https://johndoe.dev"})

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "Full Stack Dev"
    assert data["projects"][0]["name"] == "Portfolio Site"


@pytest.mark.asyncio
async def test_hiring_report(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"text": SAMPLE_RESUME_TEXT, "filename": "cv.pdf", "pages": 1, "characters": len(SAMPLE_RESUME_TEXT)},
    )
    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.multiple(
        "app.hiring_agent.service.HiringAgentService",
        _summarize_resume=AsyncMock(return_value=resume_extraction),
        _evaluate_candidate=AsyncMock(return_value=json.loads(evaluation_json)),
        _compute_ats_score=AsyncMock(return_value=json.loads(ats_json)),
        _recommend_improvements=AsyncMock(return_value=[
            {"category": "Skills", "suggestion": "Add Docker", "impact": "high", "effort": "low", "priority_score": 8},
        ]),
        _check_live_demos=AsyncMock(return_value=[{"url": "https://demo.dev", "status": "live"}]),
    ):
        response = await auth_client.get("/api/v1/hiring-agent/report")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "John Doe" in response.text
