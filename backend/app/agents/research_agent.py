"""
Research Agent — specialized in company research, interview insights, and market intelligence.

Integrates with:
- MemoryService for storing research findings
- Qdrant for semantic search over research notes
- Web search for real-time company data
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import MemoryService
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding, compute_similarity

logger = logging.getLogger("agentforge.agents.research")


async def conduct_research(
    user_id: str,
    params: dict,
    db: AsyncSession,
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

    results = {}

    if focus == "company" or (query and not focus):
        results["company_info"] = _research_company(query)

    if focus == "interview-prep" or "interview" in query.lower():
        results["interview_insights"] = _interview_insights(query, topics)

    if focus == "market" or "trend" in query.lower():
        results["market_trends"] = _market_intelligence(topics)

    if focus == "skills":
        results["skill_analysis"] = _skill_insights(topics)

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
        _store_research_embedding(user_id, agent_memory, topic, results)

    # Build summary
    sections = []
    if results.get("company_info"):
        c = results["company_info"]
        sections.append(f"🏢 {c.get('name', 'Company')} — {c.get('industry', 'Tech')}")
        sections.append(c.get("summary", ""))

    if results.get("interview_insights"):
        insights = results["interview_insights"]
        sections.append(f"🎙️ Interview Tips: {insights.get('tips', 'Focus on fundamentals and problem-solving.')}")
        questions = insights.get("common_questions", [])
        if questions:
            sections.append("Sample questions: " + "; ".join(questions[:3]))

    if results.get("market_trends"):
        trends = results["market_trends"]
        sections.append(f"📈 Market: {trends.get('outlook', 'Growing demand across roles.')}")

    if results.get("skill_analysis"):
        sa = results["skill_analysis"]
        sections.append(f"🛠️ Skills: {sa.get('insight', 'Your skills align with current market needs.')}")

    return {
        "results": results,
        "summary": "\n\n".join(sections) if sections else "Research completed. No specific findings for the given query.",
        "topics": topics,
        "message": f"Research complete on {len(topics)} topics",
    }


def _research_company(company: str) -> dict:
    """Compile company research information."""
    # In production, this would query Crunchbase, LinkedIn, Glassdoor APIs
    return {
        "name": company or "Tech Company",
        "industry": "Technology / AI",
        "stage": "Growth-stage startup" if company else "Various",
        "funding": "$10M+ raised (series A-B)" if company else "Information not available",
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

    skill_questions = [
        f"Describe your experience with {s} in a real-world setting." for s in skills
    ] if skills else []

    return {
        "focus_areas": skills or ["Technical fundamentals", "System design", "Behavioral stories"],
        "common_questions": all_questions[:5] + skill_questions[:3],
        "tips": "Prepare 2-3 strong STAR-format stories. Review system design fundamentals. "
                "Research the company's tech stack and recent product launches.",
        "recommended_prep": [
            "Review core data structures and algorithms",
            f"Practice problems related to {', '.join(skills[:3])}" if skills else "Practice coding problems",
            "Prepare questions to ask the interviewer",
        ],
    }


def _market_intelligence(skills: list[str]) -> dict:
    """Research market trends for given skills."""
    return {
        "outlook": f"Strong demand for {' and '.join(skills[:2])} skills in the current market."
                   if skills else "Strong overall demand for engineering talent.",
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
        "recommended_skills": ["System Design", "Cloud Architecture", "AI/ML Integration"],
        "learning_resources": [
            "System Design Interview — Alex Xu",
            "CS231n / CS224n (Stanford online)",
            "Building LLM Applications (DeepLearning.AI)",
        ],
    }


def _store_research_embedding(user_id: str, agent_memory: AgentMemory, topic: str, results: dict):
    """Store research findings as vector embeddings."""
    try:
        text = f"Research on {topic}: {str(results)[:2000]}"
        vector = get_text_embedding(text)
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
        query_vector = get_text_embedding(query)
        return agent_memory.get_relevant_context(query_vector, limit=limit)
    except Exception as e:
        logger.debug("Failed to retrieve research context: %s", e)
        return "Research context unavailable."
