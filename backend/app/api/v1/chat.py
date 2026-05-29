"""
Streaming chat endpoint for the Vercel AI SDK Data Stream Protocol.

Implements the SSE-based stream format that @ai-sdk/react's useChat hook expects:
  - 0: "text delta"  → appended to the assistant message
  - d: {"json": …}   → extra data available via the `data` state in useChat
  - [DONE]           → stream termination

The endpoint receives a user goal, decomposes it via the planner, dispatches
tasks to specialist agents, and streams everything back in real-time.
"""

import json
import logging
import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_factory
from app.dependencies import get_current_user, get_optional_user
from app.models.user import User, AgentType
from app.agents.planner import decompose_goal_with_llm, format_planner_response
from app.agents.graph import dispatch_agent
from app.services.profile_service import ProfileService
from app.services.memory_service import MemoryService

logger = logging.getLogger("agentforge.api.chat")
router = APIRouter()


def _sse_text(text: str) -> str:
    """Format a text-delta SSE event."""
    return f"0: {json.dumps(text)}\n"


def _sse_data(data: dict) -> str:
    """Format a data SSE event."""
    return f"d: {json.dumps(data)}\n\n"


def _sse_done() -> str:
    """Format the stream termination event."""
    return "data: [DONE]\n\n"


@router.post("/stream")
async def chat_stream(
    body: dict,
    user: User = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streaming chat endpoint compatible with @ai-sdk/react useChat.

    Accepts:  {"messages": [{"role": "user", "content": "..."}]}
    Returns:  SSE stream of text deltas and data events.
    """
    # Extract the latest user message
    messages = body.get("messages", [])
    if not messages:
        return StreamingResponse(
            iter([_sse_text("No message provided."), _sse_done()]),
            media_type="text/event-stream",
            headers={
                "x-vercel-ai-data-stream": "v1",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    last_user_msg = messages[-1]
    goal = last_user_msg.get("content", "") if last_user_msg.get("role") == "user" else ""

    if not goal:
        return StreamingResponse(
            iter([_sse_text("Please enter a goal to get started."), _sse_done()]),
            media_type="text/event-stream",
            headers={
                "x-vercel-ai-data-stream": "v1",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    user_id = str(user.id) if user else "anonymous"

    async def event_generator():
        try:
            # Get profile and memory context
            async with async_session_factory() as session:
                profile_service = ProfileService(session)
                memory_service = MemoryService(session)

                profile = None
                profile_skills = []
                memory_context = {}
                if user:
                    profile = await profile_service.get_or_create_profile(user_id)
                    profile_skills = await profile_service.get_skill_names(profile.id)
                    memory_context = await memory_service.get_user_context(user_id)

                profile_dict = {
                    "id": str(profile.id) if profile else "unknown",
                    "skills": profile_skills,
                    "target_locations": profile.target_locations if profile and profile.target_locations else [],
                    "role_types": profile.role_types if profile and profile.role_types else [],
                    "career_goal": profile.career_goal if profile and profile.career_goal else "",
                }

            # ── Step 1: Decompose goal ──
            yield _sse_text(f"## 🔍 Analyzing your goal\n\n")
            yield _sse_text(f"**Goal:** {goal}\n\n")
            yield _sse_data({"type": "phase", "phase": "planning", "message": "Decomposing goal into tasks..."})

            subtasks = await decompose_goal_with_llm(goal, profile_dict, memory_context)

            if not subtasks:
                # No tasks detected — offer general guidance
                yield _sse_text(
                    "I couldn't identify specific tasks from that goal. Try something like:\n\n"
                    "- *\"Find AI internships in Ahmedabad\"*\n"
                    "- *\"Prepare my resume for Stripe\"*\n"
                    "- *\"Research Anthropic interviews\"*\n"
                )
                yield _sse_done()
                return

            # Show the plan
            yield _sse_text(f"**Plan:** {len(subtasks)} task{'s' if len(subtasks) != 1 else ''} identified\n\n")
            for i, t in enumerate(subtasks, 1):
                yield _sse_text(f"{i}. **{t['agent'].title()} Agent** → {t['action']}\n")

            # ── Step 2: Dispatch tasks sequentially ──
            yield _sse_text(f"\n---\n\n")
            results = {}

            for t in subtasks:
                agent_name = t["agent"].title()
                yield _sse_data({
                    "type": "task_start",
                    "agent": t["agent"],
                    "message": f"Running {agent_name} Agent...",
                })
                yield _sse_text(f"## 🤖 {agent_name} Agent\n\n")
                yield _sse_text(f"*{t['action']}...*\n\n")

                try:
                    async with async_session_factory() as session:
                        agent_type = AgentType(t["agent"])
                        result = await dispatch_agent(agent_type, user_id, t["params"], session)

                    results[t["agent"]] = result

                    # Format result based on agent type
                    if isinstance(result, dict):
                        if result.get("items"):
                            items = result["items"]
                            yield _sse_text(f"**Found {len(items)} result{'s' if len(items) != 1 else ''}**\n\n")
                            for item in items[:5]:
                                title = item.get("title", "Untitled")
                                company = item.get("company", "")
                                score = item.get("match_score", "")
                                score_str = f" — Match: {score:.0f}%" if isinstance(score, (int, float)) and score else ""
                                yield _sse_text(f"- **{title}** @ {company}{score_str}\n")
                            if len(items) > 5:
                                yield _sse_text(f"  *...and {len(items) - 5} more*\n")

                        if result.get("suggestions"):
                            yield _sse_text(f"\n**Suggestions:**\n\n")
                            for s in result["suggestions"][:4]:
                                yield _sse_text(f"- {s}\n")

                        if result.get("questions"):
                            qs = result["questions"]
                            yield _sse_text(f"\n**Generated {len(qs)} practice questions**\n\n")

                        if result.get("cover_letter"):
                            cl = result["cover_letter"]
                            snippet = cl[:200] + "..."
                            yield _sse_text(f"\n**Cover letter generated**\n\n> {snippet}\n\n")
                            yield _sse_data({
                                "type": "long_output",
                                "agent": t["agent"],
                                "key": "cover_letter",
                                "preview": snippet,
                            })

                        if result.get("summary"):
                            yield _sse_text(f"\n{result['summary']}\n\n")

                    yield _sse_data({
                        "type": "task_complete",
                        "agent": t["agent"],
                        "result_summary": result.get("message", "Task completed.") if isinstance(result, dict) else "Done.",
                    })

                except Exception as e:
                    logger.warning("Agent %s failed: %s", t["agent"], e)
                    yield _sse_text(f"⚠️ **Error:** {str(e)}\n\n")
                    yield _sse_data({
                        "type": "task_error",
                        "agent": t["agent"],
                        "error": str(e),
                    })
                    results[t["agent"]] = {"error": str(e)}

            # ── Step 3: Final summary ──
            yield _sse_text(f"\n---\n\n")
            summary = format_planner_response(goal, results)
            for line in summary.split("\n"):
                yield _sse_text(line + "\n")
            yield _sse_text(f"\n\n**All tasks complete!** 🎉\n")

            yield _sse_data({
                "type": "plan_complete",
                "results": {k: v.get("message", "Done.") if isinstance(v, dict) else "Done." for k, v in results.items()},
            })

        except Exception as e:
            logger.error("Chat stream error: %s", e, exc_info=True)
            yield _sse_text(f"\n\n❌ An error occurred: {str(e)}\n")
            yield _sse_data({"type": "error", "error": str(e)})

        finally:
            yield _sse_done()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-data-stream": "v1",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
