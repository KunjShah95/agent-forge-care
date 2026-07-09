from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator.service import AGENT_REGISTRY, OrchestratorAgent


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_profile():
    p = MagicMock()
    p.id = "prof-id"
    p.target_locations = []
    p.role_types = []
    p.career_goal = ""
    return p


@pytest.mark.asyncio
async def test_registry_has_all_agents():
    assert "resume" in AGENT_REGISTRY
    assert "interview" in AGENT_REGISTRY
    assert "networking" in AGENT_REGISTRY
    assert "monitor" in AGENT_REGISTRY
    assert "guidance" in AGENT_REGISTRY


@pytest.mark.asyncio
async def test_empty_goal_returns_error(mock_db):
    agent = OrchestratorAgent(mock_db, "test-user")
    result = await agent.run({"goal": ""})
    assert result.output.get("error") == "No goal provided"


@pytest.mark.asyncio
async def test_unknown_agent_type_is_skipped(mock_db, mock_profile):
    mock_ps = AsyncMock()
    mock_ps.get_or_create_profile.return_value = mock_profile
    mock_ps.get_skill_names.return_value = []

    mock_ms = AsyncMock()
    mock_ms.get_user_context.return_value = {}

    with (
        patch("app.agents.orchestrator.service.ProfileService", return_value=mock_ps),
        patch("app.agents.orchestrator.service.MemoryService", return_value=mock_ms),
        patch.object(OrchestratorAgent, "_persist_plan"),
        patch.object(OrchestratorAgent, "_persist_results"),
        patch(
            "app.agents.orchestrator.service.decompose_goal_with_llm",
            return_value=[{"agent": "nonexistent", "action": "test", "params": {}, "priority": 5}],
        ),
    ):
        agent = OrchestratorAgent(mock_db, "test-user")
        result = await agent.run({"goal": "test goal"})
        results = result.output.get("results", {})
        assert "nonexistent" in results
        assert results["nonexistent"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_resume_agent_dispatched(mock_db, mock_profile):
    mock_ps = AsyncMock()
    mock_ps.get_or_create_profile.return_value = mock_profile
    mock_ps.get_skill_names.return_value = ["python", "react"]

    mock_ms = AsyncMock()
    mock_ms.get_user_context.return_value = {"skills": ["python"]}

    with (
        patch("app.agents.orchestrator.service.ProfileService", return_value=mock_ps),
        patch("app.agents.orchestrator.service.MemoryService", return_value=mock_ms),
        patch.object(OrchestratorAgent, "_persist_plan"),
        patch.object(OrchestratorAgent, "_persist_results"),
        patch(
            "app.agents.orchestrator.service.decompose_goal_with_llm",
            return_value=[{"agent": "resume", "action": "tailor", "params": {"role_type": "swe"}, "priority": 1}],
        ),
    ):
        agent = OrchestratorAgent(mock_db, "test-user")
        result = await agent.run({"goal": "tailor resume for swe"})
        assert result.status == "completed"
        assert "resume" in result.output.get("results", {})
