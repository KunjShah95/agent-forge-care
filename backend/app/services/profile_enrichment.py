"""
Profile Enrichment Service — inline (non-RQ) profile enrichment.

Runs GitHub scraping, portfolio scraping, and social-link auto-discovery
directly in the request context without relying on Redis/RQ background workers.
Falls back gracefully if any source is unavailable.

All results are stored in MemoryService for consumption by all agents.
"""

import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import MemoryService
from app.services.profile_scraper import (
    analyze_commit_history,
    analyze_github_for_skills,
    scrape_github_commits,
    scrape_github_contributions,
    scrape_github_oss_contributions,
    scrape_github_profile,
    scrape_portfolio,
)

logger = logging.getLogger("agentforge.services.profile_enrichment")


class SocialDiscoveryResult:
    """Results from social link auto-discovery."""

    def __init__(
        self,
        blog_url: str | None = None,
        twitter_handle: str | None = None,
        linkedin_url: str | None = None,
        portfolio_url: str | None = None,
        email: str | None = None,
        company: str | None = None,
        location: str | None = None,
    ):
        self.blog_url = blog_url
        self.twitter_handle = twitter_handle
        self.linkedin_url = linkedin_url
        self.portfolio_url = portfolio_url
        self.email = email
        self.company = company
        self.location = location

    def to_dict(self) -> dict:
        return {
            "blog_url": self.blog_url,
            "twitter_handle": self.twitter_handle,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
            "email": self.email,
            "company": self.company,
            "location": self.location,
        }


class ProfileEnrichmentResult:
    """Container for all enrichment results."""

    def __init__(
        self,
        github_profile: dict | None = None,
        github_analysis: dict | None = None,
        portfolio_data: dict | None = None,
        social_links: SocialDiscoveryResult | None = None,
        discovered_skills: list[str] | None = None,
    ):
        self.github_profile = github_profile or {}
        self.github_analysis = github_analysis or {}
        self.portfolio_data = portfolio_data or {}
        self.social_links = social_links or SocialDiscoveryResult()
        self.discovered_skills = discovered_skills or []

    def to_dict(self) -> dict:
        return {
            "github_profile": self.github_profile,
            "github_analysis": self.github_analysis,
            "portfolio_data": self.portfolio_data,
            "social_links": self.social_links.to_dict(),
            "discovered_skills": self.discovered_skills,
        }

    @property
    def is_github_loaded(self) -> bool:
        return bool(self.github_profile and "error" not in self.github_profile)

    @property
    def is_portfolio_loaded(self) -> bool:
        return bool(self.portfolio_data and "error" not in self.portfolio_data)


async def enrich_github_profile(
    github_url: str,
    db: AsyncSession,
    user_id: str,
) -> ProfileEnrichmentResult:
    """Scrape GitHub profile, auto-discover social links, and store in memory.

    Steps:
    1. Scrape GitHub profile (repos, langs, stars, bio, etc.)
    2. Analyze GitHub data for skills, experience level, project highlights
    3. Auto-discover social links from GitHub profile (blog, Twitter, etc.)
    4. Store all results in MemoryService
    """
    if not github_url or not github_url.startswith(("http://", "https://")):
        return ProfileEnrichmentResult()

    memory_service = MemoryService(db)
    import asyncio

    # ── Fire all GitHub data scrapers in parallel ──
    # Profile + commits + contributions + OSS are all independent API calls.
    # Running them concurrently instead of sequentially reduces total wall time
    # from sum(latencies) to max(latency).
    profile_task = scrape_github_profile(github_url)
    commits_task = scrape_github_commits(github_url)
    contribs_task = scrape_github_contributions(github_url)
    oss_task = scrape_github_oss_contributions(github_url)

    raw_data, commit_data, contribution_data, oss_data = await asyncio.gather(
        profile_task, commits_task, contribs_task, oss_task,
        return_exceptions=True,
    )

    # ── Handle profile result ──
    if isinstance(raw_data, BaseException):
        logger.warning("GitHub scrape exception for %s: %s", github_url, raw_data)
        await memory_service.set_memory(
            user_id, "github_profile_raw", {"error": str(raw_data)}, weight=0.5
        )
        return ProfileEnrichmentResult(github_profile={"error": str(raw_data)})

    if "error" in raw_data:
        logger.warning("GitHub scrape failed for %s: %s", github_url, raw_data["error"])
        await memory_service.set_memory(
            user_id, "github_profile_raw", raw_data, weight=0.5
        )
        return ProfileEnrichmentResult(github_profile=raw_data)

    # Store raw data
    await memory_service.set_memory(
        user_id, "github_profile_raw", raw_data, weight=0.8
    )

    # Analyze for skills
    analysis = await analyze_github_for_skills(raw_data)
    await memory_service.set_memory(
        user_id, "github_skills_analysis", analysis, weight=0.9
    )

    # ── Store commit history (if available) ──
    if isinstance(commit_data, dict) and "error" not in commit_data:
        await memory_service.set_memory(
            user_id, "github_commit_history", commit_data, weight=0.8
        )

    # ── Store contribution graph (if available) ──
    if isinstance(contribution_data, dict) and "error" not in contribution_data:
        await memory_service.set_memory(
            user_id, "github_contributions", contribution_data, weight=0.8
        )

    # ── Store open-source contributions (if available) ──
    if isinstance(oss_data, dict) and "error" not in oss_data:
        await memory_service.set_memory(
            user_id, "github_oss_contributions", oss_data, weight=0.8
        )

    # ── Analyze commit history patterns ──
    commit_data_ok = isinstance(commit_data, dict) and "error" not in commit_data
    contrib_data_ok = isinstance(contribution_data, dict) and "error" not in contribution_data
    oss_data_ok = isinstance(oss_data, dict) and "error" not in oss_data

    commit_data = commit_data if commit_data_ok else None
    contribution_data = contribution_data if contrib_data_ok else None
    oss_data = oss_data if oss_data_ok else None

    commit_analysis = await analyze_commit_history(
        commit_data=commit_data,
        contribution_data=contribution_data,
        oss_data=oss_data,
    )
    if "error" not in commit_analysis:
        await memory_service.set_memory(
            user_id, "github_commit_analysis", commit_analysis, weight=0.9
        )

    # Auto-discover social links from GitHub profile
    social = _discover_socials_from_github(raw_data)

    # Check if GitHub blog URL is actually a LinkedIn URL
    blog_url = raw_data.get("profile", {}).get("blog") or ""
    if "linkedin.com/in/" in blog_url.lower() and not social.linkedin_url:
        import re
        li_match = re.search(
            r"(https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+)",
            blog_url,
            re.IGNORECASE,
        )
        if li_match:
            social.linkedin_url = li_match.group(1)
            await memory_service.set_memory(
                user_id,
                "linkedin_url_discovered",
                {"url": li_match.group(1), "source": "github_profile_blog"},
                weight=0.7,
            )

    portfolio_url = social.portfolio_url or (
        blog_url if blog_url and "github.com" not in blog_url.lower() else None
    )
    if portfolio_url:
        await memory_service.set_memory(
            user_id,
            "portfolio_url_discovered",
            {"url": portfolio_url, "source": "github_profile"},
            weight=0.7,
        )

    # Merge discovered skills
    discovered_skills = analysis.get("skills", [])
    if isinstance(discovered_skills, list):
        discovered_skills = [s for s in discovered_skills if isinstance(s, str)]

    return ProfileEnrichmentResult(
        github_profile=raw_data,
        github_analysis=analysis,
        social_links=social,
        discovered_skills=discovered_skills,
    )


async def enrich_portfolio(
    portfolio_url: str,
    db: AsyncSession,
    user_id: str,
) -> ProfileEnrichmentResult:
    """Scrape portfolio website and store in memory.

    Steps:
    1. Scrape portfolio page (projects, skills, experience)
    2. Store in MemoryService
    """
    if not portfolio_url or not portfolio_url.startswith(("http://", "https://")):
        return ProfileEnrichmentResult()

    memory_service = MemoryService(db)
    portfolio_data = await scrape_portfolio(portfolio_url)

    if "error" in portfolio_data:
        logger.warning(
            "Portfolio scrape failed for %s: %s",
            portfolio_url,
            portfolio_data["error"],
        )

    await memory_service.set_memory(
        user_id, "portfolio_scrape", portfolio_data, weight=0.8
    )

    discovered_skills = []
    pf_skills: list = portfolio_data.get("skills", []) or []
    pf_techs: list = portfolio_data.get("technologies_detected", []) or []
    discovered_skills.extend(
        s for s in pf_skills + pf_techs if isinstance(s, str)
    )

    return ProfileEnrichmentResult(
        portfolio_data=portfolio_data, discovered_skills=discovered_skills
    )


async def enrich_all(
    user_id: str,
    db: AsyncSession,
    github_url: str | None = None,
    portfolio_url: str | None = None,
    linkedin_url: str | None = None,
) -> dict:
    """Run full enrichment: GitHub scraping + portfolio scraping + social discovery.

    This is the primary entry point. Runs all sources in parallel and returns
    merged results. Stores everything in MemoryService.

    Returns a dict suitable for API response.
    """
    import asyncio

    tasks = {}

    if github_url:
        tasks["github"] = enrich_github_profile(github_url, db, user_id)
    if portfolio_url:
        tasks["portfolio"] = enrich_portfolio(portfolio_url, db, user_id)
    if not tasks:
        return {
            "status": "skipped",
            "message": "No URLs provided for enrichment.",
            "social_links": {},
            "discovered_skills": [],
        }

    results = await asyncio.gather(*tasks.values())

    merged = ProfileEnrichmentResult()
    all_skills: list[str] = []
    final_social = SocialDiscoveryResult()
    final_social.linkedin_url = linkedin_url or None

    for result in results:
        if isinstance(result, ProfileEnrichmentResult):
            if result.github_profile:
                merged.github_profile = result.github_profile
                merged.github_analysis = result.github_analysis
            if result.portfolio_data:
                merged.portfolio_data = result.portfolio_data
            if result.social_links:
                s = result.social_links
                final_social.blog_url = final_social.blog_url or s.blog_url
                final_social.twitter_handle = (
                    final_social.twitter_handle or s.twitter_handle
                )
                final_social.linkedin_url = final_social.linkedin_url or s.linkedin_url
                final_social.portfolio_url = (
                    final_social.portfolio_url or s.portfolio_url
                )
                final_social.email = final_social.email or s.email
                final_social.company = final_social.company or s.company
                final_social.location = final_social.location or s.location
            all_skills.extend(result.discovered_skills)

    merged.social_links = final_social
    merged.discovered_skills = list(set(all_skills))

    # Store combined social discovery in memory
    if any(vars(final_social).values()):
        memory_service = MemoryService(db)
        await memory_service.set_memory(
            user_id,
            "social_links_discovered",
            final_social.to_dict(),
            weight=0.7,
        )

    return merged.to_dict()


def _discover_socials_from_github(github_data: dict) -> SocialDiscoveryResult:
    """Extract social links from GitHub profile data.

    GitHub profile includes: blog, twitter_username, email, company, location.
    These are available through the GitHub API and can be used to auto-discover
    additional profile links.
    """
    profile = github_data.get("profile", {}) or {}

    blog_url = profile.get("blog") or None
    twitter_handle = profile.get("twitter_username") or None
    email = profile.get("email") or None
    company = profile.get("company") or None
    location = profile.get("location") or None

    # Try to derive a portfolio URL from the blog field
    portfolio_url = None
    if blog_url and blog_url.startswith(("http://", "https://")):
        if "github.com" not in blog_url.lower():
            portfolio_url = blog_url

    # Try to derive LinkedIn URL from company
    linkedin_url = None

    return SocialDiscoveryResult(
        blog_url=blog_url,
        twitter_handle=twitter_handle,
        portfolio_url=portfolio_url,
        email=email,
        company=company,
        location=location,
        linkedin_url=linkedin_url,
    )


# ─── DeveloperProfile Composite ────────────────────────────────


async def build_developer_profile(
    github_url: str,
    db: AsyncSession,
    user_id: str,
) -> dict:
    """
    Build a complete composite DeveloperProfile from all GitHub data sources.

    Orchestrates all scrapers in parallel and returns a single merged dict
    ready for the API response. Each source has graceful degradation:
    if one scraper fails, the others still contribute.

    Returns a flat dict matching the DeveloperProfile schema.
    """
    import asyncio
    from app.services.profile_scraper import (
        scrape_github_profile,
        analyze_github_for_skills,
        scrape_github_commits,
        scrape_github_contributions,
        scrape_github_oss_contributions,
        analyze_commit_history,
    )

    base = {
        "username": "",
        "profile_url": github_url or "",
        "avatar_url": None,
        "name": None,
        "bio": None,
        "location": None,
        "company": None,
        "email": None,
        "twitter_handle": None,
        "blog_url": None,
        "followers": 0,
        "following": 0,
        "public_repos": 0,
        "total_stars": 0,
        "languages": {},
        "repositories": [],
        "skills": {},
        "commit_history": None,
        "contributions": None,
        "oss_contributions": None,
        "commit_analysis": None,
        "data_completeness": 0,
        "errors": [],
    }

    if not github_url:
        base["errors"].append("No GitHub URL provided")
        return base

    # ── Fire all scrapers in parallel ──
    profile_task = scrape_github_profile(github_url)
    commits_task = scrape_github_commits(github_url)
    contribs_task = scrape_github_contributions(github_url)
    oss_task = scrape_github_oss_contributions(github_url)

    profile_result, commits_result, contribs_result, oss_result = await asyncio.gather(
        profile_task, commits_task, contribs_task, oss_task,
        return_exceptions=True,
    )

    sources_loaded = 0
    total_sources = 4

    # ── Process profile ──
    if isinstance(profile_result, dict) and "error" not in profile_result:
        sources_loaded += 1
        prof = profile_result.get("profile", {}) or {}
        base.update({
            "username": profile_result.get("username", ""),
            "avatar_url": prof.get("avatar_url"),
            "name": prof.get("name"),
            "bio": prof.get("bio"),
            "location": prof.get("location"),
            "company": prof.get("company"),
            "email": prof.get("email"),
            "twitter_handle": prof.get("twitter_username"),
            "blog_url": prof.get("blog"),
            "followers": prof.get("followers", 0),
            "following": prof.get("following", 0),
            "public_repos": prof.get("public_repos", 0),
            "total_stars": profile_result.get("total_stars", 0),
            "languages": profile_result.get("languages", {}),
        })

        # Transform repositories
        repos_raw = profile_result.get("repositories", [])
        base["repositories"] = [
            {
                "name": r.get("name", ""),
                "full_name": r.get("full_name", ""),
                "description": r.get("description"),
                "language": r.get("language"),
                "stars": r.get("stars", 0),
                "forks": r.get("forks", 0),
                "topics": r.get("topics", []),
                "html_url": r.get("html_url", ""),
                "homepage": r.get("homepage"),
                "updated_at": r.get("updated_at"),
            }
            for r in repos_raw
        ][:30]

        # Analyze for skills
        analysis = await analyze_github_for_skills(profile_result)
        if isinstance(analysis, dict) and "error" not in analysis:
            base["skills"] = {
                "skills": analysis.get("skills", []),
                "primary_languages": analysis.get("primary_languages", []),
                "project_highlights": analysis.get("project_highlights", []),
                "experience_level": analysis.get("experience_level", "unknown"),
                "interests": analysis.get("interests", []),
                "professional_summary": analysis.get("summary", ""),
            }
    elif isinstance(profile_result, BaseException):
        base["errors"].append(f"Profile scraping exception: {profile_result}")
    else:
        base["errors"].append(profile_result.get("error", "Profile scraping failed"))

    # ── Process commits ──
    if isinstance(commits_result, dict) and "error" not in commits_result:
        sources_loaded += 1
        base["commit_history"] = {
            "total_commits": commits_result.get("total_commits", 0),
            "total_unique_commits": commits_result.get("total_unique_commits", 0),
            "commits_by_repo": commits_result.get("commits_by_repo", {}),
            "commit_languages": commits_result.get("commit_languages", {}),
            "commit_frequency": {
                "by_day": commits_result.get("commit_frequency", {}).get("by_day", {}),
                "by_hour": commits_result.get("commit_frequency", {}).get("by_hour", {}),
                "by_day_of_week": commits_result.get("commit_frequency", {}).get("by_day_of_week", {}),
            },
            "average_commits_per_day": commits_result.get("average_commits_per_day", 0.0),
            "recent_events": commits_result.get("recent_events", []),
        }
    elif isinstance(commits_result, BaseException):
        base["errors"].append(f"Commit scraping exception: {commits_result}")
    else:
        base["errors"].append(commits_result.get("error", "Commit history failed"))

    # ── Process contributions ──
    if isinstance(contribs_result, dict) and "error" not in contribs_result:
        sources_loaded += 1
        base["contributions"] = {
            "total_contributions": contribs_result.get("total_contributions", 0),
            "current_streak": contribs_result.get("current_streak", 0),
            "longest_streak": contribs_result.get("longest_streak", 0),
            "top_contribution_months": contribs_result.get("top_contribution_months", []),
            "contribution_calendar": contribs_result.get("contribution_calendar", []),
        }
    elif isinstance(contribs_result, BaseException):
        base["errors"].append(f"Contribution scraping exception: {contribs_result}")
    else:
        base["errors"].append(contribs_result.get("error", "Contributions failed"))

    # ── Process OSS ──
    if isinstance(oss_result, dict) and "error" not in oss_result:
        sources_loaded += 1
        base["oss_contributions"] = {
            "total_prs": oss_result.get("total_prs", 0),
            "total_issues": oss_result.get("total_issues", 0),
            "pull_requests": oss_result.get("pull_requests", []),
            "repos_contributed_to": oss_result.get("repos_contributed_to", []),
            "summary": oss_result.get("summary", ""),
        }
    elif isinstance(oss_result, BaseException):
        base["errors"].append(f"OSS scraping exception: {oss_result}")
    else:
        base["errors"].append(oss_result.get("error", "OSS contributions failed"))

    # ── Run commit analysis if we have any data ──
    commit_data = commits_result if isinstance(commits_result, dict) and "error" not in commits_result else None
    contrib_data = contribs_result if isinstance(contribs_result, dict) and "error" not in contribs_result else None
    oss_data = oss_result if isinstance(oss_result, dict) and "error" not in oss_result else None

    if commit_data or contrib_data or oss_data:
        analysis_result = await analyze_commit_history(
            commit_data=commit_data,
            contribution_data=contrib_data,
            oss_data=oss_data,
        )
        if isinstance(analysis_result, dict) and "error" not in analysis_result:
            base["commit_analysis"] = {
                "coding_frequency": analysis_result.get("coding_frequency", "unknown"),
                "preferred_work_days": analysis_result.get("preferred_work_days", []),
                "commit_quality": analysis_result.get("commit_quality", "unknown"),
                "project_focus": analysis_result.get("project_focus", "unknown"),
                "oss_participation": analysis_result.get("oss_participation", "unknown"),
                "consistency_score": analysis_result.get("consistency_score", 0),
                "experience_indicators": analysis_result.get("experience_indicators", []),
                "summary": analysis_result.get("summary", ""),
            }

    # ── Compute data completeness ──
    base["data_completeness"] = round((sources_loaded / total_sources) * 100)

    # Store the composite profile in memory for agents
    await MemoryService(db).set_memory(
        user_id, "developer_profile_composite", base, weight=0.9,
    )

    return base
