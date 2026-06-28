"""
Search adapters for AgentForge.

Provides a unified search interface across multiple sources:
- Google Custom Search API
- SerpAPI for structured job results
- Tavily AI-native search (purpose-built for agents)
- Direct web scraping fallback (built-in, no API key needed)
- DuckDuckGo scraping (resilient fallback)
- Job board scraping (Indeed, LinkedIn, Glassdoor via web search)
- LinkedIn direct scraping

All methods fall back gracefully when APIs are unavailable.
Results are cached in-memory with TTL to reduce API calls.
"""

import asyncio
import logging
import random
import re
import time
from typing import Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger("agentforge.search")

# ─── User-Agent Rotation ────────────────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
]


def _get_user_agent() -> str:
    """Return a random User-Agent string per-call to avoid detection."""
    return random.choice(_USER_AGENTS)


_SCRAPE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


async def _scrape_with_retry(
    fetch_coro,
    max_retries: int = 2,
    base_delay: float = 1.0,
) -> tuple[Optional[httpx.Response], Optional[str]]:
    """
    Execute an async scrape with random delay between retries.
    Returns (response, error_message).
    """
    last_error = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            await asyncio.sleep(delay)
        try:
            resp = await fetch_coro()
            return resp, None
        except Exception as e:
            last_error = str(e)
            logger.debug("Scrape attempt %d/%d failed: %s", attempt + 1, max_retries + 1, e)
    return None, last_error


def _make_headers() -> dict:
    """Build headers dict with a fresh random User-Agent per-call."""
    h = dict(_SCRAPE_HEADERS)
    h["User-Agent"] = _get_user_agent()
    return h


async def _safe_get(url: str, headers: dict, follow_redirects: bool = True, timeout: int = 10) -> httpx.Response:
    """HTTP GET with proper AsyncClient context manager to avoid resource leaks."""
    async with httpx.AsyncClient(headers=headers, follow_redirects=follow_redirects, timeout=timeout) as client:
        return await client.get(url)


async def _safe_post(url: str, headers: dict, data: Optional[dict] = None, follow_redirects: bool = True, timeout: int = 15) -> httpx.Response:
    """HTTP POST with proper AsyncClient context manager to avoid resource leaks."""
    async with httpx.AsyncClient(headers=headers, follow_redirects=follow_redirects, timeout=timeout) as client:
        return await client.post(url, data=data)


# ─── In-Memory Search Cache ─────────────────────────────────
CACHE_TTL = 300  # 5 minutes
_search_cache: dict[str, tuple[float, list[dict]]] = {}


def _cache_key(query: str, source_filter: Optional[str] = None, location: Optional[str] = None) -> str:
    return f"{source_filter or 'all'}:{location or ''}:{query.lower().strip()}"


def _get_cached(key: str) -> Optional[list[dict]]:
    entry = _search_cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        logger.debug("Search cache HIT for key: %s", key[:60])
        return entry[1]
    if entry:
        logger.debug("Search cache EXPIRED for key: %s", key[:60])
        _search_cache.pop(key, None)
    return None


def _set_cache(key: str, results: list[dict]):
    _search_cache[key] = (time.time(), results)
    logger.debug("Search cache SET for key: %s (%d results)", key[:60], len(results))


def _log_api_key_status():
    """Log which search API keys are available (call once at startup)."""
    keys = {
        "google_api_key": bool(settings.google_api_key),
        "google_cse_id": bool(settings.google_cse_id),
        "serpapi_key": bool(settings.serpapi_key),
        "tavily_api_key": bool(settings.tavily_api_key),
        "brave_api_key": bool(settings.brave_api_key),
        "exa_api_key": bool(settings.exa_api_key),
        "mojeek_api_key": bool(settings.mojeek_api_key),
        "searxng_base_url": bool(settings.searxng_base_url),
    }
    available = [k for k, v in keys.items() if v]
    missing = [k for k, v in keys.items() if not v]
    if available:
        logger.info("Search API keys available: %s", ", ".join(available))
    if missing:
        logger.warning("Search API keys MISSING: %s — falling back to web scraping", ", ".join(missing))


# Run once at import time
_log_api_key_status()


class SearchAdapter:
    """
    Unified search interface. Aggregates results from multiple sources.
    Tries real APIs first, then falls back to direct web scraping.
    """

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        skills: Optional[list[str]] = None,
        limit: int = 10,
        source_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Search across all available sources and return deduplicated results.
        source_filter can be 'internship', 'job', 'research', or None for all.

        Results are cached in-memory for CACHE_TTL seconds.
        Falls back gracefully through all sources if APIs are unavailable.
        """
        # Normalize source_filter
        if source_filter:
            source_filter = source_filter.lower().strip()
            # Normalize plurals: "internships" -> "internship", "jobs" -> "job"
            if source_filter in ("internships", "internship"):
                source_filter = "internship"
            elif source_filter in ("jobs", "job"):
                source_filter = "job"

        # ── Check cache first ──
        cache_key = _cache_key(query, source_filter, location)
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached[:limit]

        results = []

        # Prepend type-specific keywords
        if source_filter == "internship" and not any(k in query.lower() for k in ["intern", "internship", "fellowship"]):
            query = f"internship {query}"
        elif source_filter == "job" and not any(k in query.lower() for k in ["job", "full-time", "position", "hiring"]):
            query = f"job {query}"

        # ── Is this a job/internship search? ──
        is_job_search = source_filter in ("job", "internship")

        # ── Source 1: SerpAPI Google Jobs (returns REAL structured job listings with company, location, salary) ──
        if settings.serpapi_key:
            try:
                serp_results = await self._search_serpapi(query, location, limit)
                # Ensure every result has a company name
                for r in serp_results:
                    if not r.get("company"):
                        r["company"] = self._extract_company(r.get("title", ""), r.get("description", ""))
                results.extend(serp_results)
                logger.info("SerpAPI returned %d results", len(serp_results))
            except Exception as e:
                logger.warning("SerpAPI search failed: %s", e)

        # ── For job/internship searches: SerpAPI is the primary source. ──
        # Skip generic web search sources (Tavily, Exa, Brave, Google CSE, Mojeek, scrapes)
        # if SerpAPI already returned enough real job results. These sources return
        # generic web pages ABOUT jobs (e.g. "Internships at University of X"), not actual listings.
        if is_job_search and len(results) >= limit:
            logger.info(
                "SerpAPI returned enough results (%d) for job/internship search — "
                "skipping generic web search sources to avoid polluting with non-job results",
                len(results),
            )
        else:
            # ── Source 2: Tavily (AI-native, best for agents) ──
            if settings.tavily_api_key:
                try:
                    tavily_results = await self._search_tavily(query, limit)
                    # Enrich Tavily results (no native company/type/skills fields)
                    for r in tavily_results:
                        if not r.get("company"):
                            r["company"] = self._extract_company(r.get("title", ""), r.get("snippet", ""))
                        if not r.get("type"):
                            r["type"] = self._extract_job_type(r.get("title", ""), r.get("description", "") or r.get("snippet", ""))
                        if not r.get("skills"):
                            r["skills"] = self._extract_skills(r.get("description", "") or r.get("snippet", "") or r.get("title", ""))
                    results.extend(tavily_results)
                    logger.info("Tavily returned %d results", len(tavily_results))
                except Exception as e:
                    logger.warning("Tavily search failed: %s", e)

            # ── Source 3: Google Custom Search ──
            if settings.google_api_key and settings.google_cse_id:
                try:
                    google_results = await self._search_google(query, location, limit)
                    results.extend(google_results)
                    logger.info("Google returned %d results", len(google_results))
                except Exception as e:
                    logger.warning("Google search failed: %s", e)

            # ── Source 4: Brave Search (free tier: 2,000 queries/month) ──
            if settings.brave_api_key:
                try:
                    brave_results = await self._search_brave(query, limit)
                    results.extend(brave_results)
                    logger.info("Brave returned %d results", len(brave_results))
                except Exception as e:
                    logger.warning("Brave search failed: %s", e)

            # ── Source 5: Exa (AI-native search) ──
            if settings.exa_api_key:
                try:
                    exa_results = await self._search_exa(query, limit)
                    # Enrich Exa results (no native company/type/skills fields)
                    for r in exa_results:
                        if not r.get("company"):
                            r["company"] = self._extract_company(r.get("title", ""), r.get("snippet", ""))
                        if not r.get("type"):
                            r["type"] = self._extract_job_type(r.get("title", ""), r.get("description", "") or r.get("snippet", ""))
                        if not r.get("skills"):
                            r["skills"] = self._extract_skills(r.get("description", "") or r.get("snippet", "") or r.get("title", ""))
                    results.extend(exa_results)
                    logger.info("Exa returned %d results", len(exa_results))
                except Exception as e:
                    logger.warning("Exa search failed: %s", e)

            # ── Source 6: SearXNG (self-hosted meta search) ──
            if settings.searxng_base_url:
                try:
                    searxng_results = await self._search_searxng(query, limit)
                    results.extend(searxng_results)
                    logger.info("SearXNG returned %d results", len(searxng_results))
                except Exception as e:
                    logger.warning("SearXNG search failed: %s", e)

            # ── Source 7: Mojeek (privacy-focused, free tier) ──
            if settings.mojeek_api_key:
                try:
                    mojeek_results = await self._search_mojeek_api(query, limit)
                    results.extend(mojeek_results)
                    logger.info("Mojeek API returned %d results", len(mojeek_results))
                except Exception as e:
                    logger.warning("Mojeek API search failed: %s", e)

            # ── Source 8: Direct web scraping (always available, no API key) ──
            if not results or len(results) < limit:
                try:
                    scraped = await self._scrape_web(query, location, limit - len(results))
                    results.extend(scraped)
                    logger.info("Web scrape returned %d results", len(scraped))
                except Exception as e:
                    logger.warning("Web scrape failed: %s", e)

            # ── Source 9: Mojeek Scrape Fallback ──
            if not results or len(results) < limit:
                try:
                    mojeek_scraped = await self._scrape_mojeek(query, location, limit - len(results))
                    results.extend(mojeek_scraped)
                    logger.info("Mojeek scrape returned %d results", len(mojeek_scraped))
                except Exception as e:
                    logger.warning("Mojeek scrape failed: %s", e)

            # ── Source 10: DuckDuckGo Fallback ──
            if not results or len(results) < limit:
                try:
                    ddg_scraped = await self._scrape_duckduckgo(query, location, limit - len(results))
                    results.extend(ddg_scraped)
                    logger.info("DuckDuckGo scrape returned %d results", len(ddg_scraped))
                except Exception as e:
                    logger.warning("DuckDuckGo scrape failed: %s", e)

        # ── Job board scraping for job/internship queries (tries to find real listings) ──
        if source_filter in ("job", "internship") and len(results) < limit:
            try:
                board_results = await self._scrape_job_boards(query, location, limit - len(results), source_filter)
                results.extend(board_results)
                logger.info("Job boards returned %d results", len(board_results))
            except Exception as e:
                logger.warning("Job board scrape failed: %s", e)

        # ── LinkedIn Direct Scraping ──
        if source_filter in ("job", "internship") and len(results) < limit:
            try:
                li_results = await self._scrape_linkedin_direct(query, location, limit - len(results))
                results.extend(li_results)
                logger.info("LinkedIn Direct returned %d results", len(li_results))
            except Exception as e:
                logger.warning("LinkedIn Direct scrape failed: %s", e)

        # Log warning if ALL sources returned nothing
        if not results:
            logger.warning(
                "All search sources returned 0 results for query='%s' location='%s' filter='%s'. "
                "Agents will fall back to demo data.",
                query, location, source_filter,
            )

        # ── Quality filter: for job/internship results, prioritize real company names ──
        # This ensures SerpAPI's real job listings come before Tavily/Exa's generic web pages.
        if is_job_search and results:
            real = [r for r in results if r.get("company") and r["company"] != "Tech Company"]
            generic = [r for r in results if not r.get("company") or r["company"] == "Tech Company"]
            results = real + generic
            if generic:
                logger.debug("Quality filter: %d real results, %d generic ('Tech Company') deprioritized", len(real), len(generic))

        # Deduplicate by (title, company) pair
        seen = set()
        deduped = []
        for r in results:
            key = (r.get("title", "").lower().strip(), r.get("company", "").lower().strip())
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        result_slice = deduped[:limit]

        # Cache the result
        if result_slice:
            _set_cache(cache_key, result_slice)

        return result_slice

    async def search_research(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search the web for research purposes — company info, interview prep, market trends.
        Uses web search and returns structured snippets.
        Results are cached in-memory for CACHE_TTL seconds.
        """
        cache_key = _cache_key(query, "research", None)
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached[:limit]

        results = []

        # Try Tavily first (AI-native, best for research)
        if settings.tavily_api_key:
            try:
                tavily_results = await self._search_tavily(query, limit)
                results.extend(tavily_results)
                logger.info("Tavily returned %d results", len(tavily_results))
            except Exception as e:
                logger.warning("Tavily search failed: %s", e)

        # Try Google second
        if not results and settings.google_api_key and settings.google_cse_id:
            try:
                google_results = await self._search_google(query, None, limit)
                results.extend(google_results)
                logger.info("Google returned %d results (research)", len(google_results))
            except Exception as e:
                logger.warning("Google research search failed: %s", e)

        # Try Brave (free tier)
        if not results and settings.brave_api_key:
            try:
                brave_results = await self._search_brave(query, limit)
                results.extend(brave_results)
                logger.info("Brave returned %d results (research)", len(brave_results))
            except Exception as e:
                logger.warning("Brave research search failed: %s", e)

        # Try Exa (AI-native)
        if not results and settings.exa_api_key:
            try:
                exa_results = await self._search_exa(query, limit)
                results.extend(exa_results)
                logger.info("Exa returned %d results (research)", len(exa_results))
            except Exception as e:
                logger.warning("Exa research search failed: %s", e)

        # Try Mojeek (privacy-first, free tier)
        if not results and settings.mojeek_api_key:
            try:
                mojeek_results = await self._search_mojeek_api(query, limit)
                results.extend(mojeek_results)
                logger.info("Mojeek returned %d results (research)", len(mojeek_results))
            except Exception as e:
                logger.warning("Mojeek research search failed: %s", e)

        # Fallback: scrape search results
        if not results:
            try:
                scraped = await self._scrape_search_results(query, limit)
                results.extend(scraped)
                logger.info("Research scrape returned %d results", len(scraped))
            except Exception as e:
                logger.debug("Research scrape failed: %s", e)

        if not results:
            logger.warning(
                "All research search sources returned 0 results for query='%s'",
                query,
            )

        result_slice = results[:limit]
        if result_slice:
            _set_cache(cache_key, result_slice)
        return result_slice

    async def get_suggestions(self, query: str) -> list[str]:
        """Fetch search suggestions from Google Autocomplete API."""
        if not query:
            return []
            
        url = "http://suggestqueries.google.com/complete/search"
        params = {"client": "chrome", "q": query}
        async with httpx.AsyncClient(timeout=5) as client:
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if len(data) > 1 and isinstance(data[1], list):
                        return data[1][:5]
            except Exception as e:
                logger.debug("Failed to get suggestions: %s", e)
        return []

    # ─── Google Custom Search ──────────────────────────────

    async def _search_google(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search using Google Custom Search API."""
        q = query
        if location:
            q += f" {location}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": settings.google_api_key,
                    "cx": settings.google_cse_id,
                    "q": f"{q}",
                    "num": min(limit, 10),
                },
                timeout=10,
            )
            data = resp.json()

        if "error" in data:
            raise RuntimeError(data["error"].get("message", "Google API error"))

        results = []
        for item in data.get("items", []):
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            company = self._extract_company(title, snippet)

            results.append({
                "title": title,
                "company": company,
                "description": snippet,
                "apply_url": link,
                "source": "google",
                "remote": "remote" in (snippet or "").lower(),
            })

        return results

    # ─── SerpAPI ───────────────────────────────────────────

    async def _search_serpapi(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search using SerpAPI for structured job results."""
        q = query
        if location:
            q += f" {location}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "api_key": settings.serpapi_key,
                    "engine": "google_jobs",
                    "q": q,
                    "hl": "en",
                },
                timeout=10,
            )
            data = resp.json()

        results = []
        for job in data.get("jobs_results", [])[:limit]:
            desc = job.get("description", "") or ""
            title = job.get("title", "") or ""
            detected = job.get("detected_extensions", {}) or {}
            schedule_type = (detected.get("schedule_type") or "").lower()
            if any(t in schedule_type for t in ["intern", "internship"]):
                job_type = "Internship"
            elif any(t in schedule_type for t in ["full-time", "full time"]):
                job_type = "Full-time"
            elif any(t in schedule_type for t in ["part-time", "part time", "contract"]):
                job_type = "Part-time"
            else:
                job_type = self._extract_job_type(title, desc)
            results.append({
                "title": job.get("title"),
                "company": job.get("company_name"),
                "location": job.get("location"),
                "description": desc,
                "apply_url": (
                    job.get("related_links", [{}])[0].get("link")
                    if job.get("related_links") else None
                ),
                "source": "serpapi",
                "type": job_type,
                "skills": self._extract_skills(desc),
                "remote": "remote" in desc.lower(),
                "salary": self._extract_salary(desc),
            })

        return results

    # ─── Direct Web Scraping ───────────────────────────────

    def _parse_serp_results(self, soup, limit: int = 5, source: str = "web_scrape") -> list[dict]:
        """
        Parse Google SERP HTML into structured results.
        Uses multiple fallback selectors as Google's class names change frequently.
        Returns dicts with title, company, description/snippet, apply_url/url.
        """
        results = []

        # Multi-selector strategy: try modern selectors first, then fallback
        result_selectors = [
            "div.g",
            "div[data-hveid]",
            "div[data-sokoban-container]",
            "div[role='heading'] ~ div",
            "div.N54G5d",       # newer Google result container
            "div.Wt5Tfe",       # another modern container
            "div[jscontroller]",    # Google's newer JS-driven layout
            "div.yuRUbf",       # title+link wrapper in modern Google
        ]
        result_blocks = []
        for sel in result_selectors:
            result_blocks = soup.select(sel)
            if len(result_blocks) >= 1:
                break

        for g in result_blocks:
            if len(results) >= limit:
                break
            title_el = (
                g.select_one("h3")
                or g.select_one("[role='heading']")
                or g.select_one("a[href^='http']")
            )
            link_el = g.select_one("a[href^='http']") or g.select_one("a")
            snippet_el = (
                g.select_one("span.aCOpRe, div.VwiC3b, span.st, div[data-sncf], div.lEBKkf, span.st")
                or g.select_one("div[style*='-webkit-line-clamp']")
                or g.select_one(".VwiC3b")
                or g.select_one("[data-sncf]")
                or g.select_one("span.aCOpRe")
            )
            if title_el and link_el:
                title = title_el.get_text(strip=True)
                link = link_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                company = self._extract_company(title, snippet)
                results.append({
                    "title": title,
                    "company": company,
                    "description": snippet[:500],
                    "apply_url": link,
                    "source": source,
                    "remote": "remote" in (snippet or "").lower(),
                })
        return results

    def _parse_serp_results_research(self, soup, limit: int = 5) -> list[dict]:
        """Parse Google SERP HTML into research-style results (snippet/url keys)."""
        results = []

        result_selectors = [
            "div.g",
            "div[data-hveid]",
            "div[data-sokoban-container]",
            "div.N54G5d",
            "div.Wt5Tfe",
            "div[jscontroller]",
        ]
        result_blocks = []
        for sel in result_selectors:
            result_blocks = soup.select(sel)
            if len(result_blocks) >= 1:
                break

        for g in result_blocks:
            if len(results) >= limit:
                break
            title_el = (
                g.select_one("h3")
                or g.select_one("[role='heading']")
                or g.select_one("a[href^='http']")
            )
            link_el = g.select_one("a[href^='http']") or g.select_one("a")
            snippet_el = (
                g.select_one("span.aCOpRe, div.VwiC3b, span.st, div[data-sncf]")
                or g.select_one("div[style*='-webkit-line-clamp']")
                or g.select_one(".VwiC3b")
                or g.select_one("[data-sncf]")
            )
            if title_el and link_el:
                title = title_el.get_text(strip=True)
                link = link_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                results.append({
                    "title": title,
                    "snippet": snippet[:500],
                    "url": link,
                    "source": "web_research",
                })
        return results

    async def _scrape_web(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Scrape search engine results for job listings.
        Uses Google search as the primary source (no API key needed).
        Retries with User-Agent rotation and random delays.
        """
        q = query
        if location:
            q += f" {location}"

        search_url = f"https://www.google.com/search?q={quote_plus(q)}&num={min(limit, 10)}"
        headers = _make_headers()

        resp, error = await _scrape_with_retry(
            lambda: _safe_get(search_url, headers, follow_redirects=True, timeout=10)
        )
        if resp and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_serp_results(soup, limit)

        logger.debug("Web scrape failed: %s", error or f"status={resp.status_code if resp else 'no response'}")
        return []

    async def _scrape_job_boards(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 5,
        source_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Scrape job board listings via Google site: search.
        Targets LinkedIn, SimplyHired, and Glassdoor.
        """
        q = query
        loc = location or ""

        board_queries = []
        indeed_q = quote_plus(f"{q} internship" if source_filter == "internship" else q)
        indeed_loc = quote_plus(loc) if loc else ""
        board_queries.append(
            f"https://www.indeed.com/jobs?q={indeed_q}"
            f"{'&l=' + indeed_loc if indeed_loc else ''}"
        )
        for site in ["linkedin.com/jobs", "simplyhired.com", "glassdoor.com"]:
            board_queries.append(
                f"https://www.google.com/search?q={quote_plus(f'site:{site} {q} {loc}')}&num=10"
            )

        results = []
        for url in board_queries:
            if len(results) >= limit:
                break
            resp, error = await _scrape_with_retry(
                lambda u=url, h=_make_headers(): _safe_get(u, h, follow_redirects=True, timeout=10)
            )
            if resp and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results.extend(
                    self._parse_serp_results(soup, limit - len(results), source="job_board_scrape")
                )
            else:
                logger.debug("Board scrape failed for %s: %s", url, error)

        return results

    async def _scrape_search_results(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Scrape Google search results for research queries
        (company info, interview prep, market trends).
        """
        headers = _make_headers()
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={min(limit, 10)}"

        resp, error = await _scrape_with_retry(
            lambda: _safe_get(search_url, headers, follow_redirects=True, timeout=10)
        )
        if resp and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_serp_results_research(soup, limit)

        logger.debug("Research scrape failed: %s", error)
        return []

    async def _scrape_duckduckgo(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Scrape DuckDuckGo HTML search as a resilient fallback."""
        q = query
        if location:
            q += f" {location}"
            
        url = "https://html.duckduckgo.com/html/"
        headers = _make_headers()
        
        resp, error = await _scrape_with_retry(
            lambda: _safe_post(url, headers, data={"q": q}),
            max_retries=1,
        )
        if resp and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for a in soup.select("a.result__url"):
                if len(results) >= limit:
                    break
                link = a.get("href", "")
                result_div = a.find_parent("div", class_="result")
                title_el = result_div.select_one("h2.result__title a") if result_div else None
                snippet_el = result_div.select_one("a.result__snippet") if result_div else None
                
                title = title_el.get_text(strip=True) if title_el else "Unknown"
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                
                company = self._extract_company(title, snippet)
                results.append({
                    "title": title,
                    "company": company,
                    "description": snippet[:500],
                    "apply_url": link,
                    "source": "duckduckgo_scrape",
                    "remote": "remote" in snippet.lower(),
                })
            return results

        logger.debug("DuckDuckGo scrape failed: %s", error)
        return []

    async def _scrape_linkedin_direct(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Scrape LinkedIn jobs directory without auth."""
        params = {"keywords": query}
        if location:
            params["location"] = location
            
        url = "https://www.linkedin.com/jobs/search"
        headers = _make_headers()
        
        resp, error = await _scrape_with_retry(
            lambda: _safe_get(url, headers, follow_redirects=True, timeout=15),
            max_retries=1,
        )
        if resp and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for job_card in soup.select("ul.jobs-search__results-list li"):
                if len(results) >= limit:
                    break
                title_el = job_card.select_one("h3.base-search-card__title")
                company_el = job_card.select_one("h4.base-search-card__subtitle")
                link_el = job_card.select_one("a.base-card__full-link")
                loc_el = job_card.select_one("span.job-search-card__location")
                
                if title_el and company_el:
                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True)
                    link = link_el.get("href", "") if link_el else ""
                    loc = loc_el.get_text(strip=True) if loc_el else ""
                    
                    results.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "description": f"Role at {company} in {loc}",
                        "apply_url": link.split("?")[0],
                        "source": "linkedin_direct",
                        "remote": "remote" in title.lower() or "remote" in loc.lower(),
                    })
            return results

        logger.debug("LinkedIn direct scrape failed: %s", error)
        return []

    # ─── Brave Search ───────────────────────────────────────

    async def _search_brave(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search using Brave Search API (2,000 free queries/month)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={
                    "q": query,
                    "count": min(limit, 20),
                    "safesearch": "moderate",
                },
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": settings.brave_api_key,
                },
                timeout=10,
            )
            data = resp.json()

        results = []
        for r in data.get("web", {}).get("results", [])[:limit]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("description", ""),
                "url": r.get("url", ""),
                "source": "brave",
            })

        return results

    # ─── Exa Search ────────────────────────────────────────────

    async def _search_exa(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search using Exa (formerly Metaphor) — AI-native search API."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.exa.ai/search",
                json={
                    "query": query,
                    "numResults": limit,
                    "useAutoprompt": True,
                    "type": "keyword",
                },
                headers={
                    "Authorization": f"Bearer {settings.exa_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            data = resp.json()

        results = []
        for r in data.get("results", [])[:limit]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("text", "")[:500],
                "url": r.get("url", ""),
                "source": "exa",
            })

        return results

    # ─── SearXNG (Self-Hosted) ────────────────────────────────

    async def _search_searxng(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search using self-hosted SearXNG meta search engine."""
        base_url = settings.searxng_base_url.rstrip("/")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{base_url}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": "en",
                        "categories": "general",
                        "pageno": 1,
                    },
                    timeout=10,
                )
                data = resp.json()
            except Exception as e:
                logger.debug("SearXNG search failed: %s", e)
                return []

        results = []
        for r in data.get("results", [])[:limit]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
                "url": r.get("url", ""),
                "source": "searxng",
            })

        return results

    # ─── Mojeek (API) ──────────────────────────────────────

    async def _search_mojeek_api(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search using Mojeek Search API (free tier available with API key)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.mojeek.com/search",
                params={
                    "api_key": settings.mojeek_api_key,
                    "q": query,
                    "fmt": "json",
                    "t": min(limit, 20),
                    "s": 1,
                },
                timeout=10,
            )
            data = resp.json()

        response = data.get("response", {})
        if response.get("status") != "OK":
            logger.warning("Mojeek API returned non-OK status: %s", response.get("status"))
            return []

        results = []
        for r in response.get("results", [])[:limit]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("desc", ""),
                "url": r.get("url", ""),
                "source": "mojeek",
            })

        return results

    # ─── Mojeek (Scrape, no API key needed) ─────────────────

    async def _scrape_mojeek(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Scrape Mojeek search results as a privacy-first fallback.
        No API key required — Mojeek does not track users.
        """
        q = query
        if location:
            q += f" {location}"

        url = "https://www.mojeek.com/search"

        resp, error = await _scrape_with_retry(
            lambda h=_make_headers(): _safe_get(url, h, follow_redirects=True, timeout=15),
            max_retries=1,
        )
        if resp and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for li in soup.select("li.result"):
                if len(results) >= limit:
                    break

                title_el = li.select_one("h2 a")
                url_el = li.select_one("a")
                desc_el = li.select_one("p.desc") or li.select_one(".description")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link = url_el.get("href", "") if url_el else ""
                snippet = desc_el.get_text(strip=True) if desc_el else ""

                company = self._extract_company(title, snippet)
                results.append({
                    "title": title,
                    "company": company,
                    "description": snippet[:500],
                    "apply_url": link,
                    "source": "mojeek_scrape",
                    "remote": "remote" in (snippet or "").lower(),
                })

            return results

        logger.debug("Mojeek scrape failed: %s", error)
        return []

    # ─── Tavily ────────────────────────────────────────────

    async def _search_tavily(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search using Tavily API — purpose-built for AI research agents."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": limit,
                    "include_answer": False,
                },
                timeout=15,
            )
            data = resp.json()

        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
                "url": r.get("url", ""),
                "source": "tavily",
            })

        return results

    # ─── Utilities ─────────────────────────────────────────

    def _extract_company(self, title: str, snippet: str) -> str:
        """Extract company name from search result text."""
        text = f"{title} {snippet}"

        m = re.search(r'\bat\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s+[–-]|\s+\||\s+-\s+|$|\.|\))', text)
        if m:
            return m.group(1).strip()[:50]

        m = re.search(r'([A-Z][A-Za-z0-9\s&.]+?)\s+(?:hiring|jobs|cares?ers|recruiting)', text)
        if m:
            return m.group(1).strip()[:50]

        m = re.search(r'^([A-Z][A-Za-z0-9\s&.]+?)\s+[-–|]\s+', title)
        if m:
            return m.group(1).strip()[:50]

        return "Tech Company"

    def _extract_salary(self, text: str) -> Optional[str]:
        """Extract salary range from text."""
        m = re.search(r'\$(\d{2,3}[kK]?[\s,]*[-–to]*[\s,]*\$?\d{2,3}[kK]?)', text)
        if m:
            return m.group(1)
        m = re.search(r'(\d{2,3}[kK])\s*[-–]\s*(\d{2,3}[kK])', text)
        if m:
            return f"${m.group(1)}-${m.group(2)}"
        return None

    def _extract_job_type(self, title: str, snippet: str) -> str:
        """Infer job type from title and snippet."""
        text = f"{title} {snippet}".lower()
        if any(t in text for t in ["intern", "internship", "fellowship"]):
            return "Internship"
        if any(t in text for t in ["full-time", "full time"]):
            return "Full-time"
        if any(t in text for t in ["part-time", "part time", "contract", "temporary"]):
            return "Part-time"
        return "Full-time"

    def _extract_skills(self, text: str) -> list[str]:
        """Extract known tech skills from text."""
        text_lower = text.lower()
        found = []
        # Simple keyword matching (no regex issues)
        simple_keywords = [
            "python", "javascript", "typescript", "react", "angular", "vue",
            "java", "go", "golang", "rust", "swift", "kotlin",
            "ruby", "php", "sql", "nosql", "mongodb", "postgresql",
            "mysql", "redis", "aws", "azure", "gcp", "docker", "kubernetes",
            "git", "jenkins", "terraform", "ansible",
            "pytorch", "tensorflow", "pandas", "numpy", "flask", "django",
            "fastapi", "express", "graphql", "devops", "mlops",
            "llm", "rag", "langchain",
        ]
        for k in simple_keywords:
            if re.search(rf'\b{re.escape(k)}\b', text_lower):
                found.append(k)
        # Multi-word / special-char patterns (simple substring check)
        multi_patterns = {
            "machine learning": ["machine learning", "ml"],
            "deep learning": ["deep learning"],
            "artificial intelligence": ["artificial intelligence", "ai"],
            "natural language processing": ["natural language processing", "nlp"],
            "computer vision": ["computer vision"],
            "data science": ["data science"],
            "data engineering": ["data engineering"],
            "data analysis": ["data analysis"],
            "node.js": ["node.js", "nodejs", "node js"],
            "c++": ["c++", "cplusplus"],
            "c#": ["c#", "csharp"],
            ".net": [".net", "dotnet"],
            "scikit-learn": ["scikit-learn", "sklearn"],
            "spring boot": ["spring boot"],
            "ci/cd": ["ci/cd", "cicd"],
            "github actions": ["github actions"],
            "rest api": ["rest api", "restful"],
        }
        for skill, aliases in multi_patterns.items():
            if any(a in text_lower for a in aliases):
                found.append(skill)
        return found
