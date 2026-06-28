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

from app.models.user import (
    Opportunity,
    MatchScore,
    AgentType,
    AlertConfig,
)
from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService
from app.services.match_service import MatchService
from app.services.model_manager import get_completion_llm
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding
from app.agents.enrichment import build_enrichment_context
from app.hiring_agent.assistant_integration import enrich_with_hiring_agent
from app.utils.location import parse_location
from app.utils.industry import detect_industry

logger = logging.getLogger("agentforge.agents.assistant")


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

    memory_service = MemoryService(db)
    profile_service = ProfileService(db)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    # ── Fetch GitHub + portfolio enrichment from memory ──
    ctx = await build_enrichment_context(db, user_id, all_skills, include_raw_repos=True)

    # ── Fetch hiring agent enrichment (ATS, JD match, cover letter) ──
    ha_result = await enrich_with_hiring_agent(
        user_id=user_id, db=db,
        resume_text=None,
        target_role=role_type,
        target_company=target_company,
        job_description=None,
    )

    llm = get_completion_llm(temperature=0.7, preferred_provider="openai")
    suggestions = None
    action_items = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            github_block = f"GITHUB EVIDENCE (use this to ground suggestions in real projects):\n{ctx.github_context}\n" if ctx.github_context else ""
            portfolio_block = f"PORTFOLIO EVIDENCE (use this to reference real projects and experience):\n{ctx.portfolio_context}\n" if ctx.portfolio_context else ""
            
            ha_block = ""
            if ha_result.get("ats"):
                a = ha_result["ats"]
                ha_block = f"ATS ANALYSIS — keyword coverage: {a.keyword_coverage_pct}%, matched: {a.matched_count}, missing: {a.missing_count}\nTop missing keywords: {', '.join(a.missing_keywords[:8])}\n\n"
            if ha_result.get("resume_extracted"):
                r = ha_result["resume_extracted"]
                ha_block += "RESUME STRUCTURE:\n"
                if r.skills:
                    ha_block += f"- Skills: {', '.join(s.name for s in r.skills if s.name)}\n"
                if r.work:
                    ha_block += f"- Experience: {', '.join(f'{w.position} at {w.name}' for w in r.work if w.position)}\n"
                ha_block += "\n"

            prompt = f"""You are a career advisor AI that helps users tailor their resumes.

USER CONTEXT:
- Skills: {", ".join(all_skills) or "not specified"}
- Target role type: {role_type}
- Target company: {target_company or "not specified"}

{github_block}{portfolio_block}Generate resume tailoring suggestions as a JSON object with these keys:
- "suggestions": array of 7 specific, actionable resume suggestions (strings)
- "action_items": array of 3 concrete next steps (strings)

Make suggestions specific to the user's skills and target role. Reference their actual skills by name.
If GitHub data is available, mention specific projects, languages, and starred repos as evidence of skill proficiency.
If portfolio data is available, mention specific projects, technologies, and experience from the portfolio.
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

        # Inject ATS gap suggestions from hiring agent
        ha_ats = ha_result.get("ats")
        if ha_ats and ha_ats.missing_keywords:
            suggestions.append(
                f"Add missing ATS keywords: {', '.join(ha_ats.missing_keywords[:5])}"
            )
        if ha_ats and ha_ats.suggestions:
            for s in ha_ats.suggestions[:2]:
                suggestions.append(s)
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
        ha_ats = ha_result.get("ats")
        if ha_ats and ha_ats.missing_keywords:

            action_items.append(
                f"Add missing ATS keywords to your resume: {', '.join(ha_ats.missing_keywords[:4])}"
            )

    # Store tailoring preferences in memory
    try:
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
    except Exception as e:
        logger.debug("Failed to store resume tailoring memory: %s", e)

    result = {
        "suggestions": suggestions[:7],
        "ats_keywords": all_skills[:5],
        "role_type": role_type,
        "message": f"Resume tailored for {role_type} roles. {len(suggestions)} suggestions generated.",
        "action_items": action_items,
    }

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(
            collection="resume_embeddings",
            text=result["message"],
            vector=vector,
            metadata={
                "agent_type": "resume",
                "key": params.get("role_type", ""),
                "timestamp": str(datetime.now(timezone.utc)),
            },
        )
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result


async def generate_cover_letter(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Generate a personalized cover letter template."""
    company = params.get("company", "[Company]")
    role = params.get("role", "[Role]")
    skills = params.get("skills", [])

    profile_service = ProfileService(db)
    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)
    all_skills = list(set(skills + profile_skills))

    # ── Fetch GitHub + portfolio enrichment from memory ──
    ctx = await build_enrichment_context(db, user_id, all_skills)

    # ── Fetch hiring agent enrichment for cover letter ──
    ha_result = await enrich_with_hiring_agent(
        user_id=user_id, db=db,
        resume_text=None,
        target_role=role,
        target_company=company,
        job_description=params.get("job_description"),
    )

    llm = get_completion_llm(temperature=0.7, preferred_provider="openai")
    cover_letter = None
    customization_tips = None

    # Use hiring agent cover letter if available, fall through to LLM for prompt-based
    ha_cl = ha_result.get("cover_letter")
    if ha_cl:
        cover_letter = ha_cl
        customization_tips = [
            "Tailor the first paragraph to the specific role",
            "Add metrics and concrete project details",
            "Research the company's recent work and mention it",
        ]

    if llm and not cover_letter:
        try:
            from langchain_core.messages import HumanMessage

            portfolio_block = f"PORTFOLIO EVIDENCE (reference these real projects and experience):\n{ctx.portfolio_context}\n" if ctx.portfolio_context else ""
            github_block = f"GITHUB EVIDENCE (reference these real projects as proof of skill):\n{ctx.github_context}\n" if ctx.github_context else ""
            ha_block = ""
            ha_ats = ha_result.get("ats")
            ha_jd = ha_result.get("jd_match")
            if ha_ats:
                ha_block += f"ATS ANALYSIS — keyword coverage: {ha_ats.keyword_coverage_pct}%, missing: {', '.join(ha_ats.missing_keywords[:5])}\n"
            if ha_jd:
                ha_block += f"JD MATCH — overall score: {ha_jd.overall_score}/100, assessment: {ha_jd.overall_assessment}\n"
            if ha_block:
                ha_block = f"HIRING AGENT INSIGHTS:\n{ha_block}\n"

            prompt = f"""You are a professional cover letter writer.

USER CONTEXT:
- School/Background: {profile.school or "not specified"}
- Skills: {", ".join(all_skills) or "not specified"}
- Target company: {company}
- Target role: {role}

{portfolio_block}{github_block}{ha_block}Generate a compelling, professional cover letter and customization tips as a JSON object:
- "cover_letter": a full cover letter string (3-4 paragraphs, with greeting and sign-off using [Your Name])
- "customization_tips": array of 3 specific tips for personalizing this letter

The letter should reference the user's actual skills by name, show enthusiasm for the company, and be specific to the role.
If portfolio data is available, mention specific projects, role, and technologies from their portfolio.
If GitHub data is available, mention specific projects and languages from their GitHub profile.
Ground the letter in concrete project evidence — never make up generic claims.
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
        if ctx.pf_projects:
            for proj in ctx.pf_projects[:3]:
                cover_letter += f"- Developed {proj}\n"
        else:
            for skill in all_skills[:4]:
                cover_letter += f"- Building projects and solving problems using {skill}\n"

        if ctx.pf_experience:
            cover_letter += f"\nMy professional background includes {ctx.pf_experience[0]}"
            if len(ctx.pf_experience) > 1:
                cover_letter += f" as well as {ctx.pf_experience[1]}."
            cover_letter += "\n"

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

    # ── Fetch GitHub + portfolio enrichment from memory ──
    ctx = await build_enrichment_context(db, user_id, all_skills)

    llm = get_completion_llm(temperature=0.7, preferred_provider="openai")
    questions = None
    prep_tips = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            portfolio_block = f"PORTFOLIO EVIDENCE (use these real projects for behavioral questions):\n{ctx.portfolio_context}\n" if ctx.portfolio_context else ""
            github_block = f"GITHUB EVIDENCE (use these real projects for technical skill questions):\n{ctx.github_context}\n" if ctx.github_context else ""
            prompt = f"""You are an interview preparation expert.

USER CONTEXT:
- Skills: {", ".join(all_skills) or "not specified"}
- Target role type: {role_type}
- Target company: {company or "not specified"}

{portfolio_block}{github_block}Generate interview preparation materials as a JSON object:
- "questions": array of objects, each with keys "skill" (string), "question" (string), "type" ("behavioral" or "technical"), "tips" (string). Generate 2 questions per skill (one behavioral, one technical) for up to 5 skills, plus 3 general behavioral questions with skill set to "general".
- "prep_tips": array of 5 specific preparation tips referencing the user's actual skills and target company

Make questions realistic and tailored to the user's skills and target role.
If portfolio data is available, reference specific projects and experience in the question examples.
If GitHub data is available, reference specific repos and languages in technical questions.
Ground questions in real project evidence — make them feel like they come from a real code review or portfolio walkthrough.
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

    # Build project and repo context for fallback questions
    _project_names = ctx.pf_projects[:3] if ctx.pf_projects else []
    _project_ref = f"like your portfolio project '{_project_names[0]}'" if _project_names else ""

    if questions is None:
        questions = []
        for idx, skill in enumerate(all_skills[:5]):
            # Add project reference to first 2 behavioral questions when portfolio data exists
            project_suffix = f" — specifically in {_project_ref}" if _project_ref and idx < 2 else ""
            questions.append(
                {
                    "skill": skill,
                    "question": f"Describe your experience with {skill} and a project where you used it effectively.{project_suffix}",
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
        if ctx.pf_projects:
            prep_tips.append(
                f"Walk through your portfolio projects: {', '.join(ctx.pf_projects[:3])}"
            )
        if ctx.portfolio_context or ctx.github_context:
            prep_tips.append(
                "Be ready to dive into specific technical decisions from your GitHub/portfolio projects"
            )

    # Store interview prep in memory
    try:
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
    except Exception as e:
        logger.debug("Failed to store interview prep memory: %s", e)

    result = {
        "questions": questions,
        "total_questions": len(questions),
        "prep_tips": prep_tips,
        "focus_areas": all_skills[:3]
        + ["System Design Fundamentals", "Behavioral Storytelling"],
        "message": f"Generated {len(questions)} interview questions for preparation",
    }

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(
            collection="memory_notes",
            text=result["message"],
            vector=vector,
            metadata={
                "agent_type": "interview",
                "key": params.get("role_type", ""),
                "timestamp": str(datetime.now(timezone.utc)),
            },
        )
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result


# ─── Interview Answer Review ─────────────────────────────────


async def review_interview_answer(
    user_id: str,
    params: dict,
    db: AsyncSession,
) -> dict:
    """Review a user's interview answer and provide structured feedback."""
    question = params.get("question", "")
    answer = params.get("answer", "")
    company = params.get("company")
    role = params.get("role")

    llm = get_completion_llm(temperature=0.5, preferred_provider="openai")

    if not llm:
        return {
            "feedback": "AI review is unavailable. Your answer was recorded.",
            "score": None,
            "strengths": [],
            "improvements": [],
        }

    try:
        from langchain_core.messages import HumanMessage

        prompt = f"""You are an expert interview coach. Review this answer and provide structured feedback.

QUESTION: {question}

ANSWER: {answer}

{"COMPANY: " + company if company else ""}
{"ROLE: " + role if role else ""}

Return ONLY valid JSON with these keys:
- "feedback": A 2-3 sentence constructive critique of the answer
- "score": An integer 0-100 rating
- "strengths": Array of 1-3 specific strengths in the answer
- "improvements": Array of 1-3 specific improvements or gaps

Be specific and actionable. Reference what the candidate actually said.
Return ONLY valid JSON. No markdown, no explanations."""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        parsed = json.loads(_strip_json_fences(response.content))

        return {
            "feedback": parsed.get("feedback", "Your answer was reviewed."),
            "score": parsed.get("score"),
            "strengths": parsed.get("strengths", []),
            "improvements": parsed.get("improvements", []),
        }
    except Exception as e:
        logger.warning("LLM review_interview_answer failed: %s", e)
        return {
            "feedback": "Could not generate AI feedback at this time.",
            "score": None,
            "strengths": [],
            "improvements": [],
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

    # ── Fetch GitHub + portfolio enrichment from memory ──
    ctx = await build_enrichment_context(db, user_id, all_skills)

    llm = get_completion_llm(temperature=0.7, preferred_provider="openai")
    templates = None
    best_practices = None

    if llm:
        try:
            from langchain_core.messages import HumanMessage

            companies_str = (
                ", ".join(target_companies) if target_companies else "target companies"
            )

            portfolio_block = f"PORTFOLIO EVIDENCE (reference these real projects and experience):\n{ctx.portfolio_context}\n" if ctx.portfolio_context else ""
            github_block = f"GITHUB EVIDENCE (reference these real projects as proof of skill):\n{ctx.github_context}\n" if ctx.github_context else ""
            prompt = f"""You are a networking and outreach specialist.

USER CONTEXT:
- Skills: {", ".join(all_skills) or "not specified"}
- Target role: {role or "not specified"}
- Target companies: {companies_str}

{portfolio_block}{github_block}Generate outreach templates as a JSON object:
- "templates": array of objects, each with keys "type" ("cold_email" or "linkedin_message"), "subject" (string, empty for linkedin), "message" (string). Generate one cold_email and one linkedin_message per target company.
- "best_practices": array of 5 networking best practices (strings)

Messages should reference the user's actual skills, be concise, professional, and include a clear low-friction call to action.
If portfolio data is available, mention specific projects, role, and technologies from their portfolio.
If GitHub data is available, mention specific projects and languages from their GitHub profile.
Ground the message in concrete project evidence — never make up generic claims.
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
        # Build project bullet for inclusion in fallback templates
        project_bullets = ""
        if ctx.pf_projects:
            project_bullets = "My recent projects include:\n"
            for proj in ctx.pf_projects[:3]:
                project_bullets += f"- {proj}\n"
            project_bullets += "\n"

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
                        f"{project_bullets}"
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
                        f"{'I have projects in ' + ', '.join(ctx.pf_projects[:2]) + '. ' if ctx.pf_projects else ''}"
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
    try:
        await memory_service.set_memory(
            user_id,
            "last_networking",
            {
                "target_companies": target_companies,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            weight=0.7,
        )
    except Exception as e:
        logger.debug("Failed to store networking memory: %s", e)

    result = {
        "templates": templates,
        "message": f"Generated {len(templates)} outreach templates",
        "best_practices": best_practices,
    }

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(
            collection="memory_notes",
            text=result["message"],
            vector=vector,
            metadata={
                "agent_type": "outreach",
                "key": params.get("role", ""),
                "timestamp": str(datetime.now(timezone.utc)),
            },
        )
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result


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
            AlertConfig.is_active.is_(True),
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

    # If user typed a specific search query, use it as the primary keyword
    search_query = params.get("search_query")
    if search_query and search_query not in keywords:
        keywords.insert(0, search_query)

    # Quick scan across multiple types
    from app.search.adapters import SearchAdapter
    from app.utils.work_mode import categorize_search_keyword, infer_work_type

    search_adapter = SearchAdapter()
    all_new_items = []

    for keyword in keywords[:3]:
        kw = (keyword or "").strip()
        if not kw:
            continue
        # source_filter is a CATEGORY ("job"/"internship"), never raw query text —
        # otherwise the adapter skips its job-board + LinkedIn scrapers entirely.
        category = categorize_search_keyword(kw)
        try:
            results = await search_adapter.search(
                query=kw, limit=8, source_filter=category
            )
            for r in results:
                r.setdefault("_category", category)
            all_new_items.extend(results)
        except Exception as e:
            logger.debug("Monitor scan error for %s: %s", kw, e)

    # Fallback to demo data
    if not all_new_items:
        from app.utils.demo_data import generate_demo_opportunities

        all_new_items = generate_demo_opportunities(AgentType.monitor, "", "")

    # Skip opportunities the user already has (cross-run dedup, not just per-scan)
    existing_result = await db.execute(
        select(Opportunity.title, Opportunity.company).where(
            Opportunity.user_id == user_id
        )
    )
    existing_keys = {
        (t.lower().strip(), (c or "").lower().strip())
        for t, c in existing_result.all()
        if t
    }

    # Deduplicate and store
    seen_keys = set()
    stored_items = []
    for item in all_new_items[:20]:
        title = item.get("title", "")
        if not title:
            continue
        company = item.get("company", "Tech Company")
        key = (title.lower().strip(), (company or "").lower().strip())
        if key in seen_keys or key in existing_keys:
            continue
        seen_keys.add(key)

        loc_raw = item.get("location")
        parsed = parse_location(loc_raw)
        industry = detect_industry(
            title=title,
            company=item.get("company", ""),
            description=item.get("description", ""),
        )

        # Real full-time roles must not be mislabeled "Internship" — derive the
        # type from the result, falling back to the search category.
        opp_type = item.get("type")
        if not opp_type:
            opp_type = "Internship" if item.get("_category") == "internship" else "Full-time"

        remote = item.get("remote", False)
        work_type = item.get("work_type") or infer_work_type(
            remote, title, item.get("description"), loc_raw
        )

        opp = Opportunity(
            user_id=user_id,
            title=title,
            company=company,
            location=loc_raw,
            city=parsed["city"],
            state=parsed["state"],
            country=parsed["country"],
            industry=industry,
            remote=remote,
            work_type=work_type,
            type=opp_type,
            salary_min=item.get("salary_min"),
            salary_max=item.get("salary_max"),
            company_size=item.get("company_size"),
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

    # Store high-match alerts as notification memory entries
    from app.services.notification_service import create_notification
    from app.models.user import User

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    email_enabled = any(ac.email_notify for ac in alert_configs) if alert_configs else False

    for alert in alerts[:10]:
        title = f"High match: {alert['title']} @ {alert['company']}"
        body = alert["message"]
        await create_notification(
            db,
            user_id,
            title=title,
            body=body,
            type="success",
            to_email=user.email if (email_enabled and user and user.email) else None,
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

    result = {
        "items": stored_items,
        "total": len(stored_items),
        "scored": scored_count,
        "alerts": alerts[:10],
        "message": f"Scan completed: {len(stored_items)} new items, {scored_count} scored, {len(alerts)} high-match alerts",
    }

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(
            collection="memory_notes",
            text=result["message"],
            vector=vector,
            metadata={
                "agent_type": "scan",
                "key": "",
                "timestamp": str(datetime.now(timezone.utc)),
            },
        )
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result


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

    profile_service = ProfileService(db)
    agent_memory = AgentMemory(user_id)

    profile = await profile_service.get_or_create_profile(user_id)
    profile_skills = await profile_service.get_skill_names(profile.id)

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

    result = {
        "guidance": guidance,
        "message": "Career guidance generated based on your profile and market conditions",
    }

    try:
        agent_memory = AgentMemory(user_id)
        vector = await get_text_embedding(result["message"])
        agent_memory.store_vector(
            collection="memory_notes",
            text=result["message"],
            vector=vector,
            metadata={
                "agent_type": "guidance",
                "key": params.get("query", ""),
                "timestamp": str(datetime.now(timezone.utc)),
            },
        )
    except Exception as e:
        logger.debug("Failed to store memory vector: %s", e)

    return result
