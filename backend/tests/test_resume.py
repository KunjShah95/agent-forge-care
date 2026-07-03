import io
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import (
    TEST_USER_ID,
    MockResult,
    make_user,
    make_memory_entry,
    make_profile,
    setup_mock_execute,
)
from app.models.user import MemoryEntry, Profile, ProfileSkill, Skill


@pytest.mark.asyncio
async def test_list_resumes(auth_client, mock_db):
    entry1 = make_memory_entry(
        key="resume_cv.pdf",
        value={"filename": "cv.pdf", "pages": 2, "characters": 1500},
    )
    entry2 = make_memory_entry(
        key="resume_resume2024.pdf",
        value={"filename": "resume2024.pdf", "pages": 1, "characters": 800},
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [entry1, entry2]
    result = MockResult(scalars_list=[entry1, entry2])
    result.scalars = lambda: mock_scalars
    mock_db.execute = AsyncMock(return_value=result)

    response = await auth_client.get("/api/v1/resume")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["filename"] == "cv.pdf"
    assert data["items"][1]["filename"] == "resume2024.pdf"


@pytest.mark.asyncio
async def test_list_resumes_empty(auth_client, mock_db):
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    result = MockResult(scalars_list=[])
    result.scalars = lambda: mock_scalars
    mock_db.execute = AsyncMock(return_value=result)

    response = await auth_client.get("/api/v1/resume")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_upload_resume_success(auth_client, mock_db):
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"

    mock_result = MockResult(scalar_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock the hiring agent pdf extractor to raise (trigger pypdf fallback)
    with patch("app.hiring_agent.pdf_extractor.extract_pdf_text", side_effect=Exception("Mock: hiring agent unavailable")):
        with patch("app.api.v1.resume.pypdf.PdfReader") as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "John Doe\nSoftware Engineer\nExperience: Built APIs"
            mock_pdf_reader.return_value.pages = [mock_page]

            with patch("app.api.v1.resume.AgentMemory") as mock_agent_memory:
                mock_memory_instance = MagicMock()
                mock_agent_memory.return_value = mock_memory_instance

                with patch("app.api.v1.resume.get_text_embedding", new_callable=AsyncMock) as mock_embedding:
                    mock_embedding.return_value = [0.1] * 1536

                    files = {"file": ("test_resume.pdf", io.BytesIO(pdf_content), "application/pdf")}
                    response = await auth_client.post("/api/v1/resume/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_resume.pdf"
    assert data["pages"] == 1
    assert data["characters"] > 0
    assert "text" in data


@pytest.mark.asyncio
async def test_upload_resume_invalid_file(auth_client, mock_db):
    files = {"file": ("document.txt", io.BytesIO(b"not a pdf"), "text/plain")}
    response = await auth_client.post("/api/v1/resume/upload", files=files)

    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_resume_too_large(auth_client, mock_db):
    large_content = b"%PDF-1.4\n" + b"x" * (11 * 1024 * 1024)

    files = {"file": ("huge.pdf", io.BytesIO(large_content), "application/pdf")}
    response = await auth_client.post("/api/v1/resume/upload", files=files)

    assert response.status_code == 400
    assert "File too large" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ats_analysis_success(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={
            "filename": "cv.pdf",
            "text": "John Doe\nSoftware Engineer\nExperience\nEducation\nSkills\nPython\nDeveloped APIs\nManaged teams\nBuilt systems\nCreated solutions\nDelivered projects\nImproved performance by 50%\nLed initiatives\nDesigned architecture",
            "pages": 2,
            "characters": 500,
        },
    )

    profile = make_profile()
    skill1 = Skill(id="skill1", name="Python")
    skill2 = Skill(id="skill2", name="JavaScript")
    ps1 = ProfileSkill(profile_id=profile.id, skill_id="skill1", skill=skill1)
    ps2 = ProfileSkill(profile_id=profile.id, skill_id="skill2", skill=skill2)
    profile.skills = [ps1, ps2]

    resume_result = MockResult(scalar_value=resume_entry)
    profile_result = MockResult(scalar_value=profile)
    setup_mock_execute(mock_db, [resume_result, profile_result])

    response = await auth_client.get("/api/v1/resume/ats-analysis")

    assert response.status_code == 200
    data = response.json()
    assert "format_score" in data
    assert "keyword_score" in data
    assert "action_verb_score" in data
    assert "missing_keywords" in data
    assert "present_keywords" in data
    assert "suggestions" in data
    assert "summary" in data
    assert isinstance(data["format_score"], int)
    assert isinstance(data["keyword_score"], int)
    assert "Python" in data["present_keywords"]
    assert "JavaScript" in data["missing_keywords"]


@pytest.mark.asyncio
async def test_ats_analysis_no_resume(auth_client, mock_db):
    mock_result = MockResult(scalar_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/resume/ats-analysis")

    assert response.status_code == 404
    assert "No resume found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_search_resume(auth_client, mock_db):
    mock_vector_result = MagicMock()
    mock_vector_result.payload = {
        "text": "Software engineer with Python experience",
        "filename": "cv.pdf",
        "chunk_index": 0,
        "pages": 2,
        "characters": 500,
    }
    mock_vector_result.score = 0.95

    with patch("app.api.v1.resume.get_text_embedding", new_callable=AsyncMock) as mock_embedding:
        mock_embedding.return_value = [0.1] * 1536

        with patch("app.api.v1.resume.AgentMemory") as mock_agent_memory:
            mock_memory_instance = MagicMock()
            mock_memory_instance.search_vectors.return_value = [mock_vector_result]
            mock_agent_memory.return_value = mock_memory_instance

            response = await auth_client.get("/api/v1/resume/search?q=python")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["filename"] == "cv.pdf"
    assert data["items"][0]["score"] == 0.95
    assert "text" in data["items"][0]


@pytest.mark.asyncio
async def test_delete_resume_success(auth_client, mock_db):
    resume_entry = make_memory_entry(
        key="resume_cv.pdf",
        value={"filename": "cv.pdf", "pages": 2, "characters": 1500},
    )

    mock_result = MockResult(scalar_value=resume_entry)
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.delete("/api/v1/resume/cv.pdf")

    assert response.status_code == 204
    mock_db.delete.assert_called_once_with(resume_entry)


@pytest.mark.asyncio
async def test_delete_resume_not_found(auth_client, mock_db):
    mock_result = MockResult(scalar_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.delete("/api/v1/resume/nonexistent.pdf")

    assert response.status_code == 404
    assert "Resume not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_resumes_requires_auth(async_client):
    response = await async_client.get("/api/v1/resume")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_resume_requires_auth(async_client):
    files = {"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")}
    response = await async_client.post("/api/v1/resume/upload", files=files)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ats_analysis_requires_auth(async_client):
    response = await async_client.get("/api/v1/resume/ats-analysis")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_resume_requires_auth(async_client):
    response = await async_client.get("/api/v1/resume/search?q=test")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_resume_requires_auth(async_client):
    response = await async_client.delete("/api/v1/resume/test.pdf")
    assert response.status_code == 401
