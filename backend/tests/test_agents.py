from unittest.mock import AsyncMock, patch

import pytest

from app.models.user import AgentType, TaskStatus
from tests.conftest import (
    TEST_USER_ID,
    MockResult,
    _uid,
    make_agent_task,
    setup_mock_execute,
)


@pytest.mark.asyncio
@patch("app.agents.orchestrator.service.run_planner_agent", new_callable=AsyncMock)
async def test_planner_run_success(mock_run, auth_client, mock_db):
    task_id = _uid()
    mock_run.return_value = (task_id, None)

    response = await auth_client.post(
        "/api/v1/agents/planner/run",
        json={"goal": "Find ML internships in San Francisco"},
    )
    assert response.status_code == 202
    assert response.json()["task_id"] == task_id
    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_planner_run_missing_goal(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/agents/planner/run",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_planner_run_no_auth(async_client):
    response = await async_client.post(
        "/api/v1/agents/planner/run",
        json={"goal": "test"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_planner_status(auth_client, mock_db):
    task = make_agent_task(agent_type=AgentType.planner, status=TaskStatus.running)
    count_result = MockResult(scalar_value=3)
    latest_result = MockResult(scalar_value=task)

    mock_db.execute = AsyncMock(side_effect=[count_result, latest_result])

    response = await auth_client.get("/api/v1/agents/planner/status")
    assert response.status_code == 200
    data = response.json()
    assert data["total_goals"] == 3
    assert data["is_running"] is True


@pytest.mark.asyncio
async def test_get_planner_status_no_tasks(auth_client, mock_db):
    count_result = MockResult(scalar_value=0)
    latest_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, latest_result])

    response = await auth_client.get("/api/v1/agents/planner/status")
    assert response.status_code == 200
    data = response.json()
    assert data["total_goals"] == 0
    assert data["is_running"] is False
    assert data["latest_goal"] is None


@pytest.mark.asyncio
async def test_list_tasks(auth_client, mock_db):
    task1 = make_agent_task(agent_type=AgentType.planner)
    task2 = make_agent_task(agent_type=AgentType.internship)
    mock_result = MockResult(scalars_list=[task1, task2])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/agents/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_tasks_empty(auth_client, mock_db):
    mock_result = MockResult(scalars_list=[])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/agents/tasks")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_list_tasks_filter_by_status(auth_client, mock_db):
    task = make_agent_task(status=TaskStatus.completed)
    mock_result = MockResult(scalars_list=[task])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/agents/tasks?status=completed")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_tasks_filter_by_agent_type(auth_client, mock_db):
    task = make_agent_task(agent_type=AgentType.internship)
    mock_result = MockResult(scalars_list=[task])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/agents/tasks?agent_type=internship")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_tasks_no_auth(async_client):
    response = await async_client.get("/api/v1/agents/tasks")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_task_success(auth_client, mock_db):
    task = make_agent_task()
    setup_mock_execute(mock_db, [MockResult(scalar_value=task)])

    response = await auth_client.get(f"/api/v1/agents/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(task.id)
    assert data["agent_type"] == "planner"


@pytest.mark.asyncio
async def test_get_task_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.get(f"/api/v1/agents/tasks/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
@patch("app.agents.orchestrator.service.run_opportunity_scan", new_callable=AsyncMock)
async def test_monitor_run_success(mock_scan, auth_client, mock_db):
    task_id = _uid()
    mock_scan.return_value = task_id

    response = await auth_client.post("/api/v1/agents/monitor/run")
    assert response.status_code == 202
    assert response.json()["task_id"] == task_id


@pytest.mark.asyncio
async def test_monitor_alerts(auth_client, mock_db):
    task = make_agent_task(
        agent_type=AgentType.monitor,
        output={"alerts": [{"title": "New ML Internship at Google", "score": 92}]},
    )
    mock_result = MockResult(scalars_list=[task])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/agents/monitor/alerts")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "New ML Internship at Google"


@pytest.mark.asyncio
async def test_monitor_alerts_empty(auth_client, mock_db):
    mock_result = MockResult(scalars_list=[])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/agents/monitor/alerts")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
@patch("app.agents.interview_agent.service.InterviewAgent.run", new_callable=AsyncMock)
async def test_interview_prep_success(mock_run, auth_client, mock_db):
    from app.agents.schemas import AgentResult, AgentStatus

    mock_run.return_value = AgentResult(
        agent_type="interview",
        status=AgentStatus.COMPLETED,
        output={
            "questions": ["Tell me about yourself"],
            "tips": ["Be specific"],
        },
    )

    response = await auth_client.post(
        "/api/v1/agents/interview-prep",
        json={"company": "Google", "role": "ML Engineer", "type": "behavioral"},
    )
    assert response.status_code == 200
    assert "questions" in response.json()


@pytest.mark.asyncio
@patch("app.agents.research_agent.conduct_research", new_callable=AsyncMock)
async def test_research_success(mock_research, auth_client, mock_db):
    mock_research.return_value = {
        "name": "Anthropic",
        "summary": "AI safety company",
    }

    response = await auth_client.post(
        "/api/v1/agents/research",
        json={"company": "Anthropic"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Anthropic"


@pytest.mark.asyncio
@patch("app.agents.resume_agent.service.ResumeAgent.run", new_callable=AsyncMock)
async def test_cover_letter_success(mock_run, auth_client, mock_db):
    from app.agents.schemas import AgentResult, AgentStatus

    mock_run.return_value = AgentResult(
        agent_type="resume",
        status=AgentStatus.COMPLETED,
        output={"cover_letter": "Dear Hiring Manager..."},
    )

    response = await auth_client.post(
        "/api/v1/agents/cover-letter",
        json={"company": "OpenAI", "role": "Research Engineer"},
    )
    assert response.status_code == 200
    assert "cover_letter" in response.json()


@pytest.mark.asyncio
@patch("app.agents.resume_agent.service.ResumeAgent.run", new_callable=AsyncMock)
async def test_resume_tailor_success(mock_run, auth_client, mock_db):
    from app.agents.schemas import AgentResult, AgentStatus

    mock_run.return_value = AgentResult(
        agent_type="resume",
        status=AgentStatus.COMPLETED,
        output={"resume": "Tailored resume content"},
    )

    response = await auth_client.post(
        "/api/v1/agents/resume-tailor",
        json={
            "role_type": "internship",
            "target_company": "Meta",
            "skills": ["Python", "React"],
        },
    )
    assert response.status_code == 200
    assert "resume" in response.json()


@pytest.mark.asyncio
@patch("app.agents.orchestrator.service.run_planner_agent", new_callable=AsyncMock)
async def test_retry_task_planner_success(mock_run, auth_client, mock_db):
    task = make_agent_task(
        agent_type=AgentType.planner, status=TaskStatus.failed, input={"goal": "Find ML internships"}
    )
    setup_mock_execute(mock_db, [MockResult(scalar_value=task)])

    response = await auth_client.post(f"/api/v1/agents/tasks/{task.id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_run.assert_called_once_with(str(TEST_USER_ID), "Find ML internships")


@pytest.mark.asyncio
async def test_cancel_task_success(auth_client, mock_db):
    task = make_agent_task(agent_type=AgentType.planner, status=TaskStatus.running)
    setup_mock_execute(mock_db, [MockResult(scalar_value=task)])

    response = await auth_client.post(f"/api/v1/agents/tasks/{task.id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert task.status == TaskStatus.failed
    assert task.error == "Cancelled by user"


@pytest.mark.asyncio
async def test_cancel_task_not_running(auth_client, mock_db):
    task = make_agent_task(agent_type=AgentType.planner, status=TaskStatus.completed)
    setup_mock_execute(mock_db, [MockResult(scalar_value=task)])

    response = await auth_client.post(f"/api/v1/agents/tasks/{task.id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_clear_tasks_success(auth_client, mock_db):
    response = await auth_client.delete("/api/v1/agents/tasks/clear")
    assert response.status_code == 204
