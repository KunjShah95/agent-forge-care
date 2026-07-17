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
async def test_unknown_agent_type_is_skipped(mock_db):
    """OrchestratorAgent delegates to run_planner_graph — mock the graph output."""
    mock_graph_output = {
        "results": {
            "nonexistent": {
                "status": "skipped",
                "message": "No handler for agent type: nonexistent",
                "duration_ms": None,
            }
        },
        "reflection_scores": {},
        "detail": {},
    }

    with patch(
        "app.agents.graph_engine.run_planner_graph",
        new_callable=AsyncMock,
        return_value=mock_graph_output,
    ):
        agent = OrchestratorAgent(mock_db, "test-user")
        result = await agent.run({"goal": "test goal"})
        results = result.output.get("results", {})
        assert "nonexistent" in results
        assert results["nonexistent"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_resume_agent_dispatched(mock_db):
    """OrchestratorAgent delegates to run_planner_graph — mock the graph output."""
    mock_graph_output = {
        "results": {
            "resume": {
                "status": "completed",
                "message": "Resume tailored for SWE roles",
                "duration_ms": 1200.5,
            }
        },
        "reflection_scores": {"resume": {"accuracy": 9, "total": 40}},
        "detail": {"resume": {"items": [], "message": "Resume tailored for SWE roles"}},
    }

    with patch(
        "app.agents.graph_engine.run_planner_graph",
        new_callable=AsyncMock,
        return_value=mock_graph_output,
    ):
        agent = OrchestratorAgent(mock_db, "test-user")
        result = await agent.run({"goal": "tailor resume for swe"})
        assert result.status == "completed"
        assert "resume" in result.output.get("results", {})
