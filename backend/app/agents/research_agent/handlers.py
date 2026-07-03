"""Research Agent handlers — company research, interview insights, and market intelligence."""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.search.adapters import SearchAdapter
from app.services.memory_service import MemoryService
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding
from app.services.model_manager import get_completion_llm
from app.agents.base import strip_json_fences
from app.agents.constants import (
    LLM_TEMPERATURE_PRECISE,
    LLM_PREFERRED_PROVIDER,
    MEMORY_WEIGHT_HIGH,
    MEMORY_WEIGHT_MEDIUM,
    COLLECTION_MEMORY_NOTES,
)

logger = logging.getLogger("agentforge.agents.research.handlers")

# ── Research Focus Types ──────────────────────────────────

VALID_FOCUS_TYPES = ("company", "interview-prep", "market", "skills")

# ── Main Handler ──────────────────────────────────────────


async def conduct_research(
    user_id: str,
    params: dict,
    db: AsyncSession,
    search_adapter: Optional[SearchAdapter] = None,
) -> dict:
    """Conduct research on companies, roles, interview insights, and market trends.

    Stores findings in memory for future retrieval.
    """
    query = params.get("query", "")
    topics = params.get("topics", [])
    focus = params.get("focus", "company")

    if not isinstance(query, str):
        raise ValueError("Invalid query: must be a string")
    if not isinstance(topics, list):
        topics = []
    if not isinstance(focus, str) or focus not in VALID_FOCUS_TYPES:
        focus = "company"

    memory_service = MemoryService(db)
    agent_memory = AgentMemory(user_id)

    try:
        existing = await memory_service.get_memory(user_id, "research_topics")
        if existing and isinstance(existing, dict):
            existing_topics = existing.get("topics", [])
            topics = list(set(topics + existing_topics))

        if search_adapter is None:
            search_adapter = SearchAdapter()

        results = {}

        if focus == "company" or (query and not focus):
            results["company_info"] = await _search_company(query, search_adapter)

        if focus == "interview-prep" or "interview" in query.lower():
            results["interview_insights"] = await _search_interview_insights(query, topics, search_adapter)

        if focus == "market" or "trend" in query.lower():
            results["market_trends"] = await _search_market_intelligence(topics, search_adapter)

        if focus == "skills":
            results["skill_analysis"] = await _search_skill_insights(topics, search_adapter)

        # Store research in memory
        await memory_service.set_memory(
            user_id,
            f"research_{datetime.now(timezone.utc).timestamp()}",
            {
                "query": query,
                "topics": topics,
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            weight=MEMORY_WEIGHT_HIGH,
        )

        await memory_service.set_memory(
            user_id,
            "research_topics",
            {"topics": topics, "last_query": query},
            weight=MEMORY_WEIGHT_MEDIUM,
        )

        # Store research vectors for semantic retrieval
        for topic in topics:
            await _store_research_embedding(user_id, agent_memory, topic, results)

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

    except Exception as e:
        logger.error("Research failed for user %s: %s", user_id, str(e))
        raise


# ── GitHub Enrichment ──────────────────────────────────────


async def _fetch_github_org_data(company_name: str) -> dict | None:
    """Fetch live GitHub organization details and repo language stats."""
    if not company_name:
        return None
    org_name = re.sub(r'[^a-zA-Z0-9-]', '', company_name.lower().replace(" ", ""))

    from app.config import settings
    headers = {"User-Agent": "AgentForge-CareerOS"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            org_res = await client.get(f"https://api.github.com/orgs/{org_name}", headers=headers)
            if org_res.status_code != 200:
                search_res = await client.get(
                    "https://api.github.com/search/users",
                    params={"q": f"{company_name} type:org"},
                    headers=headers,
                )
                if search_res.status_code == 200:
                    items = search_res.json().get("items", [])
                    if items:
                        org_name = items[0]["login"]
                        org_res = await client.get(f"https://api.github.com/orgs/{org_name}", headers=headers)

            if org_res.status_code == 200:
                org_data = org_res.json()
                repos_res = await client.get(
                    f"https://api.github.com/orgs/{org_name}/repos",
                    params={"sort": "updated", "per_page": "10"},
                    headers=headers,
                )
                repos = []
                languages = {}
                stars = 0
                if repos_res.status_code == 200:
                    for repo in repos_res.json():
                        stars += repo.get("stargazers_count", 0)
                        lang = repo.get("language")
                        if lang:
                            languages[lang] = languages.get(lang, 0) + 1
                        repos.append({
                            "name": repo.get("name"),
                            "stars": repo.get("stargazers_count"),
                            "language": lang,
                            "updated_at": repo.get("updated_at"),
                        })

                sorted_languages = [lang for lang, _ in sorted(languages.items(), key=lambda x: x[1], reverse=True)]
                return {
                    "login": org_data.get("login"),
                    "name": org_data.get("name"),
                    "description": org_data.get("description"),
                    "public_repos": org_data.get("public_repos", 0),
                    "followers": org_data.get("followers", 0),
                    "blog": org_data.get("blog"),
                    "languages": sorted_languages[:5],
                    "total_stars": stars,
                    "top_repos": [r["name"] for r in sorted(repos, key=lambda x: x["stars"], reverse=True)[:3]],
                }
    except Exception as e:
        logger.warning("Failed to fetch GitHub org data for %s: %s", company_name, e)
    return None


# ── Search Functions ───────────────────────────────────────


async def _search_company(company: str, search_adapter: SearchAdapter) -> dict:
    """Search the web for company information, fall back to static data."""
    if not company:
        return _fallback_company_info(company)
    try:
        query = f"{company} company overview funding culture tech stack hiring"
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return _fallback_company_info(company)

        snippets = " ".join(r.get("snippet", "") for r in results if r.get("snippet"))
        titles = " ".join(r.get("title", "") for r in results if r.get("title"))
        combined = f"{snippets} {titles}"

        github_data = await _fetch_github_org_data(company)

        llm = get_completion_llm(temperature=LLM_TEMPERATURE_PRECISE, preferred_provider=LLM_PREFERRED_PROVIDER)
        if llm:
            try:
                from langchain_core.messages import HumanMessage

                github_str = ""
                if github_data:
                    github_str = f"""
                    LIVE GITHUB DATA:
                    - Organization: {github_data.get('login')} ({github_data.get('name')})
                    - Description: {github_data.get('description')}
                    - Public Repos: {github_data.get('public_repos')}
                    - Primary Languages: {', '.join(github_data.get('languages', []))}
                    - Top Repositories: {', '.join(github_data.get('top_repos', []))}
                    - Community Stars on recent repos: {github_data.get('total_stars')}
                    """

                prompt = (
                    f"You are an expert company research analyst. Based on these web search snippets "
                    f"and optional live GitHub data about '{company}', construct a structured JSON report.\n\n"
                    f"SEARCH SNIPPETS:\n{combined}\n"
                    f"{github_str}\n"
                    f"""Return ONLY a valid JSON object with the following keys:
- "name": company name (string)
- "industry": primary industry / sector (string)
- "stage": stage of the company (e.g. Growth-stage startup, Public, seed, etc.) (string)
- "funding": estimate of funding raised or public market valuation (string)
- "culture": primary company culture traits (string)
- "tech_stack": list of 5-8 primary technologies used (list of strings)
- "hiring_trend": summary of hiring trends (string)
- "interview_process": list of 3-4 typical interview stages (list of strings)
- "summary": 2-3 sentence summary of the company overview and culture (string)

Do not include markdown code blocks, do not explain the output."""
                )

                response = await llm.ainvoke([HumanMessage(content=prompt)])
                data = json.loads(strip_json_fences(response.content))
                required = ["name", "industry", "stage", "funding", "culture", "tech_stack", "hiring_trend", "interview_process", "summary"]
                if all(k in data for k in required):
                    return data
            except Exception as e:
                logger.warning("LLM _search_company failed, falling back to regex: %s", e)

        # Regex/heuristic fallback
        return _fallback_company_info(company, combined, github_data)

    except Exception as e:
        logger.debug("Web search failed for company '%s': %s", company, e)
        return _fallback_company_info(company)


async def _search_interview_insights(role: str, skills: list[str], search_adapter: SearchAdapter) -> dict:
    """Search the web for interview insights, fall back to static data."""
    try:
        query = f"{role} interview questions tips preparation"
        if skills:
            query += f" {' '.join(skills[:3])}"
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return _fallback_interview_insights(role, skills)

        snippets = " ".join(r.get("snippet", "") for r in results if r.get("snippet"))

        llm = get_completion_llm(temperature=LLM_TEMPERATURE_PRECISE, preferred_provider=LLM_PREFERRED_PROVIDER)
        if llm:
            try:
                from langchain_core.messages import HumanMessage

                prompt = (
                    f"You are an expert interview coach. Based on these search snippets "
                    f"about '{role}' interview preparation, construct a structured JSON report.\n\n"
                    f"SEARCH SNIPPETS:\n{snippets}\n"
                    f"""Return ONLY a valid JSON object with the following keys:
- "focus_areas": list of 3-4 primary technical or behavioral focus areas (list of strings)
- "common_questions": list of 5 typical behavioral or technical questions (list of strings)
- "tips": summary of tips/strategies for this specific role's interview (string)
- "recommended_prep": list of 3 actionable preparation steps (list of strings)

Do not include markdown code blocks, do not explain the output."""
                )

                response = await llm.ainvoke([HumanMessage(content=prompt)])
                data = json.loads(strip_json_fences(response.content))
                required = ["focus_areas", "common_questions", "tips", "recommended_prep"]
                if all(k in data for k in required):
                    return data
            except Exception as e:
                logger.warning("LLM _search_interview_insights failed, falling back to regex: %s", e)

        return _fallback_interview_insights(role, skills, snippets)
    except Exception as e:
        logger.debug("Web search failed for interview insights '%s': %s", role, e)
        return _fallback_interview_insights(role, skills)


async def _search_market_intelligence(skills: list[str], search_adapter: SearchAdapter) -> dict:
    """Search the web for market trends, fall back to static data."""
    try:
        query = "market trends tech hiring demand"
        if skills:
            query = f"{' '.join(skills[:3])} job market demand trends 2026"
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return _fallback_market_intelligence(skills)

        snippets = " ".join(r.get("snippet", "") for r in results if r.get("snippet"))
        combined = snippets.lower()

        llm = get_completion_llm(temperature=LLM_TEMPERATURE_PRECISE, preferred_provider=LLM_PREFERRED_PROVIDER)
        if llm:
            try:
                from langchain_core.messages import HumanMessage

                prompt = (
                    f"You are a market research analyst. Based on these search snippets about current tech market trends "
                    f"(focusing on {', '.join(skills) if skills else 'general tech'}), construct a structured JSON report.\n\n"
                    f"SEARCH SNIPPETS:\n{snippets}\n"
                    f"""Return ONLY a valid JSON object with the following keys:
- "outlook": 2-3 sentence overview of the hiring outlook (string)
- "trending_roles": list of 3 trending job titles in this area (list of strings)
- "salary_range": estimated salary range for these roles (string)
- "growth_areas": list of 3-4 growing industries/domains (list of strings)
- "suggestions": list of 3 career development recommendations (list of strings)

Do not include markdown code blocks, do not explain the output."""
                )

                response = await llm.ainvoke([HumanMessage(content=prompt)])
                data = json.loads(strip_json_fences(response.content))
                required = ["outlook", "trending_roles", "salary_range", "growth_areas", "suggestions"]
                if all(k in data for k in required):
                    return data
            except Exception as e:
                logger.warning("LLM _search_market_intelligence failed, falling back to regex: %s", e)

        return _fallback_market_intelligence(skills, snippets)
    except Exception as e:
        logger.debug("Web search failed for market intelligence: %s", e)
        return _fallback_market_intelligence(skills)


async def _search_skill_insights(skills: list[str], search_adapter: SearchAdapter) -> dict:
    """Search the web for skill demand insights, fall back to static data."""
    try:
        query = "most in-demand tech skills 2026"
        if skills:
            query = f"{' '.join(skills[:3])} skill demand trending 2026"
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return _fallback_skill_insights(skills)

        snippets = " ".join(r.get("snippet", "") for r in results if r.get("snippet"))
        combined = snippets.lower()

        llm = get_completion_llm(temperature=LLM_TEMPERATURE_PRECISE, preferred_provider=LLM_PREFERRED_PROVIDER)
        if llm:
            try:
                from langchain_core.messages import HumanMessage

                prompt = (
                    f"You are a technical skills analyst. Based on these search snippets about technical skill demand "
                    f"(focusing on {', '.join(skills) if skills else 'general tech'}), construct a structured JSON report.\n\n"
                    f"SEARCH SNIPPETS:\n{snippets}\n"
                    f"""Return ONLY a valid JSON object with the following keys:
- "insight": 2-3 sentence overview of the demand for these skills (string)
- "skill_demand_map": dictionary mapping each skill to a demand level (e.g. 'high', 'very high', 'stable') (dict)
- "recommended_skills": list of 3 supplementary skills to learn (list of strings)
- "learning_resources": list of 3 recommended books, courses, or resources (list of strings)

Do not include markdown code blocks, do not explain the output."""
                )

                response = await llm.ainvoke([HumanMessage(content=prompt)])
                data = json.loads(strip_json_fences(response.content))
                required = ["insight", "skill_demand_map", "recommended_skills", "learning_resources"]
                if all(k in data for k in required):
                    return data
            except Exception as e:
                logger.warning("LLM _search_skill_insights failed, falling back to regex: %s", e)

        return _fallback_skill_insights(skills, snippets)
    except Exception as e:
        logger.debug("Web search failed for skill insights: %s", e)
        return _fallback_skill_insights(skills)


# ── Fallback Templates ──────────────────────────────────────


def _fallback_company_info(company: str, combined: str = "", github_data: dict | None = None) -> dict:
    """Generate fallback company research info when LLM is unavailable."""
    if combined:
        combined_lower = combined.lower()
        industry = "Technology / AI"
        for kw in ["ai", "machine learning", "fintech", "healthcare", "saas", "e-commerce", "cloud"]:
            if kw in combined_lower:
                industry = kw.title()
                break

        funding = "Information not available"
        fm = re.search(r"(\$[\d,.]+[BMK]?[\s]*(?:million|billion|m|b)?[\s]*(?:raised|funding|series|round))", combined, re.IGNORECASE)
        if fm:
            funding = fm.group(1)

        culture = "Information not available"
        for c in ["fast-paced", "remote-first", "hybrid", "startup", "enterprise", "flat hierarchy", "innovation-driven"]:
            if c in combined_lower:
                culture = c
                break

        tech_stack = ["Python", "TypeScript", "React", "AWS", "PostgreSQL"]
        if github_data and github_data.get("languages"):
            tech_stack = [t.title() if t.lower() != "node.js" else "Node.js" for t in github_data["languages"]]
            if "React" not in tech_stack:
                tech_stack.append("React")
            if "AWS" not in tech_stack:
                tech_stack.append("AWS")
        known_techs = ["python", "typescript", "react", "aws", "postgresql", "golang", "rust", "kubernetes", "docker", "tensorflow", "pytorch", "node.js", "graphql", "kafka"]
        found = [t for t in known_techs if t in combined_lower]
        if found:
            tech_stack = [t.title() if t != "node.js" else "Node.js" for t in found[:6]]

        snippet_str = combined[:500]
        return {
            "name": company or "Tech Company",
            "industry": industry,
            "stage": "Growth-stage startup" if company else "Various",
            "funding": funding,
            "culture": culture,
            "tech_stack": tech_stack,
            "hiring_trend": "Actively hiring across multiple roles" if re.search(r"(hiring|jobs|careers|positions? open)", combined_lower, re.IGNORECASE) else "Information not available",
            "interview_process": ["Initial recruiter screen (30 min)", "Technical phone screen (45-60 min)", "On-site / final round (3-5 sessions)", "Team matching / offer decision"],
            "summary": snippet_str,
        }

    return {
        "name": company or "Tech Company",
        "industry": "Technology / AI",
        "stage": "Growth-stage startup" if company else "Various",
        "funding": "$10M+ raised (series A-B)" if company else "Information not available",
        "culture": "Fast-paced, innovation-driven, flat hierarchy",
        "tech_stack": ["Python", "TypeScript", "React", "AWS", "PostgreSQL"],
        "hiring_trend": "Actively hiring for engineering and AI roles",
        "interview_process": ["Initial recruiter screen (30 min)", "Technical phone screen (45-60 min)", "On-site / final round (3-5 sessions)", "Team matching / offer decision"],
        "summary": f"{company or 'This company'} is actively building its engineering team with a focus on AI/ML capabilities. The interview process typically takes 2-3 weeks from screen to offer.",
    }


def _fallback_interview_insights(role: str, skills: list[str], snippets: str = "") -> dict:
    """Generate fallback interview preparation insights when LLM is unavailable."""
    all_questions = [
        "Tell me about a project where you demonstrated technical leadership.",
        "Describe a time you faced a challenging bug and how you resolved it.",
        "How do you approach designing a scalable system?",
        "Explain a technical concept to a non-technical stakeholder.",
        "Walk me through your approach to debugging a production issue.",
    ]
    skill_questions = [f"Describe your experience with {s} in a real-world setting." for s in skills] if skills else []

    tips = snippets[:200] if snippets else (
        "Prepare 2-3 strong STAR-format stories. Review system design fundamentals. "
        "Research the company's tech stack and recent product launches."
    )

    return {
        "focus_areas": skills or ["Technical fundamentals", "System design", "Behavioral stories"],
        "common_questions": all_questions[:5] + skill_questions[:3],
        "tips": tips,
        "recommended_prep": [
            "Review core data structures and algorithms",
            f"Practice problems related to {', '.join(skills[:3])}" if skills else "Practice coding problems",
            "Prepare questions to ask the interviewer",
        ],
    }


def _fallback_market_intelligence(skills: list[str], snippets: str = "") -> dict:
    """Generate fallback market intelligence when LLM is unavailable."""
    combined_lower = snippets.lower()
    outlook = snippets[:200] if snippets else (
        f"Strong demand for {' and '.join(skills[:2])} skills" if skills else "Strong demand for engineering talent."
    )

    growth_areas = ["AI safety", "Developer tools", "Fintech", "Climate tech"]
    known_areas = ["ai safety", "fintech", "climate tech", "developer tools", "healthtech", "edtech", "cybersecurity", "blockchain"]
    found_areas = [a.title() for a in known_areas if a in combined_lower]
    if found_areas:
        growth_areas = found_areas[:4]

    return {
        "outlook": outlook,
        "trending_roles": ["AI/ML Engineer", "Full-stack Developer (AI-integrated apps)", "Developer Experience Engineer"],
        "salary_range": "$120K - $200K+ (depending on location and experience)",
        "growth_areas": growth_areas,
        "suggestions": ["Focus on building AI-integrated projects", "Contribute to open-source in relevant domains", "Build a strong online presence (blog, GitHub, Twitter/X)"],
    }


def _fallback_skill_insights(skills: list[str], snippets: str = "") -> dict:
    """Generate fallback skill insights when LLM is unavailable."""
    combined_lower = snippets.lower()
    insight = snippets[:200] if snippets else (
        f"Your skills in {', '.join(skills[:3])} are in high demand." if skills else "Current market shows strong tech demand."
    )

    skill_demand_map = {s: "high" for s in skills}
    known_high = ["ai", "machine learning", "python", "cloud", "kubernetes", "data science", "react"]
    for s in skills:
        if s.lower() in known_high:
            skill_demand_map[s] = "very high"

    recommended = ["System Design", "Cloud Architecture", "AI/ML Integration"]
    rec_keywords = ["system design", "cloud architecture", "ai/ml", "kubernetes", "typescript", "rust", "go"]
    found_rec = [r.title() for r in rec_keywords if r in combined_lower and r.title() not in [x.lower() for x in skills]]
    if found_rec:
        recommended = found_rec[:3]

    return {
        "insight": insight,
        "skill_demand_map": skill_demand_map,
        "recommended_skills": recommended,
        "learning_resources": ["System Design Interview — Alex Xu", "CS231n / CS224n (Stanford online)", "Building LLM Applications (DeepLearning.AI)"],
    }


# ── Embedding Helpers ──────────────────────────────────────


async def _store_research_embedding(user_id: str, agent_memory: AgentMemory, topic: str, results: dict) -> None:
    """Store research findings as vector embeddings."""
    try:
        text = f"Research on {topic}: {str(results)[:2000]}"
        vector = await get_text_embedding(text)
        agent_memory.store_vector(
            collection="research_notes",
            text=text,
            vector=vector,
            metadata={"topic": topic, "user_id": user_id, "type": "research"},
        )
    except Exception as e:
        logger.debug("Failed to store research embedding: %s", e)


async def retrieve_research_context(user_id: str, query: str, limit: int = 3) -> str:
    """Retrieve relevant research context for a given query using semantic search."""
    try:
        agent_memory = AgentMemory(user_id)
        query_vector = await get_text_embedding(query)
        return agent_memory.get_relevant_context(query_vector, limit=limit)
    except Exception as e:
        logger.debug("Failed to retrieve research context: %s", e)
        return "Research context unavailable."
