import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _parse_sse_events(text: str):
    text_events = []
    data_events = []
    done = False
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("0: "):
            text_events.append(json.loads(line[3:]))
        elif line.startswith("d: "):
            data_events.append(json.loads(line[3:]))
        elif line == "data: [DONE]":
            done = True
    return text_events, data_events, done


@pytest.mark.asyncio
async def test_chat_stream_empty_messages(async_client):
    response = await async_client.post(
        "/api/v1/chat/stream",
        json={"messages": []},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    text_events, _, done = _parse_sse_events(response.text)
    assert any("No message provided" in t for t in text_events)
    assert done


@pytest.mark.asyncio
async def test_chat_stream_no_goal(async_client):
    response = await async_client.post(
        "/api/v1/chat/stream",
        json={"messages": [{"role": "assistant", "content": "hi"}]},
    )
    assert response.status_code == 200

    text_events, _, done = _parse_sse_events(response.text)
    assert any("Please enter a goal" in t for t in text_events)
    assert done


@pytest.mark.asyncio
async def test_chat_stream_no_auth(async_client):
    response = await async_client.post(
        "/api/v1/chat/stream",
        json={"messages": []},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_stream_anonymous_user(async_client):
    response = await async_client.post(
        "/api/v1/chat/stream",
        json={"messages": [{"role": "user", "content": ""}]},
    )
    assert response.status_code == 200
    text_events, _, done = _parse_sse_events(response.text)
    assert any("Please enter a goal" in t for t in text_events)
    assert done


@pytest.mark.asyncio
@patch("app.api.v1.chat.decompose_goal_with_llm", new_callable=AsyncMock)
@patch("app.api.v1.chat.async_session_factory")
async def test_chat_stream_valid_goal(
    mock_session_factory,
    mock_decompose,
    auth_client,
):
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    mock_decompose.return_value = [
        {
            "agent": "job",
            "action": "Search for ML internships",
            "params": {"query": "ML internships"},
        }
    ]

    mock_orch = AsyncMock()
    mock_orch.run = AsyncMock(
        return_value=MagicMock(
            output={
                "results": {
                    "job": {"message": "Found 1 opportunity"},
                },
                "detail": {
                    "job": {
                        "items": [{"title": "ML Intern", "company": "TestCorp", "match_score": 85.0}],
                    },
                },
            }
        )
    )

    with (
        patch("app.api.v1.chat.OrchestratorAgent", return_value=mock_orch),
        patch("app.api.v1.chat.ProfileService") as MockProfile,
        patch("app.api.v1.chat.MemoryService") as MockMemory,
    ):
        profile_inst = AsyncMock()
        profile_inst.get_or_create_profile = AsyncMock(return_value=None)
        profile_inst.get_skill_names = AsyncMock(return_value=[])
        MockProfile.return_value = profile_inst

        memory_inst = AsyncMock()
        memory_inst.get_user_context = AsyncMock(return_value={})
        MockMemory.return_value = memory_inst

        response = await auth_client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Find ML internships"}]},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    text_events, data_events, done = _parse_sse_events(response.text)
    assert done

    full_text = "".join(text_events)
    assert "Analyzing your goal" in full_text
    assert "Find ML internships" in full_text
    assert "Plan:" in full_text
    assert "Job Agent" in full_text
    assert "ML Intern" in full_text

    phases = [d for d in data_events if d.get("type") == "phase"]
    assert len(phases) >= 1
    assert phases[0]["phase"] == "planning"

    task_completes = [d for d in data_events if d.get("type") == "task_complete"]
    assert len(task_completes) == 1

    plan_completes = [d for d in data_events if d.get("type") == "plan_complete"]
    assert len(plan_completes) == 1


@pytest.mark.asyncio
@patch("app.api.v1.chat.decompose_goal_with_llm", new_callable=AsyncMock)
@patch("app.api.v1.chat.async_session_factory")
async def test_chat_stream_no_subtasks(mock_session_factory, mock_decompose, auth_client):
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    mock_decompose.return_value = []

    with patch("app.api.v1.chat.ProfileService") as MockProfile, patch("app.api.v1.chat.MemoryService") as MockMemory:
        profile_inst = AsyncMock()
        profile_inst.get_or_create_profile = AsyncMock(return_value=None)
        profile_inst.get_skill_names = AsyncMock(return_value=[])
        MockProfile.return_value = profile_inst

        memory_inst = AsyncMock()
        memory_inst.get_user_context = AsyncMock(return_value={})
        MockMemory.return_value = memory_inst

        response = await auth_client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "something vague"}]},
        )

    assert response.status_code == 200
    text_events, _, done = _parse_sse_events(response.text)
    assert done
    full_text = "".join(text_events)
    assert "couldn't identify specific tasks" in full_text


@pytest.mark.asyncio
@patch("app.api.v1.chat.decompose_goal_with_llm", new_callable=AsyncMock)
@patch("app.api.v1.chat.async_session_factory")
async def test_chat_stream_agent_error(
    mock_session_factory,
    mock_decompose,
    auth_client,
):
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    mock_decompose.return_value = [
        {"agent": "resume", "action": "Optimize resume", "params": {}},
    ]

    mock_orch = AsyncMock()
    mock_orch.run = AsyncMock(side_effect=RuntimeError("Agent crashed"))

    with (
        patch("app.api.v1.chat.OrchestratorAgent", return_value=mock_orch),
        patch("app.api.v1.chat.ProfileService") as MockProfile,
        patch("app.api.v1.chat.MemoryService") as MockMemory,
    ):
        profile_inst = AsyncMock()
        profile_inst.get_or_create_profile = AsyncMock(return_value=None)
        profile_inst.get_skill_names = AsyncMock(return_value=[])
        MockProfile.return_value = profile_inst

        memory_inst = AsyncMock()
        memory_inst.get_user_context = AsyncMock(return_value={})
        MockMemory.return_value = memory_inst

        response = await auth_client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Fix my resume"}]},
        )

    assert response.status_code == 200
    text_events, data_events, done = _parse_sse_events(response.text)
    assert done

    full_text = "".join(text_events)
    assert "Error" in full_text or "error" in full_text
    assert "Agent crashed" in full_text

    errors = [d for d in data_events if d.get("type") == "error"]
    assert len(errors) == 1
    assert errors[0]["error"] == "Agent crashed"


@pytest.mark.asyncio
async def test_chat_stream_sse_headers(async_client):
    response = await async_client.post(
        "/api/v1/chat/stream",
        json={"messages": []},
    )
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "no-cache" in response.headers["cache-control"]
