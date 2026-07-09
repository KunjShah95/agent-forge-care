"""
Shared enrichment context builder — eliminates duplicated memory fetch + context-building
across all 4 agent functions that consume GitHub and portfolio scrape data.

Provides a single async function that:
1. Fetches github_skills_analysis and portfolio_scrape from memory
2. Merges detected skills into the caller's all_skills list (in-place)
3. Returns formatted context strings and extracted data for fallback templates

Gracefully degrades: returns empty fields when memory data is unavailable.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import MemoryService

logger = logging.getLogger("agentforge.agents.enrichment")


class EnrichmentData:
    """Container for enrichment context data extracted from memory."""

    __slots__ = (
        "portfolio_context",
        "github_context",
        "pf_projects",
        "pf_experience",
        "github_skills",
        "github_projects",
    )

    def __init__(
        self,
        portfolio_context: str = "",
        github_context: str = "",
        pf_projects: list[str] | None = None,
        pf_experience: list[str] | None = None,
        github_skills: list[str] | None = None,
        github_projects: list[str] | None = None,
    ):
        self.portfolio_context = portfolio_context
        self.github_context = github_context
        self.pf_projects = pf_projects or []
        self.pf_experience = pf_experience or []
        self.github_skills = github_skills or []
        self.github_projects = github_projects or []


def _merge_skills(all_skills: list[str], new_skills: list[str]) -> None:
    """Merge new skills into all_skills in-place, deduplicating case-insensitively."""
    for skill in new_skills:
        skill_lower = skill.lower()
        if not any(s.lower() == skill_lower for s in all_skills):
            all_skills.append(skill)


def _build_portfolio_context(portfolio_data: dict) -> tuple[str, list[str], list[str]]:
    """
    Build the PORTFOLIO EVIDENCE context string from scraped portfolio data.

    Returns (context_string, project_names, experience_entries).
    """
    pf_skills: list[str] = portfolio_data.get("skills", [])
    pf_technologies: list[str] = portfolio_data.get("technologies_detected", [])
    pf_projects: list[str] = portfolio_data.get("projects", []) or []
    pf_experience: list[str] = portfolio_data.get("experience", []) or []
    pf_summary: str = portfolio_data.get("summary", "") or ""
    pf_role: str | None = portfolio_data.get("role")

    lines: list[str] = []
    if pf_summary:
        lines.append(f"PORTFOLIO SUMMARY: {pf_summary}")
    if pf_role:
        lines.append(f"PORTFOLIO ROLE: {pf_role}")
    if pf_skills:
        lines.append(f"PORTFOLIO SKILLS: {', '.join(pf_skills)}")
    if pf_technologies:
        lines.append(f"PORTFOLIO TECHNOLOGIES: {', '.join(pf_technologies)}")
    if pf_projects:
        lines.append("PORTFOLIO PROJECTS:")
        for p in pf_projects[:5]:
            lines.append(f"  - {p}")
    if pf_experience:
        lines.append("PORTFOLIO EXPERIENCE:")
        for e in pf_experience[:3]:
            lines.append(f"  - {e}")

    return "\n".join(lines), pf_projects, pf_experience


def _build_github_context(
    github_analysis: dict,
    *,
    include_raw_repos: bool = False,
    github_raw: dict | None = None,
) -> str:
    """
    Build the GITHUB EVIDENCE context string from analyzed GitHub data.

    When include_raw_repos is True, also appends top starred repos
    from the raw GitHub profile data.
    """
    gh_skills: list[str] = github_analysis.get("skills", [])
    gh_langs: list[str] = github_analysis.get("primary_languages", [])
    gh_projects: list[str] = github_analysis.get("project_highlights", [])
    gh_exp: str = github_analysis.get("experience_level", "") or ""
    gh_summary: str = github_analysis.get("summary", "") or ""

    lines: list[str] = []
    if gh_summary:
        lines.append(f"GITHUB PROFILE SUMMARY: {gh_summary}")
    if gh_exp:
        lines.append(f"INFERRED EXPERIENCE LEVEL: {gh_exp}")
    if gh_langs:
        lines.append(f"GITHUB LANGUAGES: {', '.join(gh_langs)}")
    if gh_projects:
        lines.append("GITHUB PROJECTS:")
        for p in gh_projects[:5]:
            lines.append(f"  - {p}")
    if gh_skills:
        lines.append(f"GITHUB-INFERRED SKILLS: {', '.join(gh_skills)}")

    # Append raw repo stats when requested (tailor_resume uses this)
    if include_raw_repos and github_raw and isinstance(github_raw, dict):
        repos = github_raw.get("repositories", [])
        if repos:
            top_repos = sorted(
                [r for r in repos if not r.get("is_fork")],
                key=lambda r: r.get("stars", 0),
                reverse=True,
            )[:5]
            if top_repos:
                lines.append("TOP REPOS (STARRED):")
                for r in top_repos:
                    desc = (r.get("description", "") or "")[:100]
                    lines.append(f"  - {r['name']} (⭐{r.get('stars', 0)}, {r.get('language', 'N/A')}): {desc}")

    return "\n".join(lines)


async def build_enrichment_context(
    db: AsyncSession,
    user_id: str,
    all_skills: list[str],
    *,
    include_raw_repos: bool = False,
) -> EnrichmentData:
    """
    Fetch GitHub skills analysis and portfolio scrape data from memory,
    merge detected skills into *all_skills* (in-place), and return
    formatted context strings + extracted data for fallback templates.

    Parameters
    ----------
    db : AsyncSession
        Database session for memory lookups.
    user_id : str
        User identifier for scoping memory entries.
    all_skills : list[str]
        Mutable list of skills. Will be extended with any skills detected
        from GitHub or portfolio data (deduplicated case-insensitively).
    include_raw_repos : bool
        If True, also fetches ``github_profile_raw`` and includes top
        starred repo details in the GitHub context string. Used by
        ``tailor_resume()`` for richer resume-tailoring context.

    Returns
    -------
    EnrichmentData
        Container with ``portfolio_context``, ``github_context``,
        ``pf_projects``, ``pf_experience``, ``github_skills``, and
        ``github_projects``. All fields are safe to use — they will
        be empty when no enrichment data exists.
    """
    memory_service = MemoryService(db)

    portfolio_context = ""
    github_context = ""
    pf_projects: list[str] = []
    pf_experience: list[str] = []
    github_skills: list[str] = []
    github_projects: list[str] = []

    try:
        # ── Portfolio ──
        portfolio_data: Any = await memory_service.get_memory(user_id, "portfolio_scrape")
        if portfolio_data and isinstance(portfolio_data, dict) and "error" not in portfolio_data:
            # Merge portfolio-detected skills (both explicit + tech keywords)
            pf_skills_raw = portfolio_data.get("skills", [])
            pf_techs_raw = portfolio_data.get("technologies_detected", [])
            _merge_skills(all_skills, (pf_skills_raw or []) + (pf_techs_raw or []))

            portfolio_context, pf_projects, pf_experience = _build_portfolio_context(portfolio_data)

        # ── GitHub ──
        github_raw = None
        if include_raw_repos:
            github_raw = await memory_service.get_memory(user_id, "github_profile_raw")

        github_analysis: Any = await memory_service.get_memory(user_id, "github_skills_analysis")
        if github_analysis and isinstance(github_analysis, dict) and "error" not in github_analysis:
            gh_skills_raw: list[str] = github_analysis.get("skills", [])
            gh_projects_raw: list[str] = github_analysis.get("project_highlights", [])

            _merge_skills(all_skills, gh_skills_raw)
            github_skills = gh_skills_raw
            github_projects = [str(p) for p in (gh_projects_raw or []) if p]

            github_context = _build_github_context(
                github_analysis,
                include_raw_repos=include_raw_repos,
                github_raw=github_raw,
            )

    except Exception as e:
        logger.debug("Failed to fetch enrichment memory for user %s: %s", user_id, e)

    return EnrichmentData(
        portfolio_context=portfolio_context,
        github_context=github_context,
        pf_projects=pf_projects,
        pf_experience=pf_experience,
        github_skills=github_skills,
        github_projects=github_projects,
    )
