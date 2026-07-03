"""Resume Agent handlers — resume tailoring and cover letter generation."""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService
from app.services.model_manager import get_completion_llm
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding
from app.agents.enrichment import build_enrichment_context
from app.hiring_agent.assistant_integration import enrich_with_hiring_agent
from app.agents.base import strip_json_fences
from app.agents.constants import (
    LLM_TEMPERATURE_CREATIVE,
    LLM_PREFERRED_PROVIDER,
    MEMORY_WEIGHT_HIGH,
    MEMORY_KEY_RESUME,
    COLLECTION_RESUME,
    MAX_RESUME_SUGGESTIONS,
    MAX_RESUME_ACTION_ITEMS,
    MAX_RESUME_ATS_KEYWORDS,
    MAX_RESUME_PROJECTS,
    DEFAULT_ROLE_TYPE,
    DEFAULT_COMPANY,
    DEFAULT_ROLE,
)
from app.agents.prompts.resume import tailor_resume_prompt, cover_letter_prompt

logger = logging.getLogger("agentforge.agents.resume.handlers")


async def tailor_resume(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Tailor the user's resume for a target role or specific application."""
    role_type = params.get("role_type", DEFAULT_ROLE_TYPE)
    target_company = params.get("target_company")
    skills = params.get("skills", [])

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    ctx = await build_enrichment_context(db, user_id, all_skills, include_raw_repos=True)

    ha_result = await enrich_with_hiring_agent(
        user_id=user_id, db=db, resume_text=None,
        target_role=role_type, target_company=target_company,
        job_description=None,
    )

    llm = get_completion_llm(temperature=LLM_TEMPERATURE_CREATIVE, preferred_provider=LLM_PREFERRED_PROVIDER)
    suggestions = None
    action_items = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            ha_block = _build_ha_block(ha_result)

            prompt = tailor_resume_prompt(all_skills, role_type, target_company, ctx.github_context, ctx.portfolio_context, ha_block)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(strip_json_fences(response.content))

            if isinstance(parsed, dict) and "suggestions" in parsed and isinstance(parsed["suggestions"], list):
                suggestions = parsed["suggestions"][:MAX_RESUME_SUGGESTIONS]
            if isinstance(parsed, dict) and "action_items" in parsed and isinstance(parsed["action_items"], list):
                action_items = parsed["action_items"][:MAX_RESUME_ACTION_ITEMS]
        except Exception as e:
            logger.warning("LLM tailor_resume failed, falling back to template: %s", e)

    if suggestions is None:
        suggestions = _fallback_resume_suggestions(all_skills, role_type, target_company, ha_result)

    if action_items is None:
        action_items = _fallback_resume_action_items(all_skills, ha_result)

    try:
        await memory_service.set_memory(user_id, MEMORY_KEY_RESUME, {
            "role_type": role_type, "skills": all_skills,
            "target_company": target_company,
            "last_tailored": datetime.now(timezone.utc).isoformat(),
        }, weight=MEMORY_WEIGHT_HIGH)
    except Exception as e:
        logger.debug("Failed to store resume tailoring memory: %s", e)

    result = {
        "suggestions": suggestions[:MAX_RESUME_SUGGESTIONS],
        "ats_keywords": all_skills[:MAX_RESUME_ATS_KEYWORDS],
        "role_type": role_type,
        "message": f"Resume tailored for {role_type} roles. {len(suggestions)} suggestions generated.",
        "action_items": action_items,
    }

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(collection=COLLECTION_RESUME, text=result["message"], vector=vector, metadata={
            "agent_type": "resume", "key": params.get("role_type", ""),
            "timestamp": str(datetime.now(timezone.utc)),
        })
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result


async def generate_cover_letter(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Generate a personalized cover letter template."""
    company = params.get("company", DEFAULT_COMPANY)
    role = params.get("role", DEFAULT_ROLE)
    skills = params.get("skills", [])

    profile_service = ProfileService(db)
    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    ctx = await build_enrichment_context(db, user_id, all_skills)
    ha_result = await enrich_with_hiring_agent(
        user_id=user_id, db=db, resume_text=None,
        target_role=role, target_company=company,
        job_description=params.get("job_description"),
    )

    llm = get_completion_llm(temperature=LLM_TEMPERATURE_CREATIVE, preferred_provider=LLM_PREFERRED_PROVIDER)
    cover_letter = None
    customization_tips = None

    ha_cl = ha_result.get("cover_letter")
    if ha_cl:
        cover_letter = ha_cl
        customization_tips = ["Tailor the first paragraph to the specific role", "Add metrics and concrete project details", "Research the company's recent work and mention it"]

    if llm and not cover_letter:
        try:
            from langchain_core.messages import HumanMessage

            ha_block = _build_ha_block(ha_result, include_jd_match=True)

            prompt = cover_letter_prompt(all_skills, role, company, profile.school, ctx.github_context, ctx.portfolio_context, ha_block)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(strip_json_fences(response.content))

            if isinstance(parsed, dict) and "cover_letter" in parsed and isinstance(parsed["cover_letter"], str):
                cover_letter = parsed["cover_letter"]
            if isinstance(parsed, dict) and "customization_tips" in parsed and isinstance(parsed["customization_tips"], list):
                customization_tips = parsed["customization_tips"][:3]
        except Exception as e:
            logger.warning("LLM generate_cover_letter failed, falling back to template: %s", e)

    if cover_letter is None:
        cover_letter = _fallback_cover_letter(all_skills, role, company, profile.school, ctx)

    if customization_tips is None:
        customization_tips = ["Add specific projects relevant to the role", "Mention any mutual connections or referrals", "Reference a recent company achievement or product launch"]

    return {"cover_letter": cover_letter, "message": f"Cover letter template generated for {role} at {company}", "customization_tips": customization_tips}


# ── Shared Helpers ──────────────────────────────────────────


def _build_ha_block(ha_result: dict, include_jd_match: bool = False) -> str:
    """Build a formatted hiring agent insights block from ha_result."""
    lines = []

    ats = ha_result.get("ats")
    if ats:
        missing_sample = ', '.join(ats.missing_keywords[:8])
        lines.append(
            f"ATS ANALYSIS — keyword coverage: {ats.keyword_coverage_pct}%, "
            f"matched: {ats.matched_count}, missing: {ats.missing_count}\
"
            f"Top missing keywords: {missing_sample}"
        )

    extracted = ha_result.get("resume_extracted")
    if extracted:
        block = "RESUME STRUCTURE:"
        if extracted.skills:
            block += f"\n- Skills: {', '.join(s.name for s in extracted.skills if s.name)}"
        if extracted.work:
            block += f"\n- Experience: {', '.join(f'{w.position} at {w.name}' for w in extracted.work if w.position)}"
        lines.append(block)

    if include_jd_match:
        jd = ha_result.get("jd_match")
        if jd:
            lines.append(
                f"JD MATCH — overall score: {jd.overall_score}/100, "
                f"assessment: {jd.overall_assessment}"
            )

    if lines:
        return f"HIRING AGENT INSIGHTS:\n" + "\n\n".join(lines) + "\n\n"
    return ""


# ── Fallback Templates ──────────────────────────────────────


def _fallback_resume_suggestions(
    all_skills: list[str],
    role_type: str,
    target_company: str | None,
    ha_result: dict,
) -> list[str]:
    """Generate fallback resume suggestions when LLM is unavailable."""
    suggestions = [f"Lead with your strongest {'skills' if role_type == 'internship' else 'experience'}: {', '.join(all_skills[:3])}"]
    if target_company:
        suggestions.append(f"Research {target_company}'s products and mention relevant experience")
        suggestions.append("Use keywords from the job description throughout your resume")
    ha_ats = ha_result.get("ats")
    if ha_ats and ha_ats.missing_keywords:
        suggestions.append(f"Add missing ATS keywords: {', '.join(ha_ats.missing_keywords[:5])}")
    if ha_ats and ha_ats.suggestions:
        for s in ha_ats.suggestions[:2]:
            suggestions.append(s)
    suggestions.extend([
        f"Include metrics and impact for each {role_type} experience",
        "Optimize for ATS by matching keywords from the job posting",
        "Keep format clean and consistent — one page maximum",
        f"Highlight projects relevant to {', '.join(all_skills[:2])}",
        "Add a technical skills section at the top or bottom",
    ])
    return suggestions


def _fallback_resume_action_items(
    all_skills: list[str],
    ha_result: dict,
) -> list[str]:
    """Generate fallback action items when LLM is unavailable."""
    action_items = [
        "Update your portfolio/linkedin to match",
        f"Prepare 2-3 stories highlighting {', '.join(all_skills[:2])} skills",
        "Save this version for the current application",
    ]
    ha_ats = ha_result.get("ats")
    if ha_ats and ha_ats.missing_keywords:
        action_items.append(f"Add missing ATS keywords to your resume: {', '.join(ha_ats.missing_keywords[:4])}")
    return action_items


def _fallback_cover_letter(
    all_skills: list[str],
    role: str,
    company: str,
    school: str | None,
    ctx,
) -> str:
    """Generate fallback cover letter when LLM is unavailable."""
    text = (
        f"Dear [Hiring Manager],\n\n"
        f"I am writing to express my strong interest in the {role} position at {company}. "
        f"As a passionate {'engineer' if school else 'professional'} "
        f"{'from ' + school if school else ''} "
        f"with expertise in {', '.join(all_skills[:3])}, "
        f"I am excited about the opportunity to contribute to your team.\n\n"
        f"My experience includes:\n"
    )
    if ctx.pf_projects:
        for proj in ctx.pf_projects[:MAX_RESUME_PROJECTS]:
            text += f"- Developed {proj}\n"
    else:
        for skill in all_skills[:4]:
            text += f"- Building projects and solving problems using {skill}\n"
    if ctx.pf_experience:
        text += f"\nMy professional background includes {ctx.pf_experience[0]}"
        if len(ctx.pf_experience) > 1:
            text += f" as well as {ctx.pf_experience[1]}."
        text += "\n"
    text += (
        f"\nI am particularly drawn to {company}'s mission and would love to bring my "
        f"skills in {', '.join(all_skills[:2])} to help achieve your goals. "
        f"I look forward to the possibility of discussing how I can contribute.\n\n"
        f"Best regards,\n[Your Name]"
    )
    return text
