"""
Search adapters for AgentForge.

Provides a unified search interface across multiple sources:
- Google Custom Search API
- SerpAPI for structured job results
- Direct web scraping fallback (built-in, no API key needed)
- Job board scraping (Indeed, LinkedIn, Glassdoor via web search)

All methods fall back gracefully when APIs are unavailable.
"""

import logging
import re
from typing import Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger("agentforge.search")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


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
        """
        results = []

        # Prepend type-specific keywords
        if source_filter == "internship" and not any(k in query.lower() for k in ["intern", "internship", "fellowship"]):
            query = f"internship {query}"
        elif source_filter == "job" and not any(k in query.lower() for k in ["job", "full-time", "position", "hiring"]):
            query = f"job {query}"

        # ── Source 1: Google Custom Search ──
        if settings.google_api_key and settings.google_cse_id:
            try:
                google_results = await self._search_google(query, location, limit)
                results.extend(google_results)
                logger.info("Google returned %d results", len(google_results))
            except Exception as e:
                logger.warning("Google search failed: %s", e)

        # ── Source 2: SerpAPI Google Jobs ──
        if settings.serpapi_key:
            try:
                serp_results = await self._search_serpapi(query, location, limit)
                results.extend(serp_results)
                logger.info("SerpAPI returned %d results", len(serp_results))
            except Exception as e:
                logger.warning("SerpAPI search failed: %s", e)

        # ── Source 3: Direct web scraping (always available) ──
        if not results or len(results) < limit:
            try:
                scraped = await self._scrape_web(query, location, limit - len(results))
                results.extend(scraped)
                logger.info("Web scrape returned %d results", len(scraped))
            except Exception as e:
                logger.warning("Web scrape failed: %s", e)

        # ── Source 4: Job board scraping for job/internship queries ──
        if source_filter in ("job", "internship") and len(results) < limit:
            try:
                board_results = await self._scrape_job_boards(query, location, limit - len(results), source_filter)
                results.extend(board_results)
                logger.info("Job boards returned %d results", len(board_results))
            except Exception as e:
                logger.warning("Job board scrape failed: %s", e)

        # Deduplicate by (title, company) pair
        seen = set()
        deduped = []
        for r in results:
            key = (r.get("title", "").lower().strip(), r.get("company", "").lower().strip())
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        return deduped[:limit]

    async def search_research(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search the web for research purposes — company info, interview prep, market trends.
        Uses web search and returns structured snippets.
        """
        results = []

        # Try Google first
        if settings.google_api_key and settings.google_cse_id:
            try:
                google_results = await self._search_google(query, None, limit)
                results.extend(google_results)
            except Exception:
                pass

        # Try Tavily (AI-native search, great for research)
        if settings.tavily_api_key:
            try:
                tavily_results = await self._search_tavily(query, limit)
                results.extend(tavily_results)
                logger.info("Tavily returned %d results", len(tavily_results))
            except Exception as e:
                logger.warning("Tavily search failed: %s", e)

        # Fallback: scrape search results
        if not results:
            try:
                scraped = await self._scrape_search_results(query, limit)
                results.extend(scraped)
            except Exception as e:
                logger.debug("Research scrape failed: %s", e)

        return results[:limit]

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
            results.append({
                "title": job.get("title"),
                "company": job.get("company_name"),
                "location": job.get("location"),
                "description": job.get("description", ""),
                "apply_url": (
                    job.get("related_links", [{}])[0].get("link")
                    if job.get("related_links") else None
                ),
                "source": "serpapi",
                "remote": "remote" in (job.get("description", "") or "").lower(),
                "salary": self._extract_salary(job.get("description", "")),
            })

        return results

    # ─── Direct Web Scraping ───────────────────────────────

    def _parse_serp_results(self, soup, limit: int = 5, source: str = "web_scrape") -> list[dict]:
        """
        Parse Google SERP HTML into structured results.
        Returns dicts with title, company, description/snippet, apply_url/url.
        """
        results = []
        for g in soup.select("div.g"):
            if len(results) >= limit:
                break
            title_el = g.select_one("h3")
            link_el = g.select_one("a")
            snippet_el = g.select_one("span.aCOpRe, div.VwiC3b, span.st")
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
        for g in soup.select("div.g"):
            if len(results) >= limit:
                break
            title_el = g.select_one("h3")
            link_el = g.select_one("a")
            snippet_el = g.select_one("span.aCOpRe, div.VwiC3b")
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
        """
        q = query
        if location:
            q += f" {location}"

        search_url = f"https://www.google.com/search?q={quote_plus(q)}&num={min(limit, 10)}"
        headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:
            try:
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    return self._parse_serp_results(soup, limit)
            except Exception as e:
                logger.debug("Web scrape failed: %s", e)

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

        # Build site-specific search queries
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

        headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
        results = []

        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:
            for url in board_queries:
                if len(results) >= limit:
                    break
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    results.extend(
                        self._parse_serp_results(soup, limit - len(results), source="job_board_scrape")
                    )
                except Exception as e:
                    logger.debug("Board scrape failed for %s: %s", url, e)

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
        headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={min(limit, 10)}"

        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:
            try:
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    return self._parse_serp_results_research(soup, limit)
            except Exception as e:
                logger.debug("Research scrape failed: %s", e)

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

        # Pattern: "Title at Company"
        m = re.search(r'\bat\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s+[–-]|\s+\||\s+-\s+|$|\.|\))', text)
        if m:
            return m.group(1).strip()[:50]

        # Pattern: "Company hiring"
        m = re.search(r'([A-Z][A-Za-z0-9\s&.]+?)\s+(?:hiring|jobs|cares?ers|recruiting)', text)
        if m:
            return m.group(1).strip()[:50]

        # Pattern: "Company - Title"
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
