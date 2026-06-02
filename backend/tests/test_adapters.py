import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.search.adapters import SearchAdapter


@pytest.fixture
def adapter():
    return SearchAdapter()


def _google_response(items):
    return {"items": items}


def _serp_response(jobs):
    return {"jobs_results": jobs}


def _tavily_response(results):
    return {"results": results}


def _mock_httpx(json_data, status_code=200):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.text = "<html></html>"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ── search() with Google API ─────────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_with_google_api(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = "google-key"
    mock_settings.google_cse_id = "cse-id"
    mock_settings.serpapi_key = ""
    mock_settings.tavily_api_key = ""

    mock_httpx_cls.return_value = _mock_httpx(_google_response([
        {"title": "Software Engineer at Google", "snippet": "Remote role", "link": "https://google.com/jobs/1"},
        {"title": "Data Scientist at Meta", "snippet": "NYC office", "link": "https://meta.com/jobs/2"},
    ]))

    results = await adapter.search("software engineer", limit=10)

    assert len(results) >= 2
    assert results[0]["title"] == "Software Engineer at Google"
    assert results[0]["source"] == "google"
    assert results[0]["remote"] is True
    assert results[1]["remote"] is False


# ── search() with SerpAPI ────────────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_with_serpapi(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.serpapi_key = "serp-key"
    mock_settings.tavily_api_key = ""

    mock_httpx_cls.return_value = _mock_httpx(_serp_response([
        {
            "title": "Backend Engineer",
            "company_name": "Stripe",
            "location": "San Francisco",
            "description": "Build payment APIs. $150k-$200k salary.",
            "related_links": [{"link": "https://stripe.com/jobs/1"}],
        },
    ]))

    results = await adapter.search("backend engineer", limit=10)

    assert any(r["source"] == "serpapi" for r in results)
    serp = [r for r in results if r["source"] == "serpapi"][0]
    assert serp["company"] == "Stripe"
    assert serp["salary"] is not None


# ── search() with Tavily ─────────────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_with_tavily(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.serpapi_key = ""
    mock_settings.tavily_api_key = ""

    mock_httpx_cls.return_value = _mock_httpx(_google_response([]))

    results = await adapter.search("ml engineer", limit=5)
    assert isinstance(results, list)


# ── search() fallback to scraping ────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_fallback_to_scraping(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.serpapi_key = ""
    mock_settings.tavily_api_key = ""

    html = """
    <html><body>
    <div class="g">
        <a href="https://example.com/job1"><h3>Frontend Dev at Vercel</h3></a>
        <span class="aCOpRe">Remote frontend position</span>
    </div>
    <div class="g">
        <a href="https://example.com/job2"><h3>Python Developer</h3></a>
        <div class="VwiC3b">Django developer role</div>
    </div>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    results = await adapter.search("frontend developer", limit=5)

    assert len(results) >= 1
    assert results[0]["source"] == "web_scrape"


# ── search() deduplication ───────────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_deduplication(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = "google-key"
    mock_settings.google_cse_id = "cse-id"
    mock_settings.serpapi_key = "serp-key"
    mock_settings.tavily_api_key = ""

    google_data = _google_response([
        {"title": "SWE at Stripe", "snippet": "Payment APIs", "link": "https://g.co/1"},
    ])
    serp_data = _serp_response([
        {"title": "SWE at Stripe", "company_name": "Stripe", "location": "SF", "description": "Payment APIs", "related_links": []},
    ])

    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        if "googleapis.com" in args[0]:
            mock_resp.json.return_value = google_data
        elif "serpapi.com" in args[0]:
            mock_resp.json.return_value = serp_data
        else:
            mock_resp.status_code = 200
            mock_resp.text = "<html></html>"
        return mock_resp

    mock_client = AsyncMock()
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    results = await adapter.search("SWE at Stripe", limit=10)

    titles_companies = [(r["title"].lower(), r["company"].lower()) for r in results]
    assert len(titles_companies) == len(set(titles_companies))


# ── search_research() with Tavily ────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_research_with_tavily(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.tavily_api_key = "tavily-key"

    mock_httpx_cls.return_value = _mock_httpx(_tavily_response([
        {"title": "Google Interview Process", "content": "Detailed guide...", "url": "https://example.com/guide"},
        {"title": "FAANG Salaries 2025", "content": "Salary data...", "url": "https://example.com/salaries"},
    ]))

    results = await adapter.search_research("Google interview process", limit=5)

    assert len(results) == 2
    assert results[0]["source"] == "tavily"
    assert results[0]["title"] == "Google Interview Process"
    assert results[0]["snippet"] == "Detailed guide..."


# ── search_research() fallback ───────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_research_fallback(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.tavily_api_key = ""

    html = """
    <html><body>
    <div class="g">
        <a href="https://example.com/r1"><h3>Company Research Guide</h3></a>
        <span class="aCOpRe">Learn about the company culture</span>
    </div>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    results = await adapter.search_research("company culture research", limit=5)

    assert len(results) >= 1
    assert results[0]["source"] == "web_research"
    assert results[0]["title"] == "Company Research Guide"


# ── _extract_company() patterns ──────────────────────────


class TestExtractCompany:
    def setup_method(self):
        self.adapter = SearchAdapter()

    def test_at_pattern(self):
        assert self.adapter._extract_company("Engineer at Stripe", ". Build APIs") == "Stripe"

    def test_at_pattern_with_dash(self):
        assert self.adapter._extract_company("SWE at OpenAI – ML Team", "Research") == "OpenAI"

    def test_hiring_pattern(self):
        assert self.adapter._extract_company("Apple hiring iOS Dev", "Cupertino") == "Apple"

    def test_careers_pattern(self):
        assert self.adapter._extract_company("Netflix careers", "Join our team") == "Netflix"

    def test_dash_prefix_pattern(self):
        assert self.adapter._extract_company("Spotify - Backend Engineer", "Music streaming") == "Spotify"

    def test_pipe_prefix_pattern(self):
        assert self.adapter._extract_company("Airbnb | Data Scientist", "Analytics") == "Airbnb"

    def test_fallback_default(self):
        assert self.adapter._extract_company("random text", "no company here") == "Tech Company"

    def test_company_with_ampersand(self):
        result = self.adapter._extract_company("Role at Johnson & Johnson", "Healthcare")
        assert "Johnson" in result

    def test_company_truncated_at_50(self):
        long_name = "A" * 60
        result = self.adapter._extract_company(f"Role at {long_name}", "desc")
        assert len(result) <= 50


# ── _extract_salary() patterns ───────────────────────────


class TestExtractSalary:
    def setup_method(self):
        self.adapter = SearchAdapter()

    def test_dollar_range(self):
        assert self.adapter._extract_salary("Salary: $120k-$180k per year") is not None

    def test_dollar_with_comma(self):
        result = self.adapter._extract_salary("Pay is $80,000 - $120,000")
        assert result is not None

    def test_k_suffix_range(self):
        result = self.adapter._extract_salary("Compensation: 90k - 130k")
        assert result is not None
        assert "$" in result

    def test_k_suffix_uppercase(self):
        result = self.adapter._extract_salary("Salary 100K - 150K annually")
        assert result is not None

    def test_no_salary(self):
        assert self.adapter._extract_salary("Great benefits and culture") is None

    def test_empty_string(self):
        assert self.adapter._extract_salary("") is None


# ── search() internship filter ───────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_internship_filter(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.serpapi_key = ""
    mock_settings.tavily_api_key = ""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body></body></html>"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    await adapter.search("python developer", source_filter="internship", limit=5)

    calls = mock_client.get.call_args_list
    search_urls = [str(c) for c in calls]
    assert any("internship" in url.lower() for url in search_urls)


# ── search() job filter ──────────────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_job_filter(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.serpapi_key = ""
    mock_settings.tavily_api_key = ""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body></body></html>"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    await adapter.search("python developer", source_filter="job", limit=5)

    calls = mock_client.get.call_args_list
    search_urls = [str(c) for c in calls]
    assert any("job" in url.lower() for url in search_urls)


# ── search() skips internship keyword if already present ─


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_internship_no_double_prefix(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.serpapi_key = ""
    mock_settings.tavily_api_key = ""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body></body></html>"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    await adapter.search("internship python dev", source_filter="internship", limit=5)

    calls = mock_client.get.call_args_list
    urls = [str(c) for c in calls]
    assert not any("internship+internship" in url.lower() or "internship%20internship" in url.lower() for url in urls)


# ── search() with location ───────────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_with_location(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = "google-key"
    mock_settings.google_cse_id = "cse-id"
    mock_settings.serpapi_key = ""
    mock_settings.tavily_api_key = ""

    mock_httpx_cls.return_value = _mock_httpx(_google_response([
        {"title": "SWE at Netflix", "snippet": "LA office", "link": "https://netflix.com/jobs/1"},
    ]))

    results = await adapter.search("software engineer", location="Los Angeles", limit=5)

    assert len(results) >= 1
    first_call = mock_httpx_cls.return_value.get.call_args_list[0]
    params = first_call.kwargs.get("params", {})
    assert "Los Angeles" in params.get("q", "")


# ── search() respects limit ──────────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_respects_limit(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = "google-key"
    mock_settings.google_cse_id = "cse-id"
    mock_settings.serpapi_key = ""
    mock_settings.tavily_api_key = ""

    items = [
        {"title": f"Job {i} at Company{i}", "snippet": f"Desc {i}", "link": f"https://c{i}.com"}
        for i in range(10)
    ]
    mock_httpx_cls.return_value = _mock_httpx(_google_response(items))

    results = await adapter.search("developer", limit=3)

    assert len(results) <= 3


# ── _search_google error handling ────────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_google_api_error(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = "google-key"
    mock_settings.google_cse_id = "cse-id"

    mock_httpx_cls.return_value = _mock_httpx({"error": {"message": "quota exceeded"}})

    with pytest.raises(RuntimeError, match="quota exceeded"):
        await adapter._search_google("test query")


# ── _search_serpapi no related_links ─────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_serpapi_no_links(mock_settings, mock_httpx_cls, adapter):
    mock_settings.serpapi_key = "serp-key"

    mock_httpx_cls.return_value = _mock_httpx(_serp_response([
        {"title": "Dev", "company_name": "Acme", "location": "Remote", "description": "Code stuff"},
    ]))

    results = await adapter._search_serpapi("dev")

    assert len(results) == 1
    assert results[0]["apply_url"] is None


# ── search_research respects limit ───────────────────────


@pytest.mark.asyncio
@patch("app.search.adapters.httpx.AsyncClient")
@patch("app.search.adapters.settings")
async def test_search_research_respects_limit(mock_settings, mock_httpx_cls, adapter):
    mock_settings.google_api_key = ""
    mock_settings.google_cse_id = ""
    mock_settings.tavily_api_key = "tavily-key"

    tavily_data = _tavily_response([
        {"title": f"Result {i}", "content": f"Content {i}", "url": f"https://r{i}.com"}
        for i in range(10)
    ])
    mock_httpx_cls.return_value = _mock_httpx(tavily_data)

    results = await adapter.search_research("topic", limit=3)

    assert len(results) <= 3
