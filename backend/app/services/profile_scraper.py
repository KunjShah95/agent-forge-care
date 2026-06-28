"""
Profile Scraper Service — extracts user profile data from external sources.

Provides:
- GitHub user profile scraping (bio, repos, languages, contributions)
- Portfolio website scraping (projects, tech stack, experience)

All methods return structured dicts suitable for storing in memory/Qdrant.
"""

import json
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.services.model_manager import get_completion_llm

logger = logging.getLogger("agentforge.profile_scraper")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _get_github_headers() -> dict:
    """Build headers for GitHub API calls, with optional auth token."""
    headers = {"User-Agent": "AgentForge-CareerOS", "Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"
    return headers


def _extract_github_username(url: str) -> Optional[str]:
    """Extract GitHub username from a URL like https://github.com/username."""
    if not url:
        return None
    m = re.search(r"github\.com/([A-Za-z0-9_.-]+)", url)
    return m.group(1) if m else None


# ─── GitHub User Profile Scraper ─────────────────────────────


async def scrape_github_profile(github_url: str) -> dict:
    """
    Scrape a GitHub user's profile and repos.

    Fetches:
    - Profile: bio, location, company, blog, followers, following, public repos
    - Repos: top 30 repos by stars with languages
    - Language breakdown aggregated across all fetched repos
    - Pinned repos (via GraphQL if possible, else just top-starred)

    Returns a structured dict with all findings, or an error dict.
    """
    username = _extract_github_username(github_url)
    if not username:
        return {"error": f"Could not extract GitHub username from URL: {github_url}", "source": github_url}

    headers = _get_github_headers()
    result = {"username": username, "source": github_url, "profile": {}, "repositories": [], "languages": {}, "total_stars": 0}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # ── Fetch user profile ──
            user_resp = await client.get(f"https://api.github.com/users/{username}", headers=headers)
            if user_resp.status_code == 404:
                return {"error": f"GitHub user '{username}' not found", "source": github_url}
            if user_resp.status_code == 403:
                return {"error": "GitHub API rate limited. Set GITHUB_TOKEN for higher limits.", "source": github_url}
            if user_resp.status_code != 200:
                return {"error": f"GitHub API returned {user_resp.status_code}", "source": github_url}

            user_data = user_resp.json()
            result["profile"] = {
                "name": user_data.get("name"),
                "bio": user_data.get("bio"),
                "location": user_data.get("location"),
                "company": user_data.get("company"),
                "blog": user_data.get("blog"),
                "email": user_data.get("email"),
                "twitter_username": user_data.get("twitter_username"),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "public_repos": user_data.get("public_repos", 0),
                "public_gists": user_data.get("public_gists", 0),
                "created_at": user_data.get("created_at"),
                "avatar_url": user_data.get("avatar_url"),
                "html_url": user_data.get("html_url"),
                "hireable": user_data.get("hireable"),
            }

            # ── Fetch repositories (top 30 by stars) ──
            repos_resp = await client.get(
                f"https://api.github.com/users/{username}/repos",
                params={"sort": "stars", "direction": "desc", "per_page": 30, "type": "owner"},
                headers=headers,
            )

            if repos_resp.status_code == 200:
                repos_raw = repos_resp.json()
                lang_map = {}
                total_stars = 0

                for repo in repos_raw:
                    name = repo.get("name", "")
                    lang = repo.get("language")
                    stars = repo.get("stargazers_count", 0)
                    total_stars += stars

                    if lang:
                        lang_map[lang] = lang_map.get(lang, 0) + 1

                    result["repositories"].append({
                        "name": name,
                        "full_name": repo.get("full_name", ""),
                        "description": repo.get("description"),
                        "language": lang,
                        "stars": stars,
                        "forks": repo.get("forks_count", 0),
                        "topics": repo.get("topics", []),
                        "is_fork": repo.get("fork", False),
                        "html_url": repo.get("html_url", ""),
                        "homepage": repo.get("homepage"),
                        "updated_at": repo.get("updated_at"),
                    })

                result["languages"] = dict(sorted(lang_map.items(), key=lambda x: x[1], reverse=True))
                result["total_stars"] = total_stars

            return result

    except httpx.TimeoutException:
        return {"error": "GitHub API request timed out", "source": github_url}
    except Exception as e:
        logger.warning("Failed to scrape GitHub profile %s: %s", github_url, e)
        return {"error": str(e), "source": github_url}


async def analyze_github_for_skills(github_data: dict) -> dict:
    """
    Analyze scraped GitHub data to extract skills, project highlights,
    and career insights using LLM.
    """
    if not github_data or "error" in github_data:
        return {"error": github_data.get("error", "No data")}

    profile = github_data.get("profile", {})
    repos = github_data.get("repositories", [])
    languages = github_data.get("languages", {})
    total_stars = github_data.get("total_stars", 0)

    # Extract top repos (by stars, non-fork)
    top_repos = sorted(
        [r for r in repos if not r.get("is_fork")],
        key=lambda r: r.get("stars", 0),
        reverse=True,
    )[:5]

    # Extract all unique topics
    all_topics = list(set(t for r in repos for t in r.get("topics", [])))

    # Build summary with LLM if available
    llm = get_completion_llm(temperature=0.3, preferred_provider="openai")

    if llm and top_repos:
        try:
            from langchain_core.messages import HumanMessage

            repos_text = "\n".join(
                f"- {r['name']}: {r.get('description', 'No description')} (⭐{r.get('stars', 0)}, {r.get('language', 'N/A')})"
                for r in top_repos
            )

            prompt = f"""You are a technical recruiter analyzing a GitHub profile.

BIO: {profile.get('bio', 'N/A')}
COMPANY: {profile.get('company', 'N/A')}
LOCATION: {profile.get('location', 'N/A')}
FOLLOWERS: {profile.get('followers', 0)}
PUBLIC REPOS: {profile.get('public_repos', 0)}

TOP REPOSITORIES:
{repos_text}

LANGUAGES USED: {', '.join(languages.keys()) if languages else 'N/A'}
TOPICS: {', '.join(all_topics[:10]) if all_topics else 'N/A'}

Return ONLY valid JSON with:
- "skills": array of inferred technical skills (list of strings, up to 15)
- "primary_languages": array of top languages by usage (list of strings, up to 5)
- "project_highlights": array of notable project descriptions (list of strings, up to 3)
- "experience_level": "junior" | "mid" | "senior" | "expert" estimation based on profile
- "summary": 2-3 sentence professional summary (string)
- "interests": array of inferred technical interests (list of strings, up to 5)

No markdown, no explanations."""
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
            if content.startswith("json"):
                content = content[4:].strip()

            analysis = json.loads(content)
            analysis["_source"] = "llm"
            return analysis
        except Exception as e:
            logger.debug("LLM GitHub analysis failed, using rule-based: %s", e)

    # Rule-based fallback
    skills = list(languages.keys()) + all_topics
    repo_desc_text = " ".join(r.get("description", "") for r in top_repos)
    tech_keywords = ["python", "javascript", "typescript", "react", "node.js", "aws",
                     "docker", "kubernetes", "machine learning", "ai", "api", "graphql",
                     "sql", "mongodb", "postgresql", "redis", "tensorflow", "pytorch",
                     "go", "rust", "java", "c++", "html", "css", "tailwind"]
    for kw in tech_keywords:
        if kw.lower() in repo_desc_text.lower() and kw.title() not in skills:
            skills.append(kw.title())

    profile_name = profile.get("name") or github_data.get("username", "Unknown")
    top_lang_keys = list(languages.keys())[:5] if languages else ["Unknown"]
    experience_level = "junior" if profile.get("followers", 0) < 10 and total_stars < 50 else "mid" if total_stars < 500 else "senior"

    return {
        "skills": list(set(skills))[:15],
        "primary_languages": top_lang_keys,
        "project_highlights": [f"{r['name']}: {r.get('description', 'No description')}" for r in top_repos[:3]],
        "experience_level": experience_level,
        "summary": f"{profile_name} has {profile.get('public_repos', 0)} public repos with {total_stars} total stars. "
                   f"Primary languages include {', '.join(top_lang_keys)}.",
        "interests": all_topics[:5],
        "_source": "rule_based",
    }


# ─── Portfolio Website Scraper ──────────────────────────────


async def scrape_portfolio(portfolio_url: str) -> dict:
    """
    Scrape a personal portfolio/website to extract project info, tech stack,
    and professional experience.

    Fetches the page, extracts visible text content, then uses LLM
    to structure the findings. Falls back to regex parsing.
    """
    if not portfolio_url or not portfolio_url.startswith(("http://", "https://")):
        return {"error": f"Invalid portfolio URL: {portfolio_url}", "source": portfolio_url}

    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(portfolio_url)
            if resp.status_code != 200:
                return {"error": f"Portfolio returned HTTP {resp.status_code}", "source": portfolio_url}

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove scripts, styles, nav, footer for clean text
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            page_title = soup.title.string.strip() if soup.title and soup.title.string else ""
            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                meta_desc = meta_tag["content"].strip()

            # Extract all visible text
            body_text = soup.get_text(separator="\n", strip=True)
            # Limit to prevent token blowup
            body_text = body_text[:10000]

            # Extract links (potential project links)
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if href.startswith(("http://", "https://")) and text:
                    links.append({"text": text[:80], "url": href})
            links = links[:20]

            # Extract headings as section markers
            headings = []
            for h in soup.find_all(["h1", "h2", "h3"]):
                text = h.get_text(strip=True)
                if text:
                    headings.append(text)
            headings = headings[:15]

            # ── Use LLM to structure the findings ──
            llm = get_completion_llm(temperature=0.3, preferred_provider="openai")

            if llm:
                try:
                    from langchain_core.messages import HumanMessage

                    prompt = f"""You are analyzing a personal portfolio/website at {portfolio_url}.

TITLE: {page_title}
META DESCRIPTION: {meta_desc}
SECTIONS (headings): {', '.join(headings) if headings else 'N/A'}

PAGE CONTENT (first 8000 chars):
{body_text[:8000]}

LINKS FOUND:
{chr(10).join(f'- {l["text"]}: {l["url"]}' for l in links[:10]) if links else 'N/A'}

Return ONLY valid JSON with:
- "name": person's name if found (string or null)
- "role": current role / title if found (string or null)
- "skills": array of technologies/skills mentioned (list of strings)
- "projects": array of project names or descriptions found (list of strings, up to 5)
- "experience": array of work experience entries found (list of strings, up to 3)
- "education": array of education entries (list of strings, up to 2)
- "summary": 2-3 sentence summary of the person's profile (string)
- "technologies_detected": array of tech keywords detected (list of strings)

No markdown, no explanations."""
                    response = await llm.ainvoke([HumanMessage(content=prompt)])
                    content = response.content.strip()
                    if content.startswith("```"):
                        content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
                    if content.startswith("json"):
                        content = content[4:].strip()

                    analysis = json.loads(content)
                    analysis["_source"] = "llm"
                    analysis["page_title"] = page_title
                    analysis["url"] = portfolio_url
                    return analysis
                except Exception as e:
                    logger.debug("LLM portfolio analysis failed, using rule-based: %s", e)

            # Rule-based fallback
            tech_keywords = ["python", "javascript", "typescript", "react", "vue", "angular",
                             "node", "django", "flask", "fastapi", "aws", "docker", "kubernetes",
                             "sql", "mongodb", "postgres", "graphql", "tensorflow", "pytorch",
                             "tailwind", "bootstrap", "html", "css", "sass", "git", "api"]
            detected = [kw for kw in tech_keywords if kw.lower() in body_text.lower()]

            return {
                "name": None,
                "role": None,
                "skills": [d.title() for d in detected[:15]],
                "projects": headings[:5],
                "experience": [],
                "education": [],
                "summary": (meta_desc or page_title or f"Portfolio at {portfolio_url}")[:300],
                "technologies_detected": [d.title() for d in detected[:10]],
                "page_title": page_title,
                "url": portfolio_url,
                "_source": "rule_based",
            }

    except httpx.TimeoutException:
        return {"error": "Portfolio request timed out", "source": portfolio_url}
    except Exception as e:
        logger.warning("Failed to scrape portfolio %s: %s", portfolio_url, e)
        return {"error": str(e), "source": portfolio_url}
