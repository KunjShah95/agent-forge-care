"""
Personal Assistant Agent — the user-facing companion that handles:
- Resume tailoring and optimization
- Interview preparation and mock questions
- Networking outreach generation
- Opportunity monitoring and alerts
- General career guidance

Integrates with all memory layers and specialist outputs.
"""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import (
    Opportunity,
    MatchScore,
    AgentType,
    AlertConfig,
)
from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService
from app.services.match_service import MatchService
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding

logger = logging.getLogger("agentforge.agents.assistant")


def _get_llm(temperature: float = 0.7):
    if not settings.openai_api_key:
        return None
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=temperature,
            api_key=settings.openai_api_key,
        )
    except ImportError:
        logger.warning("langchain_openai not available")
        return None


def _strip_json_fences(content) -> str:
    content = str(content).strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    if content.startswith("json"):
        content = content[4:].strip()
    return content


# ─── Resume Actions ─────────────────────────────────────────


async def tailor_resume(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """
    Tailor the user's resume for a target role or specific application.
    Uses memory to understand the user's experience and skills.
    """
    role_type = params.get("role_type", "internship")
    target_company = params.get("target_company")
    skills = params.get("skills", [])
    application_id = params.get("application_id")

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    llm = _get_llm(temperature=0.7)
    suggestions = None
    action_items = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            prompt = f"""You are a career advisor AI that helps users tailor their resumes.

USER CONTEXT:
- Skills: {", ".join(all_skills) or "not specified"}
- Target role type: {role_type}
- Target company: {target_company or "not specified"}

Generate resume tailoring suggestions as a JSON object with these keys:
- "suggestions": array of 7 specific, actionable resume suggestions (strings)
- "action_items": array of 3 concrete next steps (strings)

Make suggestions specific to the user's skills and target role. Reference their actual skills by name.
Return ONLY valid JSON. No markdown, no explanations."""

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(_strip_json_fences(response.content))

            if (
                isinstance(parsed, dict)
                and "suggestions" in parsed
                and isinstance(parsed["suggestions"], list)
            ):
                suggestions = parsed["suggestions"][:7]
            if (
                isinstance(parsed, dict)
                and "action_items" in parsed
                and isinstance(parsed["action_items"], list)
            ):
                action_items = parsed["action_items"][:3]
        except Exception as e:
            logger.warning("LLM tailor_resume failed, falling back to template: %s", e)

    if suggestions is None:
        suggestions = [
            f"Lead with your strongest {'skills' if role_type == 'internship' else 'experience'}: {', '.join(all_skills[:3])}",
        ]
        if target_company:
            suggestions.append(
                f"Research {target_company}'s products and mention relevant experience"
            )
            suggestions.append(
                "Use keywords from the job description throughout your resume"
            )
        suggestions.extend(
            [
                f"Include metrics and impact for each {role_type} experience",
                "Optimize for ATS by matching keywords from the job posting",
                "Keep format clean and consistent — one page maximum",
                f"Highlight projects relevant to {', '.join(all_skills[:2])}",
                "Add a technical skills section at the top or bottom",
            ]
        )

    if action_items is None:
        action_items = [
            "Update your portfolio/linkedin to match",
            f"Prepare 2-3 stories highlighting {', '.join(all_skills[:2])} skills",
            "Save this version for the current application",
        ]

    # Store tailoring preferences in memory
    await memory_service.set_memory(
        user_id,
        "resume_tailoring",
        {
            "role_type": role_type,
            "skills": all_skills,
            "target_company": target_company,
            "last_tailored": datetime.now(timezone.utc).isoformat(),
        },
        weight=0.9,
    )

    return {
        "suggestions": suggestions[:7],
        "ats_keywords": all_skills[:5],
        "role_type": role_type,
        "message": f"Resume tailored for {role_type} roles. {len(suggestions)} suggestions generated.",
        "action_items": action_items,
    }


async def generate_cover_letter(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Generate a personalized cover letter template."""
    company = params.get("company", "[Company]")
    role = params.get("role", "[Role]")
    skills = params.get("skills", [])

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)
    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    llm = _get_llm(temperature=0.7)
    cover_letter = None
    customization_tips = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            prompt = f"""You are a professional cover letter writer.

USER CONTEXT:
- School/Background: {profile.school or "not specified"}
- Skills: {", ".join(all_skills) or "not specified"}
- Target company: {company}
- Target role: {role}

Generate a compelling, professional cover letter and customization tips as a JSON object:
- "cover_letter": a full cover letter string (3-4 paragraphs, with greeting and sign-off using [Your Name])
- "customization_tips": array of 3 specific tips for personalizing this letter

The letter should reference the user's actual skills by name, show enthusiasm for the company, and be specific to the role.
Return ONLY valid JSON. No markdown, no explanations."""

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(_strip_json_fences(response.content))

            if (
                isinstance(parsed, dict)
                and "cover_letter" in parsed
                and isinstance(parsed["cover_letter"], str)
            ):
                cover_letter = parsed["cover_letter"]
            if (
                isinstance(parsed, dict)
                and "customization_tips" in parsed
                and isinstance(parsed["customization_tips"], list)
            ):
                customization_tips = parsed["customization_tips"][:3]
        except Exception as e:
            logger.warning(
                "LLM generate_cover_letter failed, falling back to template: %s", e
            )

    if cover_letter is None:
        cover_letter = (
            f"Dear [Hiring Manager],\n\n"
            f"I am writing to express my strong interest in the {role} position at {company}. "
            f"As a passionate {'engineer' if profile.school else 'professional'} "
            f"{'from ' + profile.school if profile.school else ''} "
            f"with expertise in {', '.join(all_skills[:3])}, "
            f"I am excited about the opportunity to contribute to your team.\n\n"
            f"My experience includes:\n"
        )
        for skill in all_skills[:4]:
            cover_letter += f"- Building projects and solving problems using {skill}\n"
        cover_letter += (
            f"\nI am particularly drawn to {company}'s mission and would love to bring my "
            f"skills in {', '.join(all_skills[:2])} to help achieve your goals. "
            f"I look forward to the possibility of discussing how I can contribute.\n\n"
            f"Best regards,\n[Your Name]"
        )

    if customization_tips is None:
        customization_tips = [
            "Add specific projects relevant to the role",
            "Mention any mutual connections or referrals",
            "Reference a recent company achievement or product launch",
        ]

    return {
        "cover_letter": cover_letter,
        "message": f"Cover letter template generated for {role} at {company}",
        "customization_tips": customization_tips,
    }


# ─── Interview Actions ──────────────────────────────────────


async def prepare_interview(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """
    Generate interview preparation materials based on user's profile
    and the target role/company.
    """
    role_type = params.get("role_type", "internship")
    skills = params.get("skills", [])
    company = params.get("company")

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    llm = _get_llm(temperature=0.7)
    questions = None
    prep_tips = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            prompt = f"""You are an interview preparation expert.

USER CONTEXT:
- Skills: {", ".join(all_skills) or "not specified"}
- Target role type: {role_type}
- Target company: {company or "not specified"}

Generate interview preparation materials as a JSON object:
- "questions": array of objects, each with keys "skill" (string), "question" (string), "type" ("behavioral" or "technical"), "tips" (string). Generate 2 questions per skill (one behavioral, one technical) for up to 5 skills, plus 3 general behavioral questions with skill set to "general".
- "prep_tips": array of 5 specific preparation tips referencing the user's actual skills and target company

Make questions realistic and tailored to the user's skills and target role.
Return ONLY valid JSON. No markdown, no explanations."""

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(_strip_json_fences(response.content))

            if (
                isinstance(parsed, dict)
                and "questions" in parsed
                and isinstance(parsed["questions"], list)
            ):
                questions = parsed["questions"]
            if (
                isinstance(parsed, dict)
                and "prep_tips" in parsed
                and isinstance(parsed["prep_tips"], list)
            ):
                prep_tips = parsed["prep_tips"][:5]
        except Exception as e:
            logger.warning(
                "LLM prepare_interview failed, falling back to template: %s", e
            )

    if questions is None:
        questions = []
        for skill in all_skills[:5]:
            questions.append(
                {
                    "skill": skill,
                    "question": f"Describe your experience with {skill} and a project where you used it effectively.",
                    "type": "behavioral",
                    "tips": f"Use STAR format. Highlight a specific project where {skill} was critical.",
                }
            )
            questions.append(
                {
                    "skill": skill,
                    "question": f"What are the trade-offs and challenges when working with {skill} at scale?",
                    "type": "technical",
                    "tips": "Discuss performance, maintainability, and real-world constraints.",
                }
            )
        questions.extend(
            [
                {
                    "skill": "general",
                    "question": "Tell me about yourself and your background.",
                    "type": "behavioral",
                    "tips": "Structure it: present → past → future. Keep it under 2 minutes.",
                },
                {
                    "skill": "general",
                    "question": "Why are you interested in this role/company?",
                    "type": "behavioral",
                    "tips": "Show you've done your research. Mention specific products or initiatives.",
                },
                {
                    "skill": "general",
                    "question": "Describe a time you resolved a conflict or disagreement in a team.",
                    "type": "behavioral",
                    "tips": "Focus on communication and compromise. Show growth.",
                },
            ]
        )

    if prep_tips is None:
        prep_tips = [
            f"Practice {len(all_skills[:3])} technical deep-dives on {', '.join(all_skills[:3])}",
            "Prepare 3 STAR stories highlighting leadership and impact",
            f"Research {company or 'the company'} recent news and product launches",
            "Prepare 3-4 thoughtful questions to ask the interviewer",
            "Do a mock interview with a friend or use the Interview Copilot",
        ]

    # Store interview prep in memory
    await memory_service.set_memory(
        user_id,
        "interview_prep",
        {
            "role_type": role_type,
            "skills": all_skills,
            "company": company,
            "prepared_at": datetime.now(timezone.utc).isoformat(),
        },
        weight=0.8,
    )

    return {
        "questions": questions,
        "total_questions": len(questions),
        "prep_tips": prep_tips,
        "focus_areas": all_skills[:3]
        + ["System Design Fundamentals", "Behavioral Storytelling"],
        "message": f"Generated {len(questions)} interview questions for preparation",
    }


# ─── Networking Actions ─────────────────────────────────────


async def generate_outreach(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """
    Generate outreach messages for networking with recruiters,
    hiring managers, and engineers at target companies.
    """
    target_companies = params.get("target_companies", [])
    role = params.get("role", "")
    skills = params.get("skills", [])

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)
    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    llm = _get_llm(temperature=0.7)
    templates = None
    best_practices = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            companies_str = (
                ", ".join(target_companies) if target_companies else "target companies"
            )

            prompt = f"""You are a networking and outreach specialist.

USER CONTEXT:
- Skills: {", ".join(all_skills) or "not specified"}
- Target role: {role or "not specified"}
- Target companies: {companies_str}

Generate outreach templates as a JSON object:
- "templates": array of objects, each with keys "type" ("cold_email" or "linkedin_message"), "subject" (string, empty for linkedin), "message" (string). Generate one cold_email and one linkedin_message per target company.
- "best_practices": array of 5 networking best practices (strings)

Messages should reference the user's actual skills, be concise, professional, and include a clear low-friction call to action.
Return ONLY valid JSON. No markdown, no explanations."""

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(_strip_json_fences(response.content))

            if (
                isinstance(parsed, dict)
                and "templates" in parsed
                and isinstance(parsed["templates"], list)
            ):
                templates = parsed["templates"]
            if (
                isinstance(parsed, dict)
                and "best_practices" in parsed
                and isinstance(parsed["best_practices"], list)
            ):
                best_practices = parsed["best_practices"][:5]
        except Exception as e:
            logger.warning(
                "LLM generate_outreach failed, falling back to template: %s", e
            )

    if templates is None:
        templates = []
        for company in target_companies or ["target companies"]:
            templates.append(
                {
                    "type": "cold_email",
                    "subject": f"Interested in {role} opportunities at {company}",
                    "message": (
                        f"Hi [Name],\n\n"
                        f"I'm reaching out because I'm very interested in {company} "
                        f"and would love to learn more about your work. "
                        f"I have experience in {', '.join(all_skills[:3])} "
                        f"and I'm exploring {role} opportunities.\n\n"
                        f"Would you be open to a 15-minute chat?\n\n"
                        f"Best,\n[Your Name]"
                    ),
                }
            )
            templates.append(
                {
                    "type": "linkedin_message",
                    "subject": "",
                    "message": (
                        f"Hi [Name]! I'm exploring {role} opportunities at {company} "
                        f"and was impressed by your background in "
                        f"{', '.join(all_skills[:2])}. "
                        f"Would love to connect and learn more about your journey!"
                    ),
                }
            )

    if best_practices is None:
        best_practices = [
            "Personalize each message with specific details about the recipient",
            "Keep the first message under 150 words",
            "Include a clear, low-friction ask (e.g., 15-min chat)",
            "Follow up after 5-7 days if you don't hear back",
            "Connect on LinkedIn before sending a message",
        ]

    # Store networking activity in memory
    await memory_service.set_memory(
        user_id,
        "last_networking",
        {
            "target_companies": target_companies,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        weight=0.7,
    )

    return {
        "templates": templates,
        "message": f"Generated {len(templates)} outreach templates",
        "best_practices": best_practices,
    }


# ─── Monitoring Actions ─────────────────────────────────────


async def run_daily_scan(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """
    Run the daily opportunity monitor scan.
    Checks for new opportunities, updates match scores, and generates alerts.
    """
    memory_service = MemoryService(db)
    match_service = MatchService(db)

    # Get user's alert preferences
    result = await db.execute(
        select(AlertConfig).where(
            AlertConfig.user_id == user_id,
            AlertConfig.is_active == True,
        )
    )
    alert_configs = result.scalars().all()

    keywords = []
    for config in alert_configs:
        keywords.extend(config.keywords or [])

    # If no alert configs, use profile-based defaults
    if not keywords:
        profile_service = ProfileService(db)
        profile = await profile_service.get_or_create_profile(user_id)
        keywords = profile.role_types or ["internship", "job"]
        locations = profile.target_locations or []

    # Quick scan across multiple types
    from app.search.adapters import SearchAdapter

    search_adapter = SearchAdapter()
    all_new_items = []

    for keyword in keywords[:3]:
        try:
            results = await search_adapter.search(query=keyword, limit=5)
            all_new_items.extend(results)
        except Exception as e:
            logger.debug("Monitor scan error for %s: %s", keyword, e)

    # Fallback to demo data
    if not all_new_items:
        from app.utils.demo_data import generate_demo_opportunities

        all_new_items = generate_demo_opportunities(AgentType.monitor, "", "")

    # Deduplicate and store
    seen_titles = set()
    stored_items = []
    for item in all_new_items[:20]:
        title = item.get("title", "")
        if title in seen_titles:
            continue
        seen_titles.add(title)

        opp = Opportunity(
            user_id=user_id,
            title=title,
            company=item.get("company", "Tech Company"),
            location=item.get("location"),
            remote=item.get("remote", False),
            type=item.get("type", "Internship"),
            description=item.get("description"),
            apply_url=item.get("apply_url"),
            skills_required=item.get("skills", []),
            source="daily_scan",
        )
        db.add(opp)
        await db.flush()
        stored_items.append(
            {
                "id": str(opp.id),
                "title": opp.title,
                "company": opp.company,
                "type": opp.type,
            }
        )

    # Score all new matches
    scored_count = await match_service.score_all_active(user_id)

    # Generate alerts for high-scoring matches
    alerts = []
    high_score_result = await db.execute(
        select(Opportunity, MatchScore)
        .join(MatchScore, Opportunity.id == MatchScore.opportunity_id)
        .where(
            Opportunity.user_id == user_id,
            MatchScore.overall_score >= 80,
            Opportunity.source == "daily_scan",
        )
    )

    for opp, ms in high_score_result.all():
        alerts.append(
            {
                "opportunity_id": str(opp.id),
                "title": opp.title,
                "company": opp.company,
                "match_score": float(ms.overall_score),
                "message": f"High match: {opp.title} @ {opp.company} ({float(ms.overall_score):.0f}%)",
            }
        )

    # Update memory with scan timestamp
    await memory_service.set_memory(
        user_id,
        "last_daily_scan",
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "new_items": len(stored_items),
            "scored": scored_count,
            "alerts": len(alerts),
        },
        weight=0.6,
    )

    return {
        "items": stored_items,
        "total": len(stored_items),
        "scored": scored_count,
        "alerts": alerts[:10],
        "message": f"Scan completed: {len(stored_items)} new items, {scored_count} scored, {len(alerts)} high-match alerts",
    }


# ─── Career Guidance ────────────────────────────────────────


async def get_career_guidance(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """
    Provide personalized career guidance based on the user's
    profile, skills, memory, and current market conditions.
    """
    query = params.get("query", "")
    context = params.get("context", {})

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)
    agent_memory = AgentMemory(user_id)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    memory_context = await memory_service.get_user_context(user_id)

    # Generate guidance based on query and profile
    guidance = {
        "profile_summary": {
            "name": profile.school or "Student",
            "skills": profile_skills,
            "target_locations": profile.target_locations or ["Remote"],
            "career_goal": profile.career_goal or "Not yet defined",
        },
        "next_steps": [
            f"Apply to {len(profile_skills)} matching opportunities",
            "Update your resume with latest projects",
            "Set up daily monitor alerts for new openings",
            "Connect with 5 recruiters on LinkedIn this week",
        ],
        "tips": [
            "Tailor each application — generic applications have lower conversion",
            "Build a portfolio project showcasing your strongest skills",
            "Join relevant communities (Discord, Slack, meetups) in your target domain",
        ],
    }

    # Use semantic memory for personalized guidance
    if profile_skills:
        query_vector = await get_text_embedding(
            f"career guidance for skills: {', '.join(profile_skills)}"
        )
        relevant_context = agent_memory.get_relevant_context(query_vector, limit=3)
        guidance["memory_context"] = relevant_context

    return {
        "guidance": guidance,
        "message": "Career guidance generated based on your profile and market conditions",
    }
