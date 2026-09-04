"""Social writing signals — Medium RSS + personal blog analysis.

Medium exposes public RSS feeds (https://medium.com/feed/@handle) with no
API key. Personal blogs are analysed via lightweight HTML fetch:
post volume, recency, and technical depth.

X/Twitter is intentionally NOT covered: no free API, login wall, and
aggressive rate limits. Any X presence is captured only through the
GitHub-discovered twitter handle as a binary "linked" flag.
"""

import logging
import re
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("agentforge.social_signals")

TECH_RE = re.compile(
    r"\b(python|javascript|typescript|java\b|go\b|golang|rust|kotlin|swift|react|angular|vue|"
    r"node|django|flask|fastapi|docker|kubernetes|aws|azure|gcp|terraform|sql|postgres|"
    r"machine learning|\bml\b|deep learning|llm|rag|langchain|pytorch|tensorflow|pandas|"
    r"graphql|rest|api|devops|ci/cd|linux|git|typescript)\b",
    re.IGNORECASE,
)

CODE_HINT_RE = re.compile(r"(```|<code|github\.com|pip install|npm install|def \w+\(|class \w+|import \w+|SELECT .* FROM)", re.IGNORECASE)


def _normalize_medium_handle(handle_or_url: str) -> str | None:
    """Accept '@alice', 'alice', or a medium.com/@alice URL → 'alice'."""
    if not handle_or_url:
        return None
    s = handle_or_url.strip().lstrip("@")
    m = re.search(r"medium\.com/@([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    s = s.split("/")[0].split("?")[0]
    if re.fullmatch(r"[A-Za-z0-9_.-]+", s):
        return s.lstrip("@")
    return None


async def fetch_medium_posts(handle_or_url: str, max_posts: int = 20) -> dict:
    """Fetch a Medium author's recent posts via public RSS. No API key needed."""
    import feedparser

    handle = _normalize_medium_handle(handle_or_url)
    if not handle:
        return {"error": f"Invalid Medium handle: {handle_or_url}", "posts": []}

    url = f"https://medium.com/feed/@{handle}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "AgentForge/1.0"})
        if resp.status_code != 200:
            return {"error": f"Medium returned HTTP {resp.status_code}", "posts": []}
        feed = feedparser.parse(resp.text)
        if feed.bozo and not feed.entries:
            return {"error": "Medium feed unparseable (unknown handle?)", "posts": []}
        posts = []
        tech_posts = 0
        for e in feed.entries[:max_posts]:
            title = getattr(e, "title", "") or ""
            tags = [t.term for t in getattr(e, "tags", []) or [] if getattr(t, "term", None)]
            summary = re.sub(r"<[^>]+>", " ", getattr(e, "summary", "") or "")[:2000]
            body = f"{title} {' '.join(tags)} {summary}"
            is_tech = bool(TECH_RE.search(body))
            has_code = bool(CODE_HINT_RE.search(getattr(e, "summary", "") or ""))
            if is_tech:
                tech_posts += 1
            published = getattr(e, "published", "") or ""
            posts.append(
                {
                    "title": title[:200],
                    "url": getattr(e, "link", ""),
                    "published": published,
                    "tags": tags[:8],
                    "is_tech": is_tech,
                    "has_code": has_code,
                }
            )
        return {
            "handle": handle,
            "total_posts": len(posts),
            "tech_posts": tech_posts,
            "posts": posts,
            "source": "medium_rss",
        }
    except Exception as e:
        logger.debug("Medium fetch failed for %s: %s", handle, e)
        return {"error": str(e)[:200], "posts": []}


async def fetch_blog_signals(blog_url: str) -> dict:
    """Lightweight personal-blog analysis: volume, recency, technical depth."""
    if not blog_url or not blog_url.startswith(("http://", "https://")):
        return {"error": f"Invalid blog URL: {blog_url}", "posts": []}
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(blog_url, headers={"User-Agent": "AgentForge/1.0"})
        if resp.status_code != 200:
            return {"error": f"Blog returned HTTP {resp.status_code}", "posts": []}
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        articles = soup.find_all("article")
        # Fallback: dated links / headings look like post listings
        candidates = articles or soup.select("li.post, div.post, section.post")
        posts = []
        for a in candidates[:20]:
            text = a.get_text(" ", strip=True)
            if len(text) < 80:
                continue
            link = a.find("a", href=True)
            url = link["href"] if link else ""
            if url.startswith("/"):
                from urllib.parse import urljoin

                url = urljoin(blog_url, url)
            posts.append({"title": text[:200], "url": url, "is_tech": bool(TECH_RE.search(text))})
        body = soup.get_text(" ", strip=True)[:20000]
        tech_hits = len(set(TECH_RE.findall(body)))
        return {
            "url": blog_url,
            "post_count_estimate": len(posts),
            "tech_posts": sum(1 for p in posts if p["is_tech"]),
            "tech_keyword_breadth": tech_hits,
            "posts": posts[:10],
            "source": "blog_scrape",
        }
    except Exception as e:
        logger.debug("Blog fetch failed for %s: %s", blog_url, e)
        return {"error": str(e)[:200], "posts": []}


# ─── Hireability scoring (deterministic, skill/activity signals only) ───
# Deliberately blind to name, gender, school, photo, location — same fairness
# rule as the hiring-agent resume evaluator.

DIMENSIONS = ("code_evidence", "projects", "knowledge_sharing", "production_experience", "presentation")
WEIGHTS = {
    "code_evidence": 35,
    "projects": 25,
    "knowledge_sharing": 15,
    "production_experience": 15,
    "presentation": 10,
}


def compute_hireability(
    github: dict | None = None,
    portfolio: dict | None = None,
    medium: dict | None = None,
    blog: dict | None = None,
    resume_eval: dict | None = None,
) -> dict:
    """Combine all fetched signals into a 0-100 hireability report."""
    github = github or {}
    portfolio = portfolio or {}
    medium = medium or {}
    blog = blog or {}

    evidence: dict[str, list[str]] = {d: [] for d in DIMENSIONS}
    scores: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
    sources_loaded = 0
    sources_total = 4  # github, portfolio, medium/blog (one slot), resume

    # ── Code evidence (35) ──
    prof = (github.get("github_profile", {}) or {}).get("profile", {}) or {}
    analysis = github.get("github_analysis", {}) or {}
    gh_ok = bool(prof) and "error" not in (github.get("github_profile", {}) or {})
    if gh_ok:
        sources_loaded += 1
        followers = prof.get("followers", 0) or 0
        repos = prof.get("public_repos", 0) or 0
        stars = (github.get("github_profile", {}) or {}).get("total_stars", 0) or 0
        langs = (github.get("github_profile", {}) or {}).get("languages", {}) or {}
        oss = (github.get("github_oss", {}) or {})
        prs = oss.get("total_prs", 0) or 0
        contrib = (github.get("github_contributions", {}) or {})
        streak = contrib.get("longest_streak", 0) or 0

        s = 0.0
        if repos >= 5:
            s += 8
            evidence["code_evidence"].append(f"{repos} public repos")
        elif repos >= 1:
            s += 4
        if stars >= 50:
            s += 9
            evidence["code_evidence"].append(f"{stars} total stars")
        elif stars >= 5:
            s += 5
        if len(langs) >= 3:
            s += 6
            evidence["code_evidence"].append(f"{len(langs)} languages: {', '.join(list(langs)[:4])}")
        elif langs:
            s += 3
        if prs >= 5:
            s += 7
            evidence["code_evidence"].append(f"{prs} OSS pull requests")
        elif prs >= 1:
            s += 4
        if streak >= 30:
            s += 5
            evidence["code_evidence"].append(f"{streak}-day contribution streak")
        elif streak >= 7:
            s += 2
        if followers >= 50:
            evidence["code_evidence"].append(f"{followers} followers")
        skills = analysis.get("skills", []) or []
        if len(skills) >= 5:
            evidence["code_evidence"].append(f"{len(skills)} detected skills")
        scores["code_evidence"] = min(WEIGHTS["code_evidence"], s)
    else:
        evidence["code_evidence"].append("No GitHub data — connect a profile to score this")

    # ── Projects / portfolio (25) ──
    pf_ok = bool(portfolio) and "error" not in portfolio
    if pf_ok:
        sources_loaded += 1
        s = 10.0  # has a working portfolio site at all
        evidence["projects"].append("Portfolio site live")
        projects = portfolio.get("projects", []) or portfolio.get("project_list", []) or []
        if len(projects) >= 3:
            s += 8
            evidence["projects"].append(f"{len(projects)} showcased projects")
        elif projects:
            s += 4
        techs = portfolio.get("technologies_detected", []) or portfolio.get("skills", []) or []
        if len(techs) >= 5:
            s += 7
            evidence["projects"].append(f"Stack breadth: {', '.join([str(t) for t in techs[:5]])}")
        elif techs:
            s += 3
        scores["projects"] = min(WEIGHTS["projects"], s)
    else:
        evidence["projects"].append("No portfolio data")

    # ── Knowledge sharing (15): Medium + blog share one slot ──
    writing_loaded = False
    med_posts = medium.get("posts", []) if "error" not in medium else []
    blog_posts = blog.get("posts", []) if "error" not in blog else []
    if med_posts or blog_posts:
        writing_loaded = True
        sources_loaded += 1
    if writing_loaded:
        tech_total = (medium.get("tech_posts", 0) if med_posts else 0) + (blog.get("tech_posts", 0) if blog_posts else 0)
        total = len(med_posts) + len(blog_posts)
        s = 0.0
        if total >= 5:
            s += 5
            evidence["knowledge_sharing"].append(f"{total} posts published")
        elif total >= 1:
            s += 2
        if tech_total >= 5:
            s += 7
            evidence["knowledge_sharing"].append(f"{tech_total} technical posts")
        elif tech_total >= 1:
            s += 4
        code_posts = sum(1 for p in med_posts if p.get("has_code"))
        if code_posts:
            s += 3
            evidence["knowledge_sharing"].append(f"{code_posts} posts with code")
        scores["knowledge_sharing"] = min(WEIGHTS["knowledge_sharing"], s)
    else:
        evidence["knowledge_sharing"].append("No writing found — technical blogging adds signal")

    # ── Production experience (15): resume eval if present, else GitHub proxy ──
    if resume_eval:
        sources_loaded += 1
        rscores = (resume_eval.get("scores", {}) or {})
        prod = (rscores.get("production", {}) or {}).get("score", 0) or 0  # 0-25 scale
        scores["production_experience"] = round(min(WEIGHTS["production_experience"], prod * 0.6), 1)
        for st in resume_eval.get("key_strengths", [])[:2]:
            evidence["production_experience"].append(str(st)[:160])
    elif gh_ok:
        consistency = ((github.get("github_commit_analysis", {}) or {}).get("consistency_score", 0)) or 0
        s = min(8.0, consistency / 12.5)  # 0-100 → 0-8
        level = (analysis.get("experience_level", "") or "")
        if level and level != "unknown":
            s += 4
            evidence["production_experience"].append(f"GitHub-derived level: {level}")
        scores["production_experience"] = round(min(WEIGHTS["production_experience"], s), 1)
    else:
        evidence["production_experience"].append("No experience data — add a resume or GitHub")

    # ── Presentation (10): links valid, profiles complete ──
    s = 0.0
    social = github.get("social_links", {}) or {}
    if prof.get("bio"):
        s += 3
        evidence["presentation"].append("GitHub bio present")
    if prof.get("avatar_url"):
        s += 1
    if social.get("blog_url") or social.get("portfolio_url"):
        s += 3
        evidence["presentation"].append("Blog/portfolio linked from GitHub")
    if social.get("linkedin_url"):
        s += 2
        evidence["presentation"].append("LinkedIn linked")
    if social.get("twitter_handle"):
        s += 1
        evidence["presentation"].append("X handle linked")
    scores["presentation"] = min(WEIGHTS["presentation"], s)

    total = round(sum(scores.values()), 1)
    if total >= 80:
        band, recommendation = "strong_hire", "Strong hire signal — prioritize for interview loop."
    elif total >= 60:
        band, recommendation = "hire", "Solid hire signal — move to technical screen."
    elif total >= 40:
        band, recommendation = "consider", "Mixed signal — probe gaps in screening call."
    else:
        band, recommendation = "pass", "Weak public signal — needs stronger evidence to advance."

    confidence = round(sources_loaded / sources_total, 2)
    return {
        "score": total,
        "band": band,
        "recommendation": recommendation,
        "confidence": confidence,
        "sources_loaded": sources_loaded,
        "dimensions": [
            {"name": d, "score": round(scores[d], 1), "max": WEIGHTS[d], "evidence": evidence[d]}
            for d in DIMENSIONS
        ],
        "generated_at": datetime.now(UTC).isoformat(),
        "fairness_note": "Scored on skills and public activity only — never on name, gender, school, photo, or location.",
    }
