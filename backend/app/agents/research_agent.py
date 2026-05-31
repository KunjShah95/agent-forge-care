"""
Research Agent — specialized in company research, interview insights, and market intelligence.

Integrates with:
- MemoryService for storing research findings
- Qdrant for semantic search over research notes
- Web search for real-time company data
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.search.adapters import SearchAdapter
from app.services.memory_service import MemoryService
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding, compute_similarity

logger = logging.getLogger("agentforge.agents.research")


async def conduct_research(
    user_id: str,
    params: dict,
    db: AsyncSession,
    search_adapter: Optional[SearchAdapter] = None,
) -> dict:
    """
    Conduct research on companies, roles, interview insights, and market trends.
    Stores findings in memory for future retrieval.
    """
    query = params.get("query", "")
    topics = params.get("topics", [])
    focus = params.get("focus", "company")  # company | interview-prep | market | skills

    memory_service = MemoryService(db)
    agent_memory = AgentMemory(user_id)

    # Check memory for existing research on this topic
    existing = await memory_service.get_memory(user_id, "research_topics")
    if existing and isinstance(existing, dict):
        existing_topics = existing.get("topics", [])
        # Merge topics
        topics = list(set(topics + existing_topics))

    if search_adapter is None:
        search_adapter = SearchAdapter()

    results = {}

    if focus == "company" or (query and not focus):
        results["company_info"] = await _search_company(query, search_adapter)

    if focus == "interview-prep" or "interview" in query.lower():
        results["interview_insights"] = await _search_interview_insights(
            query, topics, search_adapter
        )

    if focus == "market" or "trend" in query.lower():
        results["market_trends"] = await _search_market_intelligence(
            topics, search_adapter
        )

    if focus == "skills":
        results["skill_analysis"] = await _search_skill_insights(topics, search_adapter)

    # Store full research in memory
    await memory_service.set_memory(
        user_id,
        f"research_{datetime.now(timezone.utc).timestamp()}",
        {
            "query": query,
            "topics": topics,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        weight=0.9,
    )

    # Update consolidated research topics
    await memory_service.set_memory(
        user_id,
        "research_topics",
        {"topics": topics, "last_query": query},
        weight=0.7,
    )

    # Store research vectors in Qdrant for semantic retrieval
    for topic in topics:
        await _store_research_embedding(user_id, agent_memory, topic, results)


async def _store_research_embedding(user_id: str, agent_memory: AgentMemory, topic: str, results: dict) -> None:
    try:
        vec = await get_text_embedding(topic)
        # AgentMemory.store_vector is synchronous
        agent_memory.store_vector(
            collection="research_embeddings",
            text=topic,
            vector=vec,
            metadata={"user_id": user_id, "type": "topic"},
        )
    except Exception:
        logger.exception("Failed to store research embedding for topic: %s", topic)

    # Build summary
    sections = []
    if results.get("company_info"):
        c = results["company_info"]
        sections.append(f"🏢 {c.get('name', 'Company')} — {c.get('industry', 'Tech')}")
        sections.append(c.get("summary", ""))

    if results.get("interview_insights"):
        insights = results["interview_insights"]
        sections.append(
            f"🎙️ Interview Tips: {insights.get('tips', 'Focus on fundamentals and problem-solving.')}"
        )
        questions = insights.get("common_questions", [])
        if questions:
            sections.append("Sample questions: " + "; ".join(questions[:3]))

    if results.get("market_trends"):
        trends = results["market_trends"]
        sections.append(
            f"📈 Market: {trends.get('outlook', 'Growing demand across roles.')}"
        )

    if results.get("skill_analysis"):
        sa = results["skill_analysis"]
        sections.append(
            f"🛠️ Skills: {sa.get('insight', 'Your skills align with current market needs.')}"
        )

    return {
        "results": results,
        "summary": "\n\n".join(sections)
        if sections
        else "Research completed. No specific findings for the given query.",
        "topics": topics,
        "message": f"Research complete on {len(topics)} topics",
    }


async def _search_company(company: str, search_adapter: SearchAdapter) -> dict:
    """Search the web for company information, fall back to static data."""
    if not company:
        return _research_company(company)
    try:
        query = f"{company} company overview funding culture tech stack hiring"
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return _research_company(company)

        snippets = " ".join(r.get("snippet", "") for r in results if r.get("snippet"))
        titles = " ".join(r.get("title", "") for r in results if r.get("title"))
        combined = f"{snippets} {titles}".lower()

        industry = "Technology / AI"
        for kw in [
            "ai",
            "machine learning",
            "fintech",
            "healthcare",
            "saas",
            "e-commerce",
            "cloud",
        ]:
            if kw in combined:
                industry = kw.title()
                break

        funding = "Information not available"
        fm = re.search(
            r"(\$[\d,.]+[BMK]?[\s]*(?:million|billion|m|b)?[\s]*(?:raised|funding|series|round))",
            combined,
            re.IGNORECASE,
        )
        if fm:
            funding = fm.group(1)

        culture = "Information not available"
        for c in [
            "fast-paced",
            "remote-first",
            "hybrid",
            "startup",
            "enterprise",
            "flat hierarchy",
            "innovation-driven",
        ]:
            if c in combined:
                culture = c
                break

        tech_stack = ["Python", "TypeScript", "React", "AWS", "PostgreSQL"]
        known_techs = [
            "python",
            "typescript",
            "react",
            "aws",
            "postgresql",
            "golang",
            "rust",
            "kubernetes",
            "docker",
            "tensorflow",
            "pytorch",
            "node.js",
            "graphql",
            "kafka",
        ]
        found = [t for t in known_techs if t in combined]
        if found:
            tech_stack = [t.title() if t != "node.js" else "Node.js" for t in found[:6]]

        hiring = "Information not available"
        if re.search(r"(hiring|jobs|careers|positions? open)", combined, re.IGNORECASE):
            hiring = "Actively hiring across multiple roles"

        summary = snippets[:500] if snippets else _research_company(company)["summary"]

        return {
            "name": company or "Tech Company",
            "industry": industry,
            "stage": "Growth-stage startup" if company else "Various",
            "funding": funding,
            "culture": culture,
            "tech_stack": tech_stack,
            "hiring_trend": hiring,
            "interview_process": [
                "Initial recruiter screen (30 min)",
                "Technical phone screen (45-60 min)",
                "On-site / final round (3-5 sessions)",
                "Team matching / offer decision",
            ],
            "summary": summary,
        }
    except Exception as e:
        logger.debug("Web search failed for company '%s': %s", company, e)
        return _research_company(company)


async def _search_interview_insights(
    role: str, skills: list[str], search_adapter: SearchAdapter
) -> dict:
    """Search the web for interview insights, fall back to static data."""
    try:
        query = f"{role} interview questions tips preparation"
        if skills:
            query += f" {' '.join(skills[:3])}"
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return _interview_insights(role, skills)

        snippets = " ".join(r.get("snippet", "") for r in results if r.get("snippet"))

        tips = "Focus on fundamentals and problem-solving."
        if snippets:
            tips = snippets[:200]

        focus_areas = skills or [
            "Technical fundamentals",
            "System design",
            "Behavioral stories",
        ]
        all_questions = [
            "Tell me about a project where you demonstrated technical leadership.",
            "Describe a time you faced a challenging bug and how you resolved it.",
            "How do you approach designing a scalable system?",
            "Explain a technical concept to a non-technical stakeholder.",
            "Walk me through your approach to debugging a production issue.",
        ]
        skill_questions = (
            [
                f"Describe your experience with {s} in a real-world setting."
                for s in skills
            ]
            if skills
            else []
        )

        return {
            "focus_areas": focus_areas,
            "common_questions": all_questions[:5] + skill_questions[:3],
            "tips": tips,
            "recommended_prep": [
                "Review core data structures and algorithms",
                f"Practice problems related to {', '.join(skills[:3])}"
                if skills
                else "Practice coding problems",
                "Prepare questions to ask the interviewer",
            ],
        }
    except Exception as e:
        logger.debug("Web search failed for interview insights '%s': %s", role, e)
        return _interview_insights(role, skills)


async def _search_market_intelligence(
    skills: list[str], search_adapter: SearchAdapter
) -> dict:
    """Search the web for market trends, fall back to static data."""
    try:
        query = "market trends tech hiring demand"
        if skills:
            query = f"{' '.join(skills[:3])} job market demand trends 2026"
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return _market_intelligence(skills)

        snippets = " ".join(r.get("snippet", "") for r in results if r.get("snippet"))
        combined = snippets.lower()

        outlook = (
            f"Strong demand for {' and '.join(skills[:2])} skills"
            if skills
            else "Strong demand for engineering talent."
        )
        if combined:
            outlook = snippets[:200]

        growth_areas = ["AI safety", "Developer tools", "Fintech", "Climate tech"]
        known_areas = [
            "ai safety",
            "fintech",
            "climate tech",
            "developer tools",
            "healthtech",
            "edtech",
            "cybersecurity",
            "blockchain",
        ]
        found_areas = [a.title() for a in known_areas if a in combined]
        if found_areas:
            growth_areas = found_areas[:4]

        return {
            "outlook": outlook,
            "trending_roles": [
                "AI/ML Engineer",
                "Full-stack Developer (AI-integrated apps)",
                "Developer Experience Engineer",
            ],
            "salary_range": "$120K - $200K+ (depending on location and experience)",
            "growth_areas": growth_areas,
            "suggestions": [
                "Focus on building AI-integrated projects",
                "Contribute to open-source in relevant domains",
                "Build a strong online presence (blog, GitHub, Twitter/X)",
            ],
        }
    except Exception as e:
        logger.debug("Web search failed for market intelligence: %s", e)
        return _market_intelligence(skills)


async def _search_skill_insights(
    skills: list[str], search_adapter: SearchAdapter
) -> dict:
    """Search the web for skill demand insights, fall back to static data."""
    try:
        query = "most in-demand tech skills 2026"
        if skills:
            query = f"{' '.join(skills[:3])} skill demand trending 2026"
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return _skill_insights(skills)

        snippets = " ".join(r.get("snippet", "") for r in results if r.get("snippet"))
        combined = snippets.lower()

        insight = (
            snippets[:200]
            if snippets
            else (
                f"Your skills in {', '.join(skills[:3])} are in high demand."
                if skills
                else "Current market shows strong tech demand."
            )
        )

        skill_demand_map = {s: "high" for s in skills}
        known_high = [
            "ai",
            "machine learning",
            "python",
            "cloud",
            "kubernetes",
            "data science",
            "react",
        ]
        for s in skills:
            if s.lower() in known_high:
                skill_demand_map[s] = "very high"

        recommended = ["System Design", "Cloud Architecture", "AI/ML Integration"]
        rec_keywords = [
            "system design",
            "cloud architecture",
            "ai/ml",
            "kubernetes",
            "typescript",
            "rust",
            "go",
        ]
        found_rec = [
            r.title()
            for r in rec_keywords
            if r in combined and r.title() not in [x.lower() for x in skills]
        ]
        if found_rec:
            recommended = found_rec[:3]

        return {
            "insight": insight,
            "skill_demand_map": skill_demand_map,
            "recommended_skills": recommended,
            "learning_resources": [
                "System Design Interview — Alex Xu",
                "CS231n / CS224n (Stanford online)",
                "Building LLM Applications (DeepLearning.AI)",
            ],
        }
    except Exception as e:
        logger.debug("Web search failed for skill insights: %s", e)
        return _skill_insights(skills)


def _research_company(company: str) -> dict:
    """Compile company research information."""
    # In production, this would query Crunchbase, LinkedIn, Glassdoor APIs
    return {
        "name": company or "Tech Company",
        "industry": "Technology / AI",
        "stage": "Growth-stage startup" if company else "Various",
        "funding": "$10M+ raised (series A-B)"
        if company
        else "Information not available",
        "culture": "Fast-paced, innovation-driven, flat hierarchy",
        "tech_stack": ["Python", "TypeScript", "React", "AWS", "PostgreSQL"],
        "hiring_trend": "Actively hiring for engineering and AI roles",
        "interview_process": [
            "Initial recruiter screen (30 min)",
            "Technical phone screen (45-60 min)",
            "On-site / final round (3-5 sessions)",
            "Team matching / offer decision",
        ],
        "summary": f"{company or 'This company'} is actively building its engineering team "
        f"with a focus on AI/ML capabilities. The interview process typically "
        f"takes 2-3 weeks from screen to offer.",
    }


def _interview_insights(role: str, skills: list[str]) -> dict:
    """Generate interview preparation insights."""
    all_questions = [
        "Tell me about a project where you demonstrated technical leadership.",
        "Describe a time you faced a challenging bug and how you resolved it.",
        "How do you approach designing a scalable system?",
        "Explain a technical concept to a non-technical stakeholder.",
        "Walk me through your approach to debugging a production issue.",
    ]

    skill_questions = (
        [f"Describe your experience with {s} in a real-world setting." for s in skills]
        if skills
        else []
    )

    return {
        "focus_areas": skills
        or ["Technical fundamentals", "System design", "Behavioral stories"],
        "common_questions": all_questions[:5] + skill_questions[:3],
        "tips": "Prepare 2-3 strong STAR-format stories. Review system design fundamentals. "
        "Research the company's tech stack and recent product launches.",
        "recommended_prep": [
            "Review core data structures and algorithms",
            f"Practice problems related to {', '.join(skills[:3])}"
            if skills
            else "Practice coding problems",
            "Prepare questions to ask the interviewer",
        ],
    }


def _market_intelligence(skills: list[str]) -> dict:
    """Research market trends for given skills."""
    return {
        "outlook": f"Strong demand for {' and '.join(skills[:2])} skills in the current market."
        if skills
        else "Strong overall demand for engineering talent.",
        "trending_roles": [
            "AI/ML Engineer",
            "Full-stack Developer (AI-integrated apps)",
            "Developer Experience Engineer",
        ],
        "salary_range": "$120K - $200K+ (depending on location and experience)",
        "growth_areas": ["AI safety", "Developer tools", "Fintech", "Climate tech"],
        "suggestions": [
            "Focus on building AI-integrated projects",
            "Contribute to open-source in relevant domains",
            "Build a strong online presence (blog, GitHub, Twitter/X)",
        ],
    }


def _skill_insights(skills: list[str]) -> dict:
    """Analyze skill relevance and suggest growth areas."""
    return {
        "insight": f"Your skills in {', '.join(skills[:3])} are in high demand. "
        f"Consider deepening expertise in at least one area.",
        "skill_demand_map": {s: "high" for s in skills},
        "recommended_skills": [
            "System Design",
            "Cloud Architecture",
            "AI/ML Integration",
        ],
        "learning_resources": [
            "System Design Interview — Alex Xu",
            "CS231n / CS224n (Stanford online)",
            "Building LLM Applications (DeepLearning.AI)",
        ],
    }


async def _store_research_embedding(
    user_id: str, agent_memory: AgentMemory, topic: str, results: dict
):
    """Store research findings as vector embeddings."""
    try:
        text = f"Research on {topic}: {str(results)[:2000]}"
        vector = await get_text_embedding(text)
        agent_memory.store_vector(
            collection="research_notes",
            text=text,
            vector=vector,
            metadata={
                "topic": topic,
                "user_id": user_id,
                "type": "research",
            },
        )
    except Exception as e:
        logger.debug("Failed to store research embedding: %s", e)


async def retrieve_research_context(
    user_id: str,
    query: str,
    limit: int = 3,
) -> str:
    """
    Retrieve relevant research context for a given query using semantic search.
    Returns formatted research notes for use in agent prompts.
    """
    try:
        agent_memory = AgentMemory(user_id)
        query_vector = await get_text_embedding(query)
        return agent_memory.get_relevant_context(query_vector, limit=limit)
    except Exception as e:
        logger.debug("Failed to retrieve research context: %s", e)
        return "Research context unavailable."
