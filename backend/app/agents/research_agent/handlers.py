"""Research Agent handlers — company research, interview insights, and market intelligence."""

import asyncio
import json
import logging
import re
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import strip_json_fences
from app.agents.constants import (
    LLM_PROVIDER_RESEARCH,
    LLM_TEMPERATURE_PRECISE,
    MEMORY_WEIGHT_HIGH,
    MEMORY_WEIGHT_MEDIUM,
)
from app.memory.memory_layer import AgentMemory
from app.search.adapters import SearchAdapter
from app.services.memory_service import MemoryService
from app.services.model_manager import get_completion_llm
from app.utils.embedding import get_text_embedding

logger = logging.getLogger("agentforge.agents.research.handlers")

VALID_FOCUS_TYPES = ("company", "interview-prep", "market", "skills")


async def conduct_research(
    user_id: str,
    params: dict,
    db: AsyncSession,
    search_adapter: SearchAdapter | None = None,
) -> dict:
    """Conduct research — aggregate ALL web data first, then ONE LLM call."""
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
            topics = list(set(topics + existing.get("topics", [])))

        if search_adapter is None:
            search_adapter = SearchAdapter()

        # ── Step 1: gather ALL raw search data in parallel ──
        search_tasks = []
        search_keys = []

        if focus in ("company", "all") or (query and not focus):
            search_tasks.append(_raw_search(f"{query} company overview funding culture tech stack hiring", search_adapter))
            search_keys.append("company")
            search_tasks.append(_fetch_github_org_data(query))
            search_keys.append("github")

        if focus == "interview-prep" or "interview" in query.lower():
            q = f"{query} interview questions tips preparation"
            if topics:
                q += f" {' '.join(topics[:3])}"
            search_tasks.append(_raw_search(q, search_adapter))
            search_keys.append("interview")

        if focus == "market" or "trend" in query.lower():
            mq = f"{' '.join(topics[:3])} job market demand trends 2026" if topics else "market trends tech hiring demand"
            search_tasks.append(_raw_search(mq, search_adapter))
            search_keys.append("market")

        if focus == "skills":
            sq = f"{' '.join(topics[:3])} skill demand trending 2026" if topics else "most in-demand tech skills 2026"
            search_tasks.append(_raw_search(sq, search_adapter))
            search_keys.append("skills")

        raw_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        gathered: dict = {}
        for key, val in zip(search_keys, raw_results):
            gathered[key] = val if not isinstance(val, Exception) else None

        # ── Step 2: single LLM call with all gathered data ──
        results = await _synthesize_all(query, topics, focus, gathered)

        # ── Step 3: persist to memory ──
        await memory_service.set_memory(
            user_id,
            f"research_{datetime.now(UTC).timestamp()}",
            {"query": query, "topics": topics, "results": results, "timestamp": datetime.now(UTC).isoformat()},
            weight=MEMORY_WEIGHT_HIGH,
        )
        await memory_service.set_memory(
            user_id, "research_topics",
            {"topics": topics, "last_query": query},
            weight=MEMORY_WEIGHT_MEDIUM,
        )
        for topic in topics:
            await _store_research_embedding(user_id, agent_memory, topic, results)

        sections = []
        if results.get("company_info"):
            c = results["company_info"]
            sections.append(f"🏢 {c.get('name', 'Company')} — {c.get('industry', 'Tech')}")
            sections.append(c.get("summary", ""))
        if results.get("interview_insights"):
            ins = results["interview_insights"]
            sections.append(f"🎙️ Interview Tips: {ins.get('tips', '')}")
        if results.get("market_trends"):
            sections.append(f"📈 Market: {results['market_trends'].get('outlook', '')}")
        if results.get("skill_analysis"):
            sections.append(f"🛠️ Skills: {results['skill_analysis'].get('insight', '')}")

        return {
            "results": results,
            "summary": "\n\n".join(sections) or "Research complete.",
            "topics": topics,
            "message": f"Research complete on {len(topics)} topics",
        }

    except Exception as e:
        logger.error("Research failed for user %s: %s", user_id, str(e))
        raise


async def _raw_search(query: str, search_adapter: SearchAdapter) -> str:
    """Return concatenated snippets from web search — no LLM."""
    try:
        results = await search_adapter.search_research(query, limit=5)
        if not results:
            return ""
        return " ".join(r.get("snippet", "") + " " + r.get("title", "") for r in results if r.get("snippet") or r.get("title"))
    except Exception as e:
        logger.debug("Search failed for '%s': %s", query, e)
        return ""


async def _synthesize_all(query: str, topics: list, focus: str, gathered: dict) -> dict:
    """ONE LLM call that synthesizes all gathered search data into structured JSON."""
    llm = get_completion_llm(temperature=LLM_TEMPERATURE_PRECISE, preferred_provider=LLM_PROVIDER_RESEARCH)
    if not llm:
        return _fallback_all(query, topics, focus, gathered)

    company_snippets = gathered.get("company", "") or ""
    github_data = gathered.get("github")
    interview_snippets = gathered.get("interview", "") or ""
    market_snippets = gathered.get("market", "") or ""
    skills_snippets = gathered.get("skills", "") or ""

    github_str = ""
    if github_data and isinstance(github_data, dict):
        github_str = (
            f"\nGITHUB ORG DATA: {github_data.get('name')} | "
            f"Repos: {github_data.get('public_repos')} | "
            f"Languages: {', '.join(github_data.get('languages', []))} | "
            f"Top repos: {', '.join(github_data.get('top_repos', []))}"
        )

    sections_needed = []
    if company_snippets or github_str:
        sections_needed.append('"company_info": {name, industry, stage, funding, culture, tech_stack (list), hiring_trend, interview_process (list), summary}')
    if interview_snippets:
        sections_needed.append('"interview_insights": {focus_areas (list), common_questions (list of 5), tips, recommended_prep (list of 3)}')
    if market_snippets:
        sections_needed.append('"market_trends": {outlook, trending_roles (list of 3), salary_range, growth_areas (list), suggestions (list of 3)}')
    if skills_snippets:
        sections_needed.append('"skill_analysis": {insight, skill_demand_map (dict skill→level), recommended_skills (list of 3), learning_resources (list of 3)}')

    if not sections_needed:
        return _fallback_all(query, topics, focus, gathered)

    prompt = (
        f"You are an expert career research analyst. Synthesize ALL the following web search data about '{query}' "
        f"into a single structured JSON response. Output ONLY valid JSON, no markdown fences.\n\n"
    )
    if company_snippets:
        prompt += f"COMPANY SEARCH DATA:\n{company_snippets[:1500]}\n{github_str}\n\n"
    if interview_snippets:
        prompt += f"INTERVIEW SEARCH DATA:\n{interview_snippets[:800]}\n\n"
    if market_snippets:
        prompt += f"MARKET SEARCH DATA:\n{market_snippets[:800]}\n\n"
    if skills_snippets:
        prompt += f"SKILLS SEARCH DATA:\n{skills_snippets[:800]}\n\n"
    prompt += f"Return a JSON object with these keys:\n" + "\n".join(f"- {s}" for s in sections_needed)

    try:
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        data = json.loads(strip_json_fences(response.content))
        return data
    except Exception as e:
        logger.warning("LLM synthesis failed: %s — using fallback", e)
        return _fallback_all(query, topics, focus, gathered)


def _fallback_all(query: str, topics: list, focus: str, gathered: dict) -> dict:
    company_snippets = gathered.get("company", "") or ""
    github_data = gathered.get("github")
    result = {}
    if company_snippets or focus == "company":
        result["company_info"] = _fallback_company_info(query, company_snippets, github_data)
    if focus == "interview-prep" or "interview" in query.lower():
        result["interview_insights"] = _fallback_interview_insights(query, topics, gathered.get("interview", "") or "")
    if focus == "market" or "trend" in query.lower():
        result["market_trends"] = _fallback_market_intelligence(topics, gathered.get("market", "") or "")
    if focus == "skills":
        result["skill_analysis"] = _fallback_skill_insights(topics, gathered.get("skills", "") or "")
    return result


async def _fetch_github_org_data(company_name: str) -> dict | None:
    if not company_name:
        return None
    org_name = re.sub(r"[^a-zA-Z0-9-]", "", company_name.lower().replace(" ", ""))
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
                repos, languages, stars = [], {}, 0
                if repos_res.status_code == 200:
                    for repo in repos_res.json():
                        stars += repo.get("stargazers_count", 0)
                        lang = repo.get("language")
                        if lang:
                            languages[lang] = languages.get(lang, 0) + 1
                        repos.append({"name": repo.get("name"), "stars": repo.get("stargazers_count", 0), "language": lang})
                sorted_langs = [l for l, _ in sorted(languages.items(), key=lambda x: x[1], reverse=True)]
                return {
                    "login": org_data.get("login"),
                    "name": org_data.get("name"),
                    "description": org_data.get("description"),
                    "public_repos": org_data.get("public_repos", 0),
                    "languages": sorted_langs[:5],
                    "total_stars": stars,
                    "top_repos": [r["name"] for r in sorted(repos, key=lambda x: x["stars"], reverse=True)[:3]],
                }
    except Exception as e:
        logger.warning("GitHub org fetch failed for %s: %s", company_name, e)
    return None


def _fallback_company_info(company: str, combined: str = "", github_data: dict | None = None) -> dict:
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
    tech_stack = ["Python", "TypeScript", "React", "AWS", "PostgreSQL"]
    if github_data and github_data.get("languages"):
        tech_stack = [t.title() for t in github_data["languages"]]
    return {
        "name": company or "Tech Company",
        "industry": industry,
        "stage": "Growth-stage startup",
        "funding": funding,
        "culture": "Fast-paced, innovation-driven",
        "tech_stack": tech_stack,
        "hiring_trend": "Actively hiring" if re.search(r"(hiring|jobs|careers)", combined_lower) else "Information not available",
        "interview_process": ["Recruiter screen", "Technical screen", "On-site / final round", "Offer"],
        "summary": combined[:400] or f"{company} is actively building its engineering team.",
    }


def _fallback_interview_insights(role: str, skills: list, snippets: str = "") -> dict:
    return {
        "focus_areas": skills or ["Technical fundamentals", "System design", "Behavioral stories"],
        "common_questions": [
            "Tell me about a project where you demonstrated technical leadership.",
            "Describe a time you faced a challenging bug and how you resolved it.",
            "How do you approach designing a scalable system?",
            "Explain a technical concept to a non-technical stakeholder.",
            "Walk me through your approach to debugging a production issue.",
        ],
        "tips": snippets[:200] or "Prepare 2-3 strong STAR-format stories. Review system design fundamentals.",
        "recommended_prep": [
            "Review core data structures and algorithms",
            f"Practice problems related to {', '.join(skills[:3])}" if skills else "Practice coding problems",
            "Prepare questions to ask the interviewer",
        ],
    }


def _fallback_market_intelligence(skills: list, snippets: str = "") -> dict:
    return {
        "outlook": snippets[:200] or (f"Strong demand for {' and '.join(skills[:2])} skills." if skills else "Strong demand for engineering talent."),
        "trending_roles": ["AI/ML Engineer", "Full-stack Developer", "Developer Experience Engineer"],
        "salary_range": "$120K - $200K+ (depending on location and experience)",
        "growth_areas": ["AI safety", "Developer tools", "Fintech", "Climate tech"],
        "suggestions": ["Focus on AI-integrated projects", "Contribute to open-source", "Build strong online presence"],
    }


def _fallback_skill_insights(skills: list, snippets: str = "") -> dict:
    return {
        "insight": snippets[:200] or (f"Your skills in {', '.join(skills[:3])} are in high demand." if skills else "Current market shows strong tech demand."),
        "skill_demand_map": {s: "high" for s in skills},
        "recommended_skills": ["System Design", "Cloud Architecture", "AI/ML Integration"],
        "learning_resources": ["System Design Interview — Alex Xu", "CS231n (Stanford)", "Building LLM Applications (DeepLearning.AI)"],
    }


async def _store_research_embedding(user_id: str, agent_memory: AgentMemory, topic: str, results: dict) -> None:
    try:
        text = f"Research on {topic}: {str(results)[:2000]}"
        vector = await get_text_embedding(text)
        agent_memory.store_vector(
            collection="research_notes", text=text, vector=vector,
            metadata={"topic": topic, "user_id": user_id, "type": "research"},
        )
    except Exception as e:
        logger.debug("Failed to store research embedding: %s", e)


async def retrieve_research_context(user_id: str, query: str, limit: int = 3) -> str:
    try:
        agent_memory = AgentMemory(user_id)
        query_vector = await get_text_embedding(query)
        return agent_memory.get_relevant_context(query_vector, limit=limit)
    except Exception as e:
        logger.debug("Failed to retrieve research context: %s", e)
        return "Research context unavailable."
