"""
Discovery Agent handlers — profile discovery from name or email.

Given just a name or email address, this agent searches the web to discover:
- GitHub profile URL
- LinkedIn profile URL
- Twitter/X profile URL
- Personal portfolio / website URL
- Other social links (Dev.to, Medium, Hashnode, Stack Overflow, etc.)

Uses SearchAdapter's multi-source web search + LLM parsing to extract URLs.
Can optionally scrape found profiles for deeper enrichment.
"""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import strip_json_fences
from app.search.adapters import SearchAdapter
from app.services.memory_service import MemoryService
from app.services.model_manager import get_completion_llm
from app.services.profile_scraper import (
    analyze_github_for_skills,
    scrape_github_profile,
    scrape_portfolio,
)

logger = logging.getLogger("agentforge.agents.discovery.handlers")

# ─── Known Social Platforms ──────────────────────────────

SOCIAL_PLATFORMS = {
    "github": {"domain": "github.com", "icon": "🐙", "label": "GitHub"},
    "linkedin": {"domain": "linkedin.com", "icon": "💼", "label": "LinkedIn"},
    "twitter": {"domain": ["twitter.com", "x.com"], "icon": "🐦", "label": "Twitter/X"},
    "devto": {"domain": "dev.to", "icon": "📝", "label": "Dev.to"},
    "medium": {"domain": "medium.com", "icon": "✍️", "label": "Medium"},
    "hashnode": {"domain": "hashnode.com", "icon": "📓", "label": "Hashnode"},
    "stackoverflow": {"domain": "stackoverflow.com", "icon": "📚", "label": "Stack Overflow"},
    "dribbble": {"domain": "dribbble.com", "icon": "🎨", "label": "Dribbble"},
    "behance": {"domain": "behance.net", "icon": "🎯", "label": "Behance"},
    "youtube": {"domain": "youtube.com", "icon": "📺", "label": "YouTube"},
    "twitch": {"domain": "twitch.tv", "icon": "🎮", "label": "Twitch"},
    "mastodon": {"domain": "mastodon.social", "icon": "🦣", "label": "Mastodon"},
}

# ─── Search Queries ────────────────────────────────────────


def _build_search_queries(name: str, email: str | None = None) -> list[str]:
    """Build targeted search queries for discovering social profiles."""
    queries = []
    name_quoted = f'"{name}"' if " " in name else name

    # Platform-specific searches
    platforms = [
        ("github", f"{name_quoted} github profile"),
        ("linkedin", f"{name_quoted} linkedin profile"),
        ("twitter", f"{name_quoted} twitter OR x.com profile"),
        ("portfolio", f"{name_quoted} portfolio website personal site"),
        ("devto", f"{name_quoted} dev.to profile"),
        ("medium", f"{name_quoted} medium.com"),
        ("hashnode", f"{name_quoted} hashnode blog"),
        ("stackoverflow", f"{name_quoted} stackoverflow"),
    ]

    for platform_type, query in platforms:
        queries.append(query)

    # If email is provided, search for accounts linked to it
    if email:
        queries.append(f"{email} github profile")
        queries.append(f"{email} linkedin profile")
        queries.append(f"{email} about me portfolio")

    # General presence search
    queries.append(f"{name_quoted} developer engineer portfolio github linkedin")
    queries.append(f'{name_quoted} "about me" "software" developer')

    return queries


# ─── URL Extraction from Search Results ────────────────────


def _extract_profile_urls_from_results(
    results: list[dict],
    name_lower: str,
) -> dict[str, list[dict]]:
    """Extract and categorize profile URLs from search results.

    Returns dict mapping platform -> list of matched results.
    """
    found: dict[str, list[dict]] = {}
    seen_urls: set[str] = set()

    for platform, config in SOCIAL_PLATFORMS.items():
        domains = config["domain"] if isinstance(config["domain"], list) else [config["domain"]]
        found[platform] = []

        for r in results:
            url = (r.get("url") or r.get("apply_url") or "").lower().strip()
            title = (r.get("title") or "").lower()
            snippet = (r.get("snippet") or r.get("description") or "").lower()
            combined = f"{title} {snippet} {url}"

            matched_domain = any(d in url for d in domains)
            matched_name = name_lower in combined

            if matched_domain and matched_name and url not in seen_urls:
                seen_urls.add(url)
                found[platform].append(
                    {
                        "url": r.get("url") or r.get("apply_url") or "",
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet") or r.get("description") or "",
                        "confidence": "high" if (matched_name and matched_domain) else "medium",
                    }
                )

    return found


def _deduplicate_urls(found: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Deduplicate and prioritize URLs within each platform."""
    deduped = {}
    for platform, items in found.items():
        seen = set()
        unique = []
        for item in items:
            url = (item.get("url") or "").lower().strip().rstrip("/")
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(item)
        # Sort by confidence
        unique.sort(key=lambda x: 0 if x["confidence"] == "high" else 1)
        deduped[platform] = unique[:3]  # Max 3 per platform
    return deduped


# ─── LLM-Based Profile Extraction ──────────────────────────


async def _parse_results_with_llm(
    name: str,
    email: str | None,
    results: list[dict],
) -> dict[str, Any]:
    """Use LLM to intelligently extract profile URLs from search results.

    This handles the case where regex-based extraction misses profiles.
    """
    llm = get_completion_llm(temperature=0.3, preferred_provider="openai")
    if not llm:
        return {"profiles": {}, "profiles_text": ""}

    try:
        from langchain_core.messages import HumanMessage

        results_text = "\n".join(
            f"- [{r.get('title', 'Untitled')}]({r.get('url') or r.get('apply_url', '')})"
            f"\n  {r.get('snippet', '') or r.get('description', '')[:200]}"
            for r in results[:25]
        )

        email_context = f"Email: {email}" if email else "No email provided"

        prompt = f"""You are a social profile discovery expert. Given search results for a person's name,
extract all profile URLs you can find.

NAME: {name}
{email_context}

SEARCH RESULTS:
{results_text}

Return ONLY valid JSON with the following structure:
{{
    "profiles": {{
        "github": "full URL or null",
        "linkedin": "full URL or null",
        "twitter": "full URL or null",
        "portfolio": "full URL or null",
        "devto": "full URL or null",
        "medium": "full URL or null",
        "hashnode": "full URL or null",
        "stackoverflow": "full URL or null",
        "dribbble": "full URL or null",
        "youtube": "full URL or null"
    }},
    "confidence": "high" | "medium" | "low",
    "name_found": "the person's full name as found on profiles if different from input",
    "summary": "2-3 sentence summary of all profiles discovered"
}}

Rules:
- Only include URLs that clearly belong to a person named {name} (or very close match)
- For LinkedIn: must be linkedin.com/in/...
- For GitHub: must be github.com/username (not an org)
- For portfolio: must be a personal website, not a social platform
- Set confidence based on how certain you are these belong to this person
- Return null for platforms where no profile was found

No markdown, no explanations."""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        parsed = json.loads(strip_json_fences(content))

        if not isinstance(parsed, dict):
            return {"profiles": {}, "profiles_text": ""}

        profiles = parsed.get("profiles", {})
        # Filter out null/empty values
        clean_profiles = {k: v for k, v in profiles.items() if v and isinstance(v, str)}

        # Build text summary
        sections = []
        for platform, url in clean_profiles.items():
            icon = SOCIAL_PLATFORMS.get(platform, {}).get("icon", "🔗")
            label = SOCIAL_PLATFORMS.get(platform, {}).get("label", platform.title())
            sections.append(f"{icon} {label}: {url}")

        profiles_text = "\n".join(sections)

        return {
            "profiles": clean_profiles,
            "profiles_text": profiles_text,
            "confidence": parsed.get("confidence", "low"),
            "name_found": parsed.get("name_found"),
            "summary": parsed.get("summary", ""),
        }
    except Exception as e:
        logger.warning("LLM profile extraction failed: %s", e)
        return {"profiles": {}, "profiles_text": ""}


# ─── Profile Verification ──────────────────────────────────


async def _verify_github_profile(url: str) -> dict | None:
    """Verify a GitHub profile URL actually exists by making a HEAD request."""
    if not url:
        return None
    m = re.search(r"github\.com/([A-Za-z0-9_.-]+)", url)
    if not m:
        return None
    username = m.group(1)
    try:
        import httpx

        headers = {"User-Agent": "AgentForge-CareerOS"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://api.github.com/users/{username}",
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "username": username,
                    "name": data.get("name"),
                    "bio": data.get("bio"),
                    "public_repos": data.get("public_repos"),
                    "followers": data.get("followers"),
                    "verified": True,
                }
            return {"username": username, "verified": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.debug("GitHub verification failed for %s: %s", url, e)
        return {"username": username, "verified": False, "error": str(e)}


def _verify_linkedin_url(url: str) -> dict:
    """Verify a LinkedIn URL is valid by checking format."""
    if not url:
        return {"verified": False}
    m = re.search(r"linkedin\.com/in/([A-Za-z0-9_-]+)", url)
    if m:
        return {"profile_id": m.group(1), "verified": True}
    return {"verified": False}


async def _verify_portfolio_url(url: str) -> dict:
    """Verify a portfolio URL is reachable."""
    if not url:
        return {"verified": False}
    try:
        import httpx

        headers = {"User-Agent": "AgentForge-CareerOS"}
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            return {
                "url": url,
                "status_code": resp.status_code,
                "verified": resp.status_code < 400,
            }
    except Exception as e:
        return {"url": url, "verified": False, "error": str(e)}


# ─── Main Discovery Functions ───────────────────────────────


async def discover_profiles_from_name(
    name: str,
    db: AsyncSession,
    user_id: str,
    search_adapter: SearchAdapter | None = None,
    scrape_found: bool = False,
) -> dict:
    """Discover all social profiles for a person given their name.

    Args:
        name: Full name to search for (e.g. "John Doe")
        db: Database session
        user_id: User ID for storing results
        search_adapter: Optional SearchAdapter override
        scrape_found: If True, also scrape found profiles for enrichment

    Returns:
        dict with discovered profiles, verification status, and enrichment data
    """
    if not name or not isinstance(name, str) or len(name.strip()) < 2:
        return {
            "status": "error",
            "error": "Name must be a non-empty string with at least 2 characters",
            "profiles": {},
            "profiles_text": "",
            "confidence": None,
        }

    name = name.strip()
    name_lower = name.lower()

    if search_adapter is None:
        search_adapter = SearchAdapter()

    queries = _build_search_queries(name)

    # Search across all queries in parallel-ish
    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        try:
            results = await search_adapter.search_research(query, limit=10)
            for r in results:
                url = (r.get("url") or "").strip().lower()
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
        except Exception as e:
            logger.debug("Search query failed '%s': %s", query[:50], e)
            continue

    logger.info("Discovery for '%s': collected %d unique results from %d queries", name, len(all_results), len(queries))

    # Extract profiles using regex-based approach
    extracted = _extract_profile_urls_from_results(all_results, name_lower)
    extracted = _deduplicate_urls(extracted)

    # Build flat profiles dict (best URL per platform)
    flat_profiles: dict[str, str] = {}
    for platform, items in extracted.items():
        if items:
            flat_profiles[platform] = items[0]["url"]

    # Use LLM for deeper extraction
    llm_results = await _parse_results_with_llm(name, None, all_results)
    llm_profiles = llm_results.get("profiles", {})

    # Merge: LLM results override regex results (more accurate)
    for platform, url in llm_profiles.items():
        if url and isinstance(url, str):
            flat_profiles[platform] = url

    # Build text summary from discovered profiles
    profiles_text = llm_results.get("profiles_text", "")
    if not profiles_text and flat_profiles:
        sections = []
        for platform, url in flat_profiles.items():
            icon = SOCIAL_PLATFORMS.get(platform, {}).get("icon", "🔗")
            label = SOCIAL_PLATFORMS.get(platform, {}).get("label", platform.title())
            sections.append(f"{icon} {label}: {url}")
        profiles_text = "\n".join(sections)

    # Verify discovered profiles
    verification: dict[str, dict] = {}
    if "github" in flat_profiles:
        verification["github"] = await _verify_github_profile(flat_profiles["github"])
    if "linkedin" in flat_profiles:
        verification["linkedin"] = await _verify_linkedin_url(flat_profiles["linkedin"])
    if "portfolio" in flat_profiles:
        verification["portfolio"] = await _verify_portfolio_url(flat_profiles["portfolio"])

    # Store discovery results in memory
    try:
        memory_service = MemoryService(db)
        await memory_service.set_memory(
            user_id,
            "discovery_result",
            {
                "query": name,
                "query_type": "name",
                "profiles": flat_profiles,
                "verification": verification,
                "confidence": llm_results.get("confidence"),
                "discovered_at": datetime.now(UTC).isoformat(),
            },
            weight=0.8,
        )
    except Exception as e:
        logger.debug("Failed to store discovery result: %s", e)

    # Optionally scrape found profiles
    enrichment = {}
    if scrape_found:
        enrichment = await _scrape_discovered_profiles(
            flat_profiles, db, user_id
        )

    return {
        "status": "completed",
        "profiles": flat_profiles,
        "profiles_text": profiles_text,
        "confidence": llm_results.get("confidence", "low"),
        "name_found": llm_results.get("name_found"),
        "summary": llm_results.get(
            "summary",
            f"Discovered {len(flat_profiles)} profile(s) for {name}."
        ),
        "verification": verification,
        "enrichment": enrichment,
        "total_results_scanned": len(all_results),
    }


async def discover_profiles_from_email(
    email: str,
    db: AsyncSession,
    user_id: str,
    search_adapter: SearchAdapter | None = None,
    scrape_found: bool = False,
) -> dict:
    """Discover social profiles for a person given their email address.

    Uses the email to search for associated accounts and profiles.
    Falls back to name discovery if the email contains a name pattern.
    """
    if not email or not isinstance(email, str) or "@" not in email:
        return {
            "status": "error",
            "error": "A valid email address is required",
            "profiles": {},
        }

    email = email.strip().lower()
    name = _extract_name_from_email(email)

    if search_adapter is None:
        search_adapter = SearchAdapter()

    queries = _build_search_queries(name, email)

    # Also add email-specific queries
    email_local = email.split("@")[0]
    queries.append(f"{email} profile site:github.com OR site:linkedin.com OR site:twitter.com")
    queries.append(f"\"{email_local}\" developer engineer")
    queries.append(f"email \"{email}\" portfolio OR \"about me\" OR resume")

    # Reuse the name discovery logic with email context
    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        try:
            results = await search_adapter.search_research(query, limit=10)
            for r in results:
                url = (r.get("url") or "").strip().lower()
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
        except Exception as e:
            logger.debug("Email search query failed '%s': %s", query[:50], e)
            continue

    # Extract profiles using regex
    name_lower = name.lower()
    extracted = _extract_profile_urls_from_results(all_results, name_lower)
    extracted = _deduplicate_urls(extracted)

    flat_profiles: dict[str, str] = {}
    for platform, items in extracted.items():
        if items:
            flat_profiles[platform] = items[0]["url"]

    # Use LLM for better extraction
    llm_results = await _parse_results_with_llm(name, email, all_results)
    llm_profiles = llm_results.get("profiles", {})
    for platform, url in llm_profiles.items():
        if url and isinstance(url, str):
            flat_profiles[platform] = url

    # Verify
    verification: dict[str, dict] = {}
    if "github" in flat_profiles:
        verification["github"] = await _verify_github_profile(flat_profiles["github"])
    if "linkedin" in flat_profiles:
        verification["linkedin"] = await _verify_linkedin_url(flat_profiles["linkedin"])
    if "portfolio" in flat_profiles:
        verification["portfolio"] = await _verify_portfolio_url(flat_profiles["portfolio"])

    # Store
    try:
        memory_service = MemoryService(db)
        await memory_service.set_memory(
            user_id,
            "discovery_result",
            {
                "query": email,
                "query_type": "email",
                "extracted_name": name,
                "profiles": flat_profiles,
                "verification": verification,
                "confidence": llm_results.get("confidence"),
                "discovered_at": datetime.now(UTC).isoformat(),
            },
            weight=0.8,
        )
    except Exception as e:
        logger.debug("Failed to store email discovery result: %s", e)

    enrichment = {}
    if scrape_found:
        enrichment = await _scrape_discovered_profiles(flat_profiles, db, user_id)

    return {
        "status": "completed",
        "query_type": "email",
        "extracted_name": name,
        "profiles": flat_profiles,
        "profiles_text": llm_results.get("profiles_text", ""),
        "confidence": llm_results.get("confidence", "low"),
        "summary": llm_results.get(
            "summary",
            f"Discovered {len(flat_profiles)} profile(s) from email {email}."
        ),
        "verification": verification,
        "enrichment": enrichment,
        "total_results_scanned": len(all_results),
    }


async def discover_profiles(
    user_id: str,
    params: dict,
    db: AsyncSession,
    search_adapter: SearchAdapter | None = None,
) -> dict:
    """Main discovery entry point — dispatches by query type.

    Params:
        name: Full name to search for
        email: Email address to search from
        scrape: If True, scrape found profiles for enrichment (default: False)

    At least one of 'name' or 'email' must be provided. If both are given,
    both are used for more comprehensive search.
    """
    name = (params.get("name") or "").strip()
    email = (params.get("email") or "").strip()
    scrape_found = params.get("scrape", False)

    if not isinstance(scrape_found, bool):
        scrape_found = False

    if not name and not email:
        return {
            "status": "error",
            "error": "At least one of 'name' or 'email' must be provided",
            "profiles": {},
            "profiles_text": "",
        }

    if search_adapter is None:
        search_adapter = SearchAdapter()

    results = {}

    if email and not name:
        results = await discover_profiles_from_email(email, db, user_id, search_adapter, scrape_found)
    elif name and not email:
        results = await discover_profiles_from_name(name, db, user_id, search_adapter, scrape_found)
    else:
        # Both name and email provided — use email discovery (includes name context)
        results = await discover_profiles_from_email(email, db, user_id, search_adapter, scrape_found)

        # If email discovery was weak, also try name-only
        if results.get("confidence") in (None, "low"):
            name_results = await discover_profiles_from_name(name, db, user_id, search_adapter, scrape_found)
            for platform, url in name_results.get("profiles", {}).items():
                if platform not in results.get("profiles", {}):
                    results["profiles"][platform] = url

    return results


# ─── Helpers ────────────────────────────────────────────────


def _extract_name_from_email(email: str) -> str:
    """Extract a likely name from an email address.

    Examples:
        john.doe@gmail.com -> John Doe
        jdoe@company.com -> Jdoe (best effort)
        john-doe@company.com -> John Doe
    """
    local_part = email.split("@")[0] if "@" in email else email

    # Try splitting on common delimiters
    for sep in [".", "-", "_"]:
        if sep in local_part:
            parts = local_part.split(sep)
            # Filter out common non-name parts
            parts = [p for p in parts if p.lower() not in ("dev", "contact", "hello", "hi", "me", "info", "mail")]
            if len(parts) >= 2:
                return " ".join(p.capitalize() for p in parts[:2])

    # If no delimiter, try to camelCase split
    parts = re.findall(r"[A-Za-z][a-z]*", local_part)
    if len(parts) >= 2:
        return " ".join(p.capitalize() for p in parts[:2])

    return local_part.capitalize()


async def _scrape_discovered_profiles(
    profiles: dict[str, str],
    db: AsyncSession,
    user_id: str,
) -> dict:
    """Scrape discovered profiles for deeper enrichment data.

    For GitHub profiles: scrape repos, languages, skills
    For portfolio URLs: scrape projects, skills, experience
    """
    import asyncio

    enrichment = {}

    github_url = profiles.get("github")
    portfolio_url = profiles.get("portfolio")

    tasks = {}

    if github_url:
        tasks["github"] = scrape_github_profile(github_url)
    if portfolio_url:
        tasks["portfolio"] = scrape_portfolio(portfolio_url)

    if not tasks:
        return enrichment

    scraped_results = await asyncio.gather(*tasks.values())

    for result in scraped_results:
        if "profile" in result:
            enrichment["github_raw"] = result
            analysis = await analyze_github_for_skills(result)
            enrichment["github_analysis"] = analysis
        elif "name" in result or "skills" in result:
            enrichment["portfolio"] = result

    return enrichment
