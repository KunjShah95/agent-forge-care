"""
End-to-end synthetic tests for the full planner agent pipeline.

Exercises the entire flow:
  1. Goal decomposition (keyword fallback — no LLM needed)
  2. Task filtering by user context (dynamic routing)
  3. Parallel agent dispatch with retry/timeout
  4. Reflection scoring and regeneration logic
  5. Final response formatting
  6. API endpoints that wire everything together

All agent handlers are mocked to test orchestration logic only.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime, timezone

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db
from app.dependencies import get_current_user
from app.agents.planner import (
    _keyword_decompose,
    format_planner_response,
    decompose_goal_with_llm,
)
from app.agents.graph import (
    build_planner_graph,
    PlannerGraphState,
    gen_id,
    _execute_with_retry,
    _filter_tasks_by_context,
    _score_agent_output,
    should_regenerate,
    get_planner_graph,
)
from app.agents.internship_agent import _demo_internships
from app.agents.job_agent import _demo_jobs
from app.models.user import AgentType, TaskStatus
from tests.conftest import TEST_USER_ID, make_user, MockResult


# =============================================================================
# Part 1: Goal Decomposition (keyword fallback)
# =============================================================================


class TestGoalDecomposition:
    """Test keyword-based goal decomposition produces correct agent tasks."""

    def setup_profile(self) -> dict:
        return {
            "id": "test-profile-id",
            "skills": ["Python", "TypeScript", "React"],
            "target_locations": ["Remote", "Ahmedabad"],
            "role_types": ["Internship"],
            "career_goal": "ML Research Intern",
        }

    def test_internship_goal_dispatches_internship_agent(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose("Find AI internships in Ahmedabad", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "internship" in agents
        params = tasks[0]["params"]
        assert params["location"] == "Ahmedabad"

    def test_job_goal_dispatches_job_agent(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose("Find full-time React developer roles", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "job" in agents

    def test_complex_goal_dispatches_multiple_agents(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose(
            "Find AI internships and prepare for interviews at Anthropic",
            profile,
            {},
        )
        agents = [t["agent"] for t in tasks]
        assert "internship" in agents
        assert "interview" in agents

    def test_vague_goal_defaults_to_monitor(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose("Help me find something good", profile, {})
        agents = [t["agent"] for t in tasks]
        assert len(tasks) == 1
        assert tasks[0]["agent"] == "monitor"

    def test_research_goal_dispatches_research_agent(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose("Research Anthropic before interview", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "research" in agents

    def test_resume_goal_dispatches_resume_agent(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose("Tailor my resume for ML roles", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "resume" in agents

    def test_networking_goal_dispatches_networking_agent(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose("Help me network at Stripe", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "networking" in agents

    def test_all_tasks_have_required_fields(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose(
            "Find internships and jobs in AI and research Anthropic", profile, {}
        )
        for t in tasks:
            assert "agent" in t
            assert "action" in t
            assert "params" in t and isinstance(t["params"], dict)
            assert "priority" in t and isinstance(t["priority"], int)

    def test_extracts_location(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose("Internships in San Francisco", profile, {})
        params = tasks[0]["params"]
        assert params["location"] == "San Francisco"

    def test_extracts_skills(self):
        profile = self.setup_profile()
        tasks = _keyword_decompose("Python ML internship", profile, {})
        params = tasks[0]["params"]
        # Keyword-based extraction returns lowercase skills
        assert "python" in [s.lower() for s in params.get("skills", [])]


# =============================================================================
# Part 2: Dynamic Agent Routing (filtering)
# =============================================================================


class TestDynamicRouting:
    """Test that agents are correctly filtered based on user profile context."""

    def test_skips_internship_when_role_types_exclude_intern(self):
        profile = {"role_types": ["Full-time"], "target_locations": [], "career_goal": ""}
        tasks = [
            {"agent": "internship", "params": {"query": "test"}, "priority": 1},
            {"agent": "job", "params": {"query": "test"}, "priority": 1},
        ]
        filtered = _filter_tasks_by_context(tasks, profile)
        agents = [t["agent"] for t in filtered]
        assert "internship" not in agents
        assert "job" in agents

    def test_skips_job_when_user_only_wants_internships(self):
        profile = {"role_types": ["Internship"], "target_locations": [], "career_goal": ""}
        tasks = [
            {"agent": "internship", "params": {"query": "test"}, "priority": 1},
            {"agent": "job", "params": {"query": "test"}, "priority": 1},
        ]
        filtered = _filter_tasks_by_context(tasks, profile)
        agents = [t["agent"] for t in filtered]
        assert "internship" in agents
        assert "job" not in agents

    def test_skips_research_when_no_query_and_no_target(self):
        profile = {"role_types": [], "target_locations": [], "career_goal": ""}
        tasks = [
            {"agent": "research", "params": {"query": ""}, "priority": 2},
            {"agent": "monitor", "params": {"query": "test"}, "priority": 1},
        ]
        filtered = _filter_tasks_by_context(tasks, profile)
        agents = [t["agent"] for t in filtered]
        assert "research" not in agents

    def test_enriches_task_with_career_goal(self):
        profile = {"role_types": ["Internship"], "target_locations": [], "career_goal": "ML Engineer"}
        tasks = [
            {"agent": "internship", "params": {"query": "test"}, "priority": 1},
        ]
        filtered = _filter_tasks_by_context(tasks, profile)
        params = filtered[0]["params"]
        assert "career_goal" in params
        assert params["career_goal"] == "ml engineer"

    def test_empty_tasks_returns_empty(self):
        profile = {"role_types": [], "target_locations": [], "career_goal": ""}
        filtered = _filter_tasks_by_context([], profile)
        assert filtered == []


# =============================================================================
# Part 3: Parallel Agent Dispatch & Retry
# =============================================================================


@pytest.mark.asyncio
@patch("app.agents.graph._execute_single_agent_inner", new_callable=AsyncMock)
async def test_execute_with_retry_success_first_try(mock_inner):
    """Agent succeeds on first attempt — no retry needed."""
    mock_inner.return_value = {"test_agent": {"items": [{"id": "1"}]}}
    result = await _execute_with_retry("test_agent", "user1", {}, None)
    assert "test_agent" in result
    assert mock_inner.call_count == 1


@pytest.mark.asyncio
@patch("app.agents.graph._execute_single_agent_inner", new_callable=AsyncMock)
async def test_execute_with_retry_fails_all_attempts(mock_inner):
    """Agent fails all attempts — returns error dict."""
    mock_inner.side_effect = RuntimeError("Service unavailable")
    result = await _execute_with_retry("test_agent", "user1", {}, None)
    assert "error" in result["test_agent"]
    assert mock_inner.call_count == 3  # 3 attempts total (AGENT_MAX_RETRIES + 1)


@pytest.mark.asyncio
@patch("app.agents.graph._execute_single_agent_inner", new_callable=AsyncMock)
async def test_execute_with_retry_succeeds_on_retry(mock_inner):
    """Agent fails twice then succeeds on third attempt."""
    mock_inner.side_effect = [
        RuntimeError("Timeout"),
        RuntimeError("Busy"),
        {"test_agent": {"items": [{"id": "1"}]}},
    ]
    result = await _execute_with_retry("test_agent", "user1", {}, None)
    assert "test_agent" in result
    assert "error" not in result["test_agent"]
    assert mock_inner.call_count == 3


# =============================================================================
# Part 4: Reflection Scoring
# =============================================================================


@pytest.mark.asyncio
async def test_score_agent_output_error_returns_zeros():
    """Agent output with error should get 0 across all dimensions."""
    scores = await _score_agent_output("test", {"error": "Failed"}, "goal", {"skills": []})
    assert scores["total"] == 0
    assert scores["accuracy"] == 0
    assert scores["feedback"] == "Agent returned error or empty result"


@pytest.mark.asyncio
async def test_score_agent_output_good_result():
    """Agent with items, message, and suggestions should score well."""
    result = {
        "items": [{"id": "1"}, {"id": "2"}],
        "message": "Found 2 matches for your Python and ML skills",
        "suggestions": ["Tailor resume", "Practice interviews"],
    }
    scores = await _score_agent_output("internship", result, "Find Python jobs", {"skills": ["Python"]})
    assert scores["total"] >= 30  # Should score well on most dimensions
    assert scores["actionability"] >= 8  # Items + suggestions


@pytest.mark.asyncio
async def test_score_agent_output_poor_result():
    """Agent with generic/no content should score low (below threshold)."""
    # Empty dict gives minimum possible score for a non-error result
    result = {}
    scores = await _score_agent_output("test", result, "goal", {"skills": []})
    assert scores["total"] < 33  # Well below passing threshold of 35


def test_should_regenerate_condition():
    """Only regenerate when below threshold and under iteration limit."""
    state: PlannerGraphState = {
        "user_id": "u1",
        "goal": "test",
        "profile": {},
        "memory_context": {},
        "tasks": [],
        "results": {},
        "final_response": "",
        "error": None,
        "planner_goal_id": None,
        "planner_task_id": None,
        "reflection_scores": {},
        "reflection_iterations": 0,
        "needs_regeneration": True,
    }
    assert should_regenerate(state) == "dispatch_all_agents"

    state["reflection_iterations"] = 2
    assert should_regenerate(state) == "generate_final_response"

    state["reflection_iterations"] = 0
    state["needs_regeneration"] = False
    assert should_regenerate(state) == "generate_final_response"


# =============================================================================
# Part 5: Response Formatting
# =============================================================================


class TestResponseFormatting:
    """Test that planner responses are well-formatted."""

    def test_format_with_items(self):
        result = format_planner_response(
            "Find internships",
            {"internship": {"items": [{"id": "1"}], "message": "Found 1 match"}},
        )
        assert "Internship" in result
        assert "1 match" in result

    def test_format_with_errors(self):
        result = format_planner_response(
            "Find internships",
            {"internship": {"error": "API timeout"}},
        )
        assert "Internship" in result
        assert "⚠" in result or "timeout" in result

    def test_format_empty_results(self):
        result = format_planner_response("Find internships", {})
        assert "No results found" in result

    def test_format_research_result(self):
        """Research results are nested under 'results' key but have 'message'."""
        result = format_planner_response(
            "Research Anthropic",
            {"research": {
                "results": {"company_info": {"name": "Anthropic"}},
                "summary": "Anthropic is an AI safety company",
                "message": "Research complete on 1 topics",
            }},
        )
        assert "Research" in result
        assert "1 topics" in result  # Falls back to 'message'

    def test_format_guidance_result(self):
        result = format_planner_response(
            "Career advice",
            {"planner": {
                "guidance": {"next_steps": ["Apply to jobs"]},
                "message": "Career guidance generated",
            }},
        )
        assert "Planner" in result


# =============================================================================
# Part 6: Full Graph Pipeline (synthetic end-to-end)
# =============================================================================


@pytest.mark.asyncio
@patch("app.search.adapters.SearchAdapter.search", new_callable=AsyncMock)
@patch("app.agents.graph.async_session_factory")
async def test_full_planner_graph_pipeline(mock_session_factory, mock_search):
    """
    Synthetic end-to-end test of the full LangGraph pipeline.

    Tests:
      - Goal decomposition (keyword fallback)
      - Parallel agent dispatch calling real _execute_single_agent_inner
      - Agent handler invocation (mocked)
      - Reflection scoring
      - Final response generation
    """
    # Create a proper mock DB session that simulates SQLAlchemy execute
    from tests.conftest import MockResult

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MockResult(scalar_value=None))
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.close = AsyncMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_db

    # Mock the search adapter to return nothing, forcing fallback to demo data
    mock_search.return_value = []

    graph = build_planner_graph()

    initial_state: PlannerGraphState = {
        "user_id": "test-user",
        "goal": "Find AI internships in San Francisco",
        "profile": {
            "id": "profile-1",
            "skills": ["Python", "PyTorch"],
            "target_locations": ["San Francisco"],
            "role_types": ["Internship"],
            "career_goal": "ML Research Intern",
        },
        "memory_context": {},
        "tasks": [],
        "results": {},
        "final_response": "",
        "error": None,
        "planner_goal_id": None,
        "planner_task_id": None,
        "reflection_scores": {},
        "reflection_iterations": 0,
        "needs_regeneration": False,
    }

    final_state = await graph.ainvoke(initial_state)

    # Verify the pipeline completed
    assert final_state["planner_task_id"] is not None
    assert "final_response" in final_state
    assert final_state["final_response"] != ""

    # Verify internship agent was dispatched (falls back to demo data since search returns empty)
    assert "internship" in final_state.get("results", {})
    assert final_state["results"]["internship"]["total"] >= 1

    # Verify reflection ran
    assert "reflection_scores" in final_state
    assert len(final_state["reflection_scores"]) > 0


@pytest.mark.asyncio
@patch("app.agents.graph.async_session_factory")
async def test_planner_graph_handles_empty_tasks(mock_session_factory):
    from tests.conftest import MockResult

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MockResult(scalar_value=None))
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.close = AsyncMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_db
    """Graph handles the case where no tasks are generated."""
    graph = build_planner_graph()

    initial_state: PlannerGraphState = {
        "user_id": "test-user",
        "goal": "",
        "profile": {"id": "p1", "skills": [], "target_locations": [], "role_types": [], "career_goal": ""},
        "memory_context": {},
        "tasks": [],
        "results": {},
        "final_response": "",
        "error": None,
        "planner_goal_id": None,
        "planner_task_id": None,
        "reflection_scores": {},
        "reflection_iterations": 0,
        "needs_regeneration": False,
    }

    final_state = await graph.ainvoke(initial_state)
    # Should still complete without error (monitor handles empty / vague goals)
    assert "final_response" in final_state


# =============================================================================
# Part 7: API End-to-End Tests
# =============================================================================


@pytest.mark.asyncio
@patch("app.agents.graph.run_planner_agent", new_callable=AsyncMock)
async def test_api_planner_full_flow(mock_run_planner, mock_db, auth_client):
    """The planner API endpoint correctly receives a goal and returns a task ID."""
    from tests.conftest import _uid

    expected_task_id = _uid()
    mock_run_planner.return_value = expected_task_id

    response = await auth_client.post(
        "/api/v1/agents/planner/run",
        json={"goal": "Find ML internships in San Francisco"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["task_id"] == expected_task_id
    mock_run_planner.assert_called_once_with(str(TEST_USER_ID), "Find ML internships in San Francisco")


@pytest.mark.asyncio
async def test_api_planner_status_flow(mock_db, auth_client):
    """The planner status endpoint returns system state."""
    from tests.conftest import make_agent_task

    task = make_agent_task(agent_type=AgentType.planner, status=TaskStatus.running)
    count_result = MockResult(scalar_value=5)
    latest_result = MockResult(scalar_value=task)

    mock_db.execute = AsyncMock(side_effect=[count_result, latest_result])

    response = await auth_client.get("/api/v1/agents/planner/status")
    assert response.status_code == 200
    data = response.json()
    assert data["total_goals"] == 5
    assert data["is_running"] is True


@pytest.mark.asyncio
@patch("app.agents.internship_agent.discover_internships", new_callable=AsyncMock)
async def test_api_internship_discover_flow(mock_discover, mock_db, auth_client):
    """The internship discovery API works end-to-end."""
    mock_discover.return_value = {
        "items": [{"id": "1", "title": "ML Research Intern", "company": "Anthropic"}],
        "total": 1,
        "message": "Found 1 match",
    }

    response = await auth_client.post(
        "/api/v1/agents/internship-discover",
        json={"query": "ML internship", "location": "San Francisco"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["company"] == "Anthropic"


@pytest.mark.asyncio
@patch("app.agents.assistant_agent.prepare_interview", new_callable=AsyncMock)
async def test_api_interview_prep_role_mapping(mock_prep, mock_db, auth_client):
    """Frontend sends 'role' but backend expects 'role_type' — ensure mapping works."""
    mock_prep.return_value = {
        "questions": [{"skill": "general", "question": "Tell me about yourself", "type": "behavioral"}],
        "message": "Ready",
    }

    response = await auth_client.post(
        "/api/v1/agents/interview-prep",
        json={"company": "Google", "role": "ML Engineer", "type": "behavioral"},
    )
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 1


@pytest.mark.asyncio
@patch("app.agents.research_agent.conduct_research", new_callable=AsyncMock)
async def test_api_research_company_query_mapping(mock_research, mock_db, auth_client):
    """The research endpoint correctly maps 'company' to 'query' for the agent."""
    mock_research.return_value = {
        "results": {"company_info": {"name": "Anthropic", "industry": "AI Safety"}},
        "summary": "Anthropic is an AI safety company",
        "message": "Research complete",
    }

    response = await auth_client.post(
        "/api/v1/agents/research",
        json={"company": "Anthropic", "topics": ["AI Safety"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["results"]["company_info"]["name"] == "Anthropic"
    # Verify the agent received 'query' param (mapped from 'company')
    mock_research.assert_called_once()
    call_kwargs = mock_research.call_args[0][1]
    assert "query" in call_kwargs


@pytest.mark.asyncio
@patch("app.agents.graph.run_planner_agent", new_callable=AsyncMock)
async def test_api_retry_planner_task_updates_status(mock_run, mock_db, auth_client):
    """Retrying a planner task should set original task back to completed."""
    from tests.conftest import make_agent_task, _uid, setup_mock_execute

    task = make_agent_task(
        agent_type=AgentType.planner,
        status=TaskStatus.failed,
        input={"goal": "Find ML internships"},
    )
    mock_run.return_value = _uid()
    setup_mock_execute(mock_db, [MockResult(scalar_value=task)])

    response = await auth_client.post(f"/api/v1/agents/tasks/{task.id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Original task should be marked as completed (was set to running, then completed)
    assert task.completed_at is not None


# =============================================================================
# Part 8: Demo data quality checks
# =============================================================================


class TestDemoData:
    """Verify demo data used by agents is well-formed."""

    def test_demo_internships_are_valid(self):
        results = _demo_internships("test", "Remote")
        assert len(results) >= 1
        for r in results:
            assert "title" in r
            assert "company" in r
            assert "description" in r
            assert "skills" in r
            assert "apply_url" in r

    def test_demo_jobs_are_valid(self):
        from app.agents.job_agent import _demo_jobs
        results = _demo_jobs("test", "Remote")
        assert len(results) >= 1
        for r in results:
            assert "title" in r
            assert "company" in r
            assert "salary_min" in r
            assert "salary_max" in r

    def test_demo_data_utility(self):
        from app.utils.demo_data import generate_demo_opportunities
        results = generate_demo_opportunities(AgentType.internship, "ML", "Remote")
        assert len(results) > 0
        assert all("title" in r and "company" in r for r in results)
