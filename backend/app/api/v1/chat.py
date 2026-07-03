import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_factory
from app.dependencies import get_optional_user
from app.models.user import User
from app.agents.planner import decompose_goal_with_llm
from app.agents.orchestrator.service import OrchestratorAgent
from app.services.profile_service import ProfileService
from app.services.memory_service import MemoryService

logger = logging.getLogger("agentforge.api.chat")
router = APIRouter()


def _sse_text(text: str) -> str:
    return f"0: {json.dumps(text)}\n"


def _sse_data(data: dict) -> str:
    return f"d: {json.dumps(data)}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


@router.post("/stream")
async def chat_stream(
    body: dict,
    user: User = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    messages = body.get("messages", [])
    if not messages:
        return StreamingResponse(
            iter([_sse_text("No message provided."), _sse_done()]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache", "Connection": "keep-alive",
            },
        )

    last_user_msg = messages[-1]
    goal = last_user_msg.get("content", "") if last_user_msg.get("role") == "user" else ""

    if not goal:
        return StreamingResponse(
            iter([_sse_text("Please enter a goal to get started."), _sse_done()]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache", "Connection": "keep-alive",
            },
        )

    user_id = str(user.id) if user else "anonymous"

    async def event_generator():
        try:
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

            yield _sse_text("## Analyzing your goal\n\n")
            yield _sse_text(f"**Goal:** {goal}\n\n")
            yield _sse_data({"type": "phase", "phase": "planning", "message": "Planning tasks..."})

            subtasks = await decompose_goal_with_llm(goal, profile_dict, memory_context)
            if not subtasks:
                yield _sse_text(
                    "I couldn't identify specific tasks from that goal. Try something like:\n\n"
                    "- *\"Find AI internships in Ahmedabad\"*\n"
                    "- *\"Prepare my resume for Stripe\"*\n"
                    "- *\"Research Anthropic interviews\"*\n"
                )
                yield _sse_done()
                return

            yield _sse_text(f"**Plan:** {len(subtasks)} task{'s' if len(subtasks) != 1 else ''} identified\n\n")
            for i, t in enumerate(subtasks, 1):
                yield _sse_text(f"{i}. **{t['agent'].title()} Agent** → {t['action']}\n")

            yield _sse_text("\n---\n\n")
            yield _sse_data({"type": "phase", "phase": "executing", "message": "Executing tasks..."})

            results = {}
            async with async_session_factory() as session:
                orchestrator = OrchestratorAgent(session, user_id)
                result = await orchestrator.run({"goal": goal})

            if result.output:
                flat = result.output.get("results", {})
                for agent_key, agent_res in flat.items():
                    results[agent_key] = agent_res
                    msg = agent_res.get("message", "Done.")
                    yield _sse_text(f"**{agent_key.title()}:** {msg}\n\n")
                    yield _sse_data({
                        "type": "task_complete",
                        "agent": agent_key,
                        "result_summary": msg,
                    })
                detail = result.output.get("detail", {})
                for agent_key, agent_detail in detail.items():
                    if isinstance(agent_detail, dict):
                        if agent_detail.get("items"):
                            items = agent_detail["items"]
                            yield _sse_text(f"**Found {len(items)} result{'s' if len(items) != 1 else ''}**\n\n")
                            for item in items[:5]:
                                title = item.get("title", "Untitled")
                                company = item.get("company", "")
                                yield _sse_text(f"- **{title}** @ {company}\n")
                        if agent_detail.get("questions"):
                            qs = agent_detail["questions"]
                            yield _sse_text(f"\n**Generated {len(qs)} practice questions**\n\n")
                        if agent_detail.get("cover_letter"):
                            cl = agent_detail["cover_letter"]
                            yield _sse_text(f"\n**Cover letter generated**\n\n> {cl[:200]}...\n\n")
                            yield _sse_data({
                                "type": "long_output", "agent": agent_key,
                                "key": "cover_letter", "preview": cl[:200],
                            })
                        if agent_detail.get("summary"):
                            yield _sse_text(f"\n{agent_detail['summary']}\n\n")

            # Stream reflection/quality scores
            reflection_scores = result.output.get("reflection_scores", {})
            if reflection_scores:
                yield _sse_text("\n---\n")
                yield _sse_text("### 📊 Quality Assessment\n\n")
                yield _sse_data({"type": "phase", "phase": "quality", "message": "Evaluating output quality..."})
                max_score = 50
                for agent_key, scores in reflection_scores.items():
                    total = scores.get("total", 0)
                    if total == 0:
                        continue
                    bar_filled = round(total / max_score * 10)
                    bar_empty = 10 - bar_filled
                    bar = "🟢" * bar_filled + "⚪" * bar_empty
                    feedback = scores.get("feedback", "")
                    yield _sse_text(
                        f"**{agent_key.title()}** — {bar} `{total}/{max_score}`  _{feedback}_\n\n"
                    )
                    yield _sse_data({
                        "type": "quality_score",
                        "agent": agent_key,
                        "scores": {k: v for k, v in scores.items() if k not in ("total", "feedback")},
                        "total": total,
                        "max": max_score,
                        "feedback": feedback,
                    })

            yield _sse_text("\n---\n\n**All tasks complete!**\n")
            yield _sse_data({
                "type": "plan_complete",
                "results": {k: v.get("message", "Done.") if isinstance(v, dict) else "Done." for k, v in results.items()},
                "reflection_scores": reflection_scores,
            })

        except Exception as e:
            logger.error("Chat stream error: %s", e, exc_info=True)
            yield _sse_text(f"\n\nAn error occurred: {str(e)}\n")
            yield _sse_data({"type": "error", "error": str(e)})

        finally:
            yield _sse_done()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
