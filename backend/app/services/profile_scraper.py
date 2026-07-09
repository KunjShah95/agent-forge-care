"""
Profile Scraper Service — extracts user profile data from external sources.

Provides:
- GitHub user profile scraping (bio, repos, languages, contributions)
- LinkedIn profile scraping (experience, education, skills)
- Portfolio website scraping (projects, tech stack, experience)

All methods return structured dicts suitable for storing in memory/Qdrant.
"""

import asyncio
import json
import logging
import re

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.services.model_manager import get_completion_llm

logger = logging.getLogger("agentforge.profile_scraper")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _get_github_headers() -> dict:
    """Build headers for GitHub API calls, with optional auth token."""
    headers = {"User-Agent": "AgentForge-CareerOS", "Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"
    return headers


def _extract_github_username(url: str) -> str | None:
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
    result = {
        "username": username,
        "source": github_url,
        "profile": {},
        "repositories": [],
        "languages": {},
        "total_stars": 0,
    }

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

                    result["repositories"].append(
                        {
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
                        }
                    )

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

BIO: {profile.get("bio", "N/A")}
COMPANY: {profile.get("company", "N/A")}
LOCATION: {profile.get("location", "N/A")}
FOLLOWERS: {profile.get("followers", 0)}
PUBLIC REPOS: {profile.get("public_repos", 0)}

TOP REPOSITORIES:
{repos_text}

LANGUAGES USED: {", ".join(languages.keys()) if languages else "N/A"}
TOPICS: {", ".join(all_topics[:10]) if all_topics else "N/A"}

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
    tech_keywords = [
        "python",
        "javascript",
        "typescript",
        "react",
        "node.js",
        "aws",
        "docker",
        "kubernetes",
        "machine learning",
        "ai",
        "api",
        "graphql",
        "sql",
        "mongodb",
        "postgresql",
        "redis",
        "tensorflow",
        "pytorch",
        "go",
        "rust",
        "java",
        "c++",
        "html",
        "css",
        "tailwind",
    ]
    for kw in tech_keywords:
        if kw.lower() in repo_desc_text.lower() and kw.title() not in skills:
            skills.append(kw.title())

    profile_name = profile.get("name") or github_data.get("username", "Unknown")
    top_lang_keys = list(languages.keys())[:5] if languages else ["Unknown"]
    experience_level = (
        "junior" if profile.get("followers", 0) < 10 and total_stars < 50 else "mid" if total_stars < 500 else "senior"
    )

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


# ─── GitHub Commit History Scraper ────────────────────────────


async def scrape_github_commits(github_url: str, max_commits: int = 500) -> dict:
    """
    Fetch recent commit history across a user's repos and public events.

    Uses:
    - Events API: /users/{username}/events/public (last 90 days of pushes, PRs, etc.)
    - Commits API: /repos/{owner}/{repo}/commits?author={username} (per-repo)

    Returns structured data:
    - total_commits: count across all repos
    - commits_by_repo: dict mapping repo name -> list of commit summaries
    - recent_events: last 100 public events
    - commit_languages: languages used in committed repos
    - commit_frequency: daily commit patterns
    """
    username = _extract_github_username(github_url)
    if not username:
        return {"error": f"Could not extract GitHub username from URL: {github_url}"}

    headers = _get_github_headers()
    result = {
        "username": username,
        "total_commits": 0,
        "commits_by_repo": {},
        "recent_events": [],
        "commit_languages": {},
        "commit_frequency": {"by_day": {}, "by_hour": {}, "by_day_of_week": {}},
        "average_commits_per_day": 0.0,
        "commit_dates": [],
        "commit_messages": [],
    }
    # Track seen SHAs to prevent double-counting between Events API and per-repo API
    seen_shas: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # ── Step 1: Fetch public events (pushes, PRs, issues, etc.) ──
            events = []
            events_url = f"https://api.github.com/users/{username}/events/public"
            events_resp = await client.get(events_url, headers=headers)
            if events_resp.status_code == 200:
                events_raw = events_resp.json()
                for ev in events_raw[:100]:
                    event_type = ev.get("type", "")
                    repo_name = ev.get("repo", {}).get("name", "") if ev.get("repo") else ""
                    created_at = ev.get("created_at", "")
                    payload = ev.get("payload", {}) or {}

                    entry = {
                        "type": event_type,
                        "repo": repo_name,
                        "date": created_at,
                    }

                    # Extract commit messages from PushEvents
                    if event_type == "PushEvent" and payload.get("commits"):
                        commits = []
                        for c in payload["commits"][:10]:
                            sha = c.get("sha", "")[:7]
                            msg = (c.get("message") or "").split("\n")[0][:120]
                            commits.append({
                                "sha": sha,
                                "message": msg,
                            })
                            if sha and sha not in seen_shas:
                                seen_shas.add(sha)
                                result["commit_messages"].append(msg)
                                result["commits_by_repo"].setdefault(repo_name, []).append(msg)
                                result["total_commits"] += 1
                                result["commit_dates"].append(created_at[:10])
                        entry["commits"] = commits

                    events.append(entry)

                result["recent_events"] = events

            # ── Step 2: Fetch repos and get per-repo commit counts ──
            repos_resp = await client.get(
                f"https://api.github.com/users/{username}/repos",
                params={"sort": "pushed", "direction": "desc", "per_page": 10, "type": "owner"},
                headers=headers,
            )

            if repos_resp.status_code == 200:
                repos_data = repos_resp.json()
                for repo in repos_data:
                    repo_name = repo.get("full_name", repo.get("name", ""))
                    lang = repo.get("language")
                    pushed_at = repo.get("pushed_at", "")

                    # Track languages
                    if lang and lang not in result["commit_languages"]:
                        result["commit_languages"][lang] = 0
                    if lang:
                        result["commit_languages"][lang] += 1

                    # Only fetch commits for repos pushed to in last 90 days
                    if pushed_at:
                        try:
                            from datetime import datetime, timezone
                            pushed_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                            now = datetime.now(timezone.utc)
                            days_since_push = (now - pushed_dt).days
                        except Exception:
                            days_since_push = 0

                        if days_since_push < 180:  # Only recently active repos
                            try:
                                commits_resp = await client.get(
                                    f"https://api.github.com/repos/{repo_name}/commits",
                                    params={"author": username, "per_page": 20},
                                    headers=headers,
                                    timeout=5.0,
                                )
                                if commits_resp.status_code == 200:
                                    commits_data = commits_resp.json()
                                    for c in commits_data:
                                        sha = c.get("sha", "")[:7]
                                        msg = (c.get("commit", {}).get("message", "") or "").split("\n")[0][:120]
                                        date = c.get("commit", {}).get("author", {}).get("date", "")[:10]

                                        if sha and msg and sha not in seen_shas:
                                            seen_shas.add(sha)
                                            result["commits_by_repo"].setdefault(repo_name, []).append(msg)
                                            result["commit_messages"].append(msg)
                                            result["total_commits"] += 1
                                            result["commit_dates"].append(date)

                                    # Avoid hitting rate limits — pause briefly
                                    await asyncio.sleep(0.1)
                            except Exception as e:
                                logger.debug("Failed to fetch commits for %s: %s", repo_name, e)
                                continue

            # ── Step 3: Compute commit frequency patterns ──
            dates = result["commit_dates"]
            if dates:
                from collections import Counter
                day_counts = Counter(dates)
                result["commit_frequency"]["by_day"] = dict(day_counts.most_common(30))

                # Day of week and hour patterns (from events timestamps)
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                dow_counts = Counter()
                for ev in events:
                    ev_date = ev.get("date", "")
                    if ev_date:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(ev_date.replace("Z", "+00:00"))
                            dow_counts[day_names[dt.weekday()]] += 1
                        except Exception:
                            pass
                result["commit_frequency"]["by_day_of_week"] = dict(dow_counts.most_common(7))

                # Average commits per day
                unique_days = len(set(dates))
                if unique_days > 0:
                    result["average_commits_per_day"] = round(result["total_commits"] / unique_days, 1)

            # Deduplicate commit messages
            result["total_unique_commits"] = len(set(result["commit_messages"]))
            result["commit_messages"] = result["commit_messages"][:200]

            return result

    except httpx.TimeoutException:
        return {"error": "GitHub Events API request timed out"}
    except Exception as e:
        logger.warning("Failed to scrape GitHub commits: %s", e)
        return {"error": str(e)}


async def scrape_github_contributions(github_url: str) -> dict:
    """
    Scrape GitHub contribution graph data.

    Uses GraphQL API (if GITHUB_TOKEN is set) or falls back to
    scraping the profile page HTML for contribution calendar data.

    Returns:
    - total_contributions: last year total
    - contribution_calendar: weekly contribution counts (52 weeks)
    - longest_streak: days
    - current_streak: days
    - top_contribution_months
    """
    username = _extract_github_username(github_url)
    if not username:
        return {"error": f"Could not extract GitHub username from URL: {github_url}"}

    result = {
        "username": username,
        "total_contributions": 0,
        "contribution_calendar": [],
        "longest_streak": 0,
        "current_streak": 0,
        "top_contribution_months": [],
    }

    headers = _get_github_headers()

    try:
        # Try GraphQL API first (requires GITHUB_TOKEN)
        if settings.github_token:
            graphql_url = "https://api.github.com/graphql"
            query = """
            query($username: String!) {
              user(login: $username) {
                contributionsCollection {
                  contributionCalendar {
                    totalContributions
                    weeks {
                      contributionDays {
                        contributionCount
                        date
                      }
                    }
                  }
                }
              }
            }
            """

            async with httpx.AsyncClient(timeout=10.0) as client:
                gql_resp = await client.post(
                    graphql_url,
                    json={"query": query, "variables": {"username": username}},
                    headers={
                        "Authorization": f"bearer {settings.github_token}",
                        "User-Agent": "AgentForge-CareerOS",
                    },
                )

                if gql_resp.status_code == 200:
                    gql_data = gql_resp.json()
                    cal_data = (
                        gql_data.get("data", {})
                        .get("user", {})
                        .get("contributionsCollection", {})
                        .get("contributionCalendar", {})
                    )

                    if cal_data:
                        total = cal_data.get("totalContributions", 0)
                        result["total_contributions"] = total

                        weeks = cal_data.get("weeks", [])
                        calendar = []
                        daily_counts = []
                        for week in weeks:
                            for day in week.get("contributionDays", []):
                                count = day.get("contributionCount", 0)
                                date = day.get("date", "")
                                calendar.append({"date": date, "count": count})
                                daily_counts.append(count)

                        result["contribution_calendar"] = calendar

                        # Compute streaks
                        current_streak = 0
                        longest_streak = 0
                        temp_streak = 0

                        for day in reversed(calendar):
                            if day["count"] > 0:
                                current_streak += 1
                            else:
                                break
                        result["current_streak"] = current_streak

                        for day in calendar:
                            if day["count"] > 0:
                                temp_streak += 1
                                longest_streak = max(longest_streak, temp_streak)
                            else:
                                temp_streak = 0
                        result["longest_streak"] = longest_streak

                        # Top months
                        month_map: dict[str, int] = {}
                        for d in calendar:
                            month_key = d["date"][:7]  # YYYY-MM
                            month_map[month_key] = month_map.get(month_key, 0) + d["count"]
                        sorted_months = sorted(month_map.items(), key=lambda x: x[1], reverse=True)
                        result["top_contribution_months"] = [
                            {"month": m, "count": c} for m, c in sorted_months[:6]
                        ]

                        return result

        # Fallback: scrape profile page HTML for contribution graph
        profile_url = f"https://github.com/{username}"
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=10.0,
        ) as client:
            resp = await client.get(profile_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")

                # Parse contribution squares from the graph
                contrib_els = soup.select("rect.ContributionCalendar-day")
                if not contrib_els:
                    contrib_els = soup.select("rect[data-date]")

                if contrib_els:
                    calendar = []
                    for rect in contrib_els:
                        date = rect.get("data-date", "")
                        count_text = rect.get("data-count", "0") or rect.get("data-level", "0")
                        try:
                            count = int(count_text)
                        except (ValueError, TypeError):
                            count = 0
                        if date:
                            calendar.append({"date": date, "count": count})

                    result["contribution_calendar"] = calendar
                    result["total_contributions"] = sum(d["count"] for d in calendar)

                    # Streaks
                    current_streak = 0
                    longest_streak = 0
                    temp_streak = 0

                    for day in reversed(calendar):
                        if day["count"] > 0:
                            current_streak += 1
                        else:
                            break
                    result["current_streak"] = current_streak

                    for day in calendar:
                        if day["count"] > 0:
                            temp_streak += 1
                            longest_streak = max(longest_streak, temp_streak)
                        else:
                            temp_streak = 0
                    result["longest_streak"] = longest_streak

                # Fallback: try text-based parsing
                total_text = soup.find("h2", class_="f4 text-normal mb-2")
                if total_text:
                    import re as _re
                    nums = _re.findall(r"\d[\d,]*", total_text.get_text())
                    if nums:
                        try:
                            result["total_contributions"] = int(nums[0].replace(",", ""))
                        except ValueError:
                            pass

                return result

            return {"error": f"Profile page returned HTTP {resp.status_code}"}

    except httpx.TimeoutException:
        return {"error": "GitHub contribution request timed out"}
    except Exception as e:
        logger.warning("Failed to scrape GitHub contributions: %s", e)
        return {"error": str(e)}


async def scrape_github_oss_contributions(github_url: str, max_results: int = 30) -> dict:
    """
    Scrape a user's open-source contributions to OTHER repos.

    Uses GitHub Search API to find:
    - Pull requests authored by the user to repos they don't own
    - Issues opened by the user to other repos

    Returns structured data with PRs, issues, and contribution summary.
    """
    username = _extract_github_username(github_url)
    if not username:
        return {"error": f"Could not extract GitHub username from URL: {github_url}"}

    headers = _get_github_headers()
    result = {
        "username": username,
        "pull_requests": [],
        "issues": [],
        "total_prs": 0,
        "total_issues": 0,
        "repos_contributed_to": [],
        "summary": "",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # ── Search for PRs authored by this user ──
            pr_query = f"author:{username} type:pr is:public"
            pr_resp = await client.get(
                "https://api.github.com/search/issues",
                params={"q": pr_query, "sort": "created", "order": "desc", "per_page": min(max_results, 30)},
                headers=headers,
            )

            if pr_resp.status_code == 200:
                pr_data = pr_resp.json()
                result["total_prs"] = pr_data.get("total_count", 0)

                for item in pr_data.get("items", [])[:max_results]:
                    repo_url = item.get("repository_url", "")
                    repo_name = repo_url.replace("https://api.github.com/repos/", "") if repo_url else ""
                    html_url = item.get("html_url", "")

                    # Only count as OSS if it's not the user's own repo
                    if repo_name and not repo_name.startswith(f"{username}/"):
                        pr_entry = {
                            "title": item.get("title", ""),
                            "url": html_url,
                            "repo": repo_name,
                            "state": item.get("state", ""),
                            "created_at": item.get("created_at", ""),
                            "comments": item.get("comments", 0),
                        }
                        result["pull_requests"].append(pr_entry)
                        if repo_name not in result["repos_contributed_to"]:
                            result["repos_contributed_to"].append(repo_name)

            # ── Search for issues authored by this user to other repos ──
            issue_query = f"author:{username} type:issue is:public"
            issue_resp = await client.get(
                "https://api.github.com/search/issues",
                params={"q": issue_query, "sort": "created", "order": "desc", "per_page": min(max_results, 30)},
                headers=headers,
            )

            if issue_resp.status_code == 200:
                issue_data = issue_resp.json()
                result["total_issues"] = issue_data.get("total_count", 0)

                for item in issue_data.get("items", [])[:max_results]:
                    repo_url = item.get("repository_url", "")
                    repo_name = repo_url.replace("https://api.github.com/repos/", "") if repo_url else ""

                    if repo_name and not repo_name.startswith(f"{username}/"):
                        issue_entry = {
                            "title": item.get("title", ""),
                            "url": item.get("html_url", ""),
                            "repo": repo_name,
                            "state": item.get("state", ""),
                            "created_at": item.get("created_at", ""),
                            "comments": item.get("comments", 0),
                        }
                        result["issues"].append(issue_entry)
                        if repo_name not in result["repos_contributed_to"]:
                            result["repos_contributed_to"].append(repo_name)

            # Build summary
            if result["pull_requests"] or result["issues"]:
                merged_prs = sum(1 for pr in result["pull_requests"] if pr["state"] == "merged" or pr["state"] == "closed")
                open_prs = sum(1 for pr in result["pull_requests"] if pr["state"] == "open")

                parts = []
                if result["total_prs"]:
                    parts.append(f"{result['total_prs']} total PRs ({merged_prs} merged/closed, {open_prs} open)")
                if result["repos_contributed_to"]:
                    parts.append(f"contributed to {len(result['repos_contributed_to'])} repos")
                result["summary"] = ", ".join(parts) if parts else "No OSS contributions found"

            return result

    except httpx.TimeoutException:
        return {"error": "GitHub OSS search request timed out"}
    except Exception as e:
        logger.warning("Failed to scrape GitHub OSS contributions: %s", e)
        return {"error": str(e)}


# ─── Commit & Contribution Analysis ────────────────────────


async def analyze_commit_history(
    commit_data: dict | None = None,
    contribution_data: dict | None = None,
    oss_data: dict | None = None,
) -> dict:
    """
    Analyze commit history, contribution patterns, and OSS activity
    to extract insights about a developer's coding behavior.

    Uses LLM when available, falls back to rule-based analysis.
    """
    llm = get_completion_llm(temperature=0.3, preferred_provider="openai")

    # Build context for analysis
    context_parts = []

    if commit_data and "error" not in commit_data:
        messages = commit_data.get("commit_messages", [])[:50]
        by_repo = commit_data.get("commits_by_repo", {})
        frequency = commit_data.get("commit_frequency", {})
        avg_per_day = commit_data.get("average_commits_per_day", 0)
        languages = commit_data.get("commit_languages", {})

        context_parts.append(
            f"COMMIT HISTORY:\n"
            f"- Total commits tracked: {commit_data.get('total_commits', 0)}\n"
            f"- Average commits per day: {avg_per_day}\n"
            f"- Active repos: {len(by_repo)}\n"
            f"- Languages used: {', '.join(list(languages.keys())[:8])}\n"
        )

        if messages:
            context_parts.append(
                "RECENT COMMIT MESSAGES:\n" + "\n".join(f"  - {m}" for m in messages[:20])
            )

        dow = frequency.get("by_day_of_week", {})
        if dow:
            context_parts.append(
                "COMMIT DAY OF WEEK PATTERN: " + ", ".join(f"{d}: {c}" for d, c in dow.items())
            )

    if contribution_data and "error" not in contribution_data:
        context_parts.append(
            f"CONTRIBUTION GRAPH:\n"
            f"- Total contributions (last year): {contribution_data.get('total_contributions', 0)}\n"
            f"- Current streak: {contribution_data.get('current_streak', 0)} days\n"
            f"- Longest streak: {contribution_data.get('longest_streak', 0)} days\n"
        )
        top_months = contribution_data.get("top_contribution_months", [])
        if top_months:
            context_parts.append(
                "TOP MONTHS: " + ", ".join(f"{m['month']} ({m['count']})" for m in top_months[:4])
            )

    if oss_data and "error" not in oss_data:
        prs = oss_data.get("pull_requests", [])
        repos = oss_data.get("repos_contributed_to", [])
        context_parts.append(
            f"OPEN SOURCE:\n"
            f"- Total PRs: {oss_data.get('total_prs', 0)}\n"
            f"- Repos contributed to: {len(repos)}\n"
        )
        if prs[:5]:
            context_parts.append(
                "RECENT OSS PRs:\n" + "\n".join(f"  - {p.get('repo', '')}: {p.get('title', '')}" for p in prs[:5])
            )

    context = "\n".join(context_parts)

    if not context.strip():
        return {"error": "No commit or contribution data to analyze"}

    # ── LLM Analysis ──
    if llm:
        try:
            from langchain_core.messages import HumanMessage

            prompt = f"""You are a developer productivity analyst. Analyze this developer's coding activity
and provide structured insights.

{context}

Return ONLY valid JSON with:
- "coding_frequency": "daily" | "weekly" | "sporadic" | "intense_bursts" — when they code most
- "preferred_work_days": array of top 3 days they commit (e.g. ["Mon", "Tue", "Wed"])
- "commit_quality": "well_documented" | "functional" | "minimal" | "mixed" based on commit messages
- "project_focus": "single_repo" | "multiple_repos" | "many_projects" based on repo spread
- "oss_participation": "active" | "moderate" | "minimal" | "none"
- "consistency_score": 0-100 estimate based on commit regularity
- "experience_indicators": array of strings noting strong signals (e.g. "frequent contributions to major projects", "sustained commit streaks", "well documented commits")
- "summary": 2-3 sentence summary of their coding activity (string)

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
            logger.debug("LLM commit analysis failed, using rule-based: %s", e)

    # ── Rule-based fallback ──
    total_commits = (commit_data or {}).get("total_commits", 0) or 0
    active_repos = len((commit_data or {}).get("commits_by_repo", {}) or {})
    avg_per_day = (commit_data or {}).get("average_commits_per_day", 0) or 0.0
    current_streak = (contribution_data or {}).get("current_streak", 0) or 0
    total_contrib = (contribution_data or {}).get("total_contributions", 0) or 0
    oss_prs = len((oss_data or {}).get("pull_requests", []) or [])
    oss_repos = len((oss_data or {}).get("repos_contributed_to", []) or [])

    # Frequency
    if avg_per_day >= 3:
        coding_frequency = "daily"
    elif avg_per_day >= 1:
        coding_frequency = "regular"
    elif current_streak >= 7:
        coding_frequency = "weekly"
    else:
        coding_frequency = "sporadic"

    # OSS level
    if oss_repos >= 5 or oss_prs >= 10:
        oss_level = "active"
    elif oss_repos >= 2 or oss_prs >= 3:
        oss_level = "moderate"
    elif oss_prs > 0:
        oss_level = "minimal"
    else:
        oss_level = "none"

    # Consistency
    consistency = min(100, int(total_contrib / 3.65))  # ~365 days / 100
    if current_streak > 30:
        consistency += 20
    consistency = min(100, consistency)

    return {
        "coding_frequency": coding_frequency,
        "preferred_work_days": list((commit_data or {}).get("commit_frequency", {}).get("by_day_of_week", {}).keys())[:3],
        "commit_quality": "functional",
        "project_focus": "multiple_repos" if active_repos > 3 else "single_repo",
        "oss_participation": oss_level,
        "consistency_score": consistency,
        "experience_indicators": [
            f"{total_commits} tracked commits across {active_repos} repos",
            f"{current_streak}-day current contribution streak" if current_streak > 0 else "",
            f"Contributed to {oss_repos} external projects" if oss_repos > 0 else "",
            f"{total_contrib} contributions in the last year" if total_contrib > 0 else "",
        ],
        "summary": f"Developer with {total_commits} tracked commits across {active_repos} repos. "
        f"{coding_frequency.title()} coder with {current_streak}-day streak. "
        f"{oss_level.title()} OSS participation across {oss_repos} projects.",
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
SECTIONS (headings): {", ".join(headings) if headings else "N/A"}

PAGE CONTENT (first 8000 chars):
{body_text[:8000]}

LINKS FOUND:
{chr(10).join(f"- {link['text']}: {link['url']}" for link in links[:10]) if links else "N/A"}

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
            tech_keywords = [
                "python",
                "javascript",
                "typescript",
                "react",
                "vue",
                "angular",
                "node",
                "django",
                "flask",
                "fastapi",
                "aws",
                "docker",
                "kubernetes",
                "sql",
                "mongodb",
                "postgres",
                "graphql",
                "tensorflow",
                "pytorch",
                "tailwind",
                "bootstrap",
                "html",
                "css",
                "sass",
                "git",
                "api",
            ]
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
