"""
Industry Detection Utility — automatically populates the `industry` field on
Opportunity records using a two-tier approach:

1. **Keyword matching** (fast, always available) — maps job titles, company
   names, and description keywords to ~30 standard industry categories.
2. **LLM detection** (optional, when available) — uses the configured chat
   model for more nuanced classification when keyword matching is uncertain.

Gracefully degrades: returns ``None`` when no industry can be confidently
determined.
"""

import logging
from typing import Optional

from app.services.model_manager import get_completion_llm

logger = logging.getLogger("agentforge.industry")

# ── Industry Category Definitions ────────────────────────────

# Robust industry map: maps search tokens → canonical industry label
# Tokens are matched case-insensitively against title, company, and description.
INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "Artificial Intelligence / ML": [
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "llm", "gpt", "neural network", "nlp", "natural language",
        "computer vision", "ml engineer", "ai engineer", "prompt engineer",
        "ai safety", "ai research", "foundation model", "generative ai",
        "genai", "diffusion model", "transformer", "rag", "retrieval augmented",
        "openai", "anthropic", "google deepmind", "hugging face",
    ],
    "Technology / Software": [
        "software", "full stack", "backend", "frontend", "full-stack",
        "front-end", "back-end", "developer", "engineer", "devops",
        "platform engineer", "infrastructure", "sre", "site reliability",
        "api", "microservice", "saas", "paas", "cloud native",
        "software engineer", "sde", "app developer", "mobile engineer",
        "ios", "android", "web developer", "fullstack",
    ],
    "Cloud / Infrastructure": [
        "cloud", "aws", "azure", "gcp", "kubernetes", "docker",
        "terraform", "infrastructure as code", "cloud architect",
        "cloud engineer", "cloud infrastructure", "serverless",
        "k8s", "helm", "istio", "observability", "datadog",
        "cloudflare", "vercel", "netlify", "digitalocean",
    ],
    "Cybersecurity": [
        "cyber", "security", "penetration testing", "pen test",
        "infosec", "information security", "zero trust", "encryption",
        "vulnerability", "exploit", "malware", "ransomware",
        "security engineer", "soc", "incident response", "threat detection",
        "identity", "iam", "auth", "authentication", "authorization",
        "crowdstrike", "palo alto", "cloudflare security",
    ],
    "Data / Analytics": [
        "data scientist", "data engineer", "data analyst", "data science",
        "analytics", "bi", "business intelligence", "tableau", "power bi",
        "looker", "data pipeline", "etl", "data warehouse", "data lake",
        "big data", "spark", "hadoop", "databricks", "snowflake",
        "airflow", "dbt", "data modeling", "data infrastructure",
        "data platform", "analytics engineer",
    ],
    "Finance / Fintech": [
        "fintech", "finance", "banking", "investment", "trading",
        "quant", "quantitative", "blockchain", "crypto", "defi",
        "payments", "payment", "stripe", "square", "paypal",
        "venmo", "wise", "plaid", "robinhood", "coinbase",
        "wealth", "portfolio", "insurance", "insurtech",
        "financial", "mortgage", "lending", "credit",
    ],
    "Healthcare / Biotech": [
        "healthcare", "health tech", "biotech", "biotechnology",
        "pharma", "pharmaceutical", "medical", "clinical",
        "hospital", "health", "bioinformatics", "genomics",
        "drug discovery", "therapeutics", "diagnostics",
        "medtech", "medical device", "healthtech",
    ],
    "E-commerce / Retail": [
        "ecommerce", "e-commerce", "retail", "marketplace",
        "shopify", "amazon", "etsy", "ebay", "walmart",
        "shopping", "d2c", "direct-to-consumer", "consumer goods",
        "supply chain", "logistics", "fulfillment", "inventory",
        "merchant", "store", "omnichannel",
    ],
    "Education / EdTech": [
        "education", "edtech", "learning", "teaching", "teacher",
        "course", "curriculum", "student", "university", "school",
        "training", "upskill", "reskill", "ed-tech", "coursera",
        "udemy", "khan academy", "duolingo", "quizlet",
        "online learning", "e-learning",
    ],
    "Gaming / Entertainment": [
        "gaming", "game", "video game", "esports", "unity",
        "unreal engine", "roblox", "epic games", "riot",
        "blizzard", "electronic arts", "nintendo", "sony",
        "entertainment", "streaming", "media", "content",
        "netflix", "hulu", "spotify", "disney", "warner bros",
        "animation", "vfx", "visual effects", "3d modeling",
    ],
    "Social Media / Communication": [
        "social media", "social network", "messaging", "chat",
        "discord", "slack", "telegram", "whatsapp", "signal",
        "linkedin", "twitter", "x ", "meta", "facebook",
        "instagram", "tiktok", "snapchat", "pinterest",
        "community", "forums", "communication",
    ],
    "Hardware / Semiconductors": [
        "hardware", "semiconductor", "chip", "processor", "gpu",
        "fpga", "asic", "nvidia", "intel", "amd", "arm",
        "quantum computing", "robotics", "iot", "internet of things",
        "embedded", "firmware", "raspberry pi", "arduino",
        "sensor", "electronics", "circuit", "pcb",
    ],
    "Automotive / Transportation": [
        "automotive", "autonomous vehicle", "self-driving", "ev",
        "electric vehicle", "tesla", "uber", "lyft", "waymo",
        "cruise", "rivian", "lucid", "ride-sharing", "rideshare",
        "transportation", "logistics", "delivery", "fleet",
        "aviation", "aerospace", "drone", "uav",
    ],
    "Energy / CleanTech": [
        "energy", "clean energy", "renewable", "solar", "wind",
        "cleantech", "climate", "sustainability", "green tech",
        "tesla energy", "battery", "grid", "power",
        "carbon", "emissions", "environmental", "climatetech",
        "nuclear", "fusion", "hydro", "geothermal",
    ],
    "Consulting / Professional Services": [
        "consulting", "consultant", "mckinsey", "bain", "boston consulting",
        "bcg", "deloitte", "pwc", "ey", "kpmg", "accenture",
        "strategy", "management consulting", "advisory",
        "professional services", "systems integrator",
    ],
    "Media / Advertising": [
        "media", "advertising", "ad tech", "adtech", "marketing",
        "digital marketing", "seo", "sem", "content marketing",
        "pr", "public relations", "publishing", "news",
        "journalism", "broadcast", "television", "tv",
        "radio", "podcast", "influencer", "creative agency",
    ],
    "Real Estate / Property": [
        "real estate", "property", "proptech", "zillow", "redfin",
        "realtor", "housing", "rental", "commercial real estate",
        "cre", "mortgage", "title", "property management",
        "construction", "architecture", "smart building",
    ],
    "Legal / Compliance": [
        "legal", "law", "attorney", "lawyer", "paralegal",
        "compliance", "regulatory", "gdpr", "hipaa",
        "contract", "litigation", "intellectual property",
        "patent", "trademark", "legal tech", "legaltech",
        "governance", "risk", "audit",
    ],
    "Aerospace / Defense": [
        "aerospace", "defense", "space", "nasa", "spacex",
        "blue origin", "lockheed martin", "boeing", "northrop",
        "raytheon", "satellite", "rocket", "missile",
        "aviation", "aircraft", "drone defense", "military",
    ],
    "Food / Hospitality": [
        "food", "restaurant", "hospitality", "hotel", "travel",
        "tourism", "food delivery", "doordash", "ubereats",
        "grubhub", "instacart", "hello fresh", "meal prep",
        "catering", "bakery", "brewery", "winery",
        "food tech", "foodtech", "agriculture", "agtech",
    ],
    "Non-profit / Social Impact": [
        "nonprofit", "non-profit", "ngo", "charity", "foundation",
        "social impact", "social good", "philanthropy",
        "community development", "volunteer", "humanitarian",
        "education nonprofit", "environmental nonprofit",
        "public interest", "open source",
    ],
    "Government / Public Sector": [
        "government", "public sector", "federal", "state government",
        "local government", "municipal", "public service",
        "civic tech", "govtech", "usda", "nasa",
        "national lab", "research lab", "public policy",
        "democracy", "voting", "civic",
    ],
}

# ── Company → Industry mapping for well-known employers ──────
# These override keyword-based detection for precise classification.
COMPANY_INDUSTRY_OVERRIDE: dict[str, str] = {
    # Tech giants
    "google": "Technology / Software",
    "alphabet": "Technology / Software",
    "meta": "Social Media / Communication",
    "facebook": "Social Media / Communication",
    "apple": "Technology / Software",
    "microsoft": "Technology / Software",
    "amazon": "E-commerce / Retail",
    "netflix": "Gaming / Entertainment",
    "nvidia": "Hardware / Semiconductors",
    "intel": "Hardware / Semiconductors",
    "amd": "Hardware / Semiconductors",
    "arm": "Hardware / Semiconductors",
    "ibm": "Technology / Software",
    "oracle": "Technology / Software",
    "salesforce": "Technology / Software",
    "sap": "Technology / Software",
    "adobe": "Technology / Software",
    # AI / ML
    "openai": "Artificial Intelligence / ML",
    "anthropic": "Artificial Intelligence / ML",
    "deepmind": "Artificial Intelligence / ML",
    "hugging face": "Artificial Intelligence / ML",
    "cohere": "Artificial Intelligence / ML",
    "mistral ai": "Artificial Intelligence / ML",
    "stability ai": "Artificial Intelligence / ML",
    "midjourney": "Artificial Intelligence / ML",
    "perplexity ai": "Artificial Intelligence / ML",
    # Cloud / Infrastructure
    "aws": "Cloud / Infrastructure",
    "amazon web services": "Cloud / Infrastructure",
    "cloudflare": "Cloud / Infrastructure",
    "vercel": "Cloud / Infrastructure",
    "netlify": "Cloud / Infrastructure",
    "digitalocean": "Cloud / Infrastructure",
    "hashicorp": "Cloud / Infrastructure",
    "datadog": "Cloud / Infrastructure",
    "new relic": "Cloud / Infrastructure",
    "mongodb": "Technology / Software",
    "databricks": "Data / Analytics",
    "snowflake": "Data / Analytics",
    "confluent": "Data / Analytics",
    "elastic": "Data / Analytics",
    # Cybersecurity
    "crowdstrike": "Cybersecurity",
    "palo alto": "Cybersecurity",
    "palo alto networks": "Cybersecurity",
    "okta": "Cybersecurity",
    "cloudflare security": "Cybersecurity",
    # Fintech
    "stripe": "Finance / Fintech",
    "square": "Finance / Fintech",
    "block": "Finance / Fintech",
    "paypal": "Finance / Fintech",
    "venmo": "Finance / Fintech",
    "wise": "Finance / Fintech",
    "plaid": "Finance / Fintech",
    "robinhood": "Finance / Fintech",
    "coinbase": "Finance / Fintech",
    "chime": "Finance / Fintech",
    "brex": "Finance / Fintech",
    "bill.com": "Finance / Fintech",
    "jpmorgan": "Finance / Fintech",
    "goldman sachs": "Finance / Fintech",
    "morgan stanley": "Finance / Fintech",
    # Gaming / Entertainment
    "unity": "Gaming / Entertainment",
    "epic games": "Gaming / Entertainment",
    "roblox": "Gaming / Entertainment",
    "riot games": "Gaming / Entertainment",
    "blizzard": "Gaming / Entertainment",
    "activision": "Gaming / Entertainment",
    "electronic arts": "Gaming / Entertainment",
    "nintendo": "Gaming / Entertainment",
    "sony interactive": "Gaming / Entertainment",
    "spotify": "Gaming / Entertainment",
    "disney": "Gaming / Entertainment",
    "warner bros": "Gaming / Entertainment",
    # E-commerce / Retail
    "shopify": "E-commerce / Retail",
    "etsy": "E-commerce / Retail",
    "ebay": "E-commerce / Retail",
    "walmart": "E-commerce / Retail",
    "target": "E-commerce / Retail",
    "costco": "E-commerce / Retail",
    "doordash": "Food / Hospitality",
    "uber eats": "Food / Hospitality",
    "instacart": "E-commerce / Retail",
    # Education
    "coursera": "Education / EdTech",
    "udemy": "Education / EdTech",
    "udacity": "Education / EdTech",
    "khan academy": "Education / EdTech",
    "duolingo": "Education / EdTech",
    "quizlet": "Education / EdTech",
    "chegg": "Education / EdTech",
    # Healthcare
    "robin": "Healthcare / Biotech",  # "robin healthcare"
    "zocdoc": "Healthcare / Biotech",
    "flatiron": "Healthcare / Biotech",
    "23andme": "Healthcare / Biotech",
    "gsk": "Healthcare / Biotech",
    "pfizer": "Healthcare / Biotech",
    "moderna": "Healthcare / Biotech",
    "bioNTech": "Healthcare / Biotech",
    # Automotive
    "tesla": "Automotive / Transportation",
    "waymo": "Automotive / Transportation",
    "cruise": "Automotive / Transportation",
    "rivian": "Automotive / Transportation",
    "lucid": "Automotive / Transportation",
    "uber": "Automotive / Transportation",
    "lyft": "Automotive / Transportation",
    # Aerospace
    "spacex": "Aerospace / Defense",
    "blue origin": "Aerospace / Defense",
    "lockheed martin": "Aerospace / Defense",
    "boeing": "Aerospace / Defense",
    "northrop grumman": "Aerospace / Defense",
    "raytheon": "Aerospace / Defense",
    # Consulting
    "mckinsey": "Consulting / Professional Services",
    "bain": "Consulting / Professional Services",
    "boston consulting group": "Consulting / Professional Services",
    "deloitte": "Consulting / Professional Services",
    "pwc": "Consulting / Professional Services",
    "accenture": "Consulting / Professional Services",
    # Social Media
    "linkedin": "Social Media / Communication",
    "twitter": "Social Media / Communication",
    "tiktok": "Social Media / Communication",
    "snapchat": "Social Media / Communication",
    "pinterest": "Social Media / Communication",
    "reddit": "Social Media / Communication",
    "discord": "Social Media / Communication",
    "slack": "Social Media / Communication",
    "telegram": "Social Media / Communication",
    "zoom": "Social Media / Communication",
    # Energy
    "tesla energy": "Energy / CleanTech",
    "nextracker": "Energy / CleanTech",
    "sunrun": "Energy / CleanTech",
    "enphase": "Energy / CleanTech",
    "commonwealth fusion": "Energy / CleanTech",
}


def _normalize(text: str) -> str:
    """Lowercase and strip whitespace for matching."""
    return text.lower().strip()


def detect_industry(
    title: str,
    company: str = "",
    description: str = "",
    use_llm: bool = False,
) -> Optional[str]:
    """
    Detect the industry for an opportunity using keyword matching (fast)
    and optionally LLM fallback for ambiguous cases.

    Priority order:
    1. Company override (exact match against known employers)
    2. Keyword scoring (title + company + description)
    3. LLM (optional — only when use_llm=True and keyword match is uncertain)

    Returns a canonical industry label string, or None if no industry
    can be confidently determined.
    """
    title_norm = _normalize(title)
    company_norm = _normalize(company)
    description_norm = _normalize(description)

    # ── 1. Company override ──
    for company_key, industry in COMPANY_INDUSTRY_OVERRIDE.items():
        if company_key in company_norm:
            return industry

    # ── 2. Keyword scoring ──
    scores: dict[str, int] = {}
    combined = f"{title_norm} {company_norm} {description_norm}"

    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            # Exact word/phrase match in combined text
            if kw in combined:
                score += 1
            # Title matches get extra weight
            if kw in title_norm:
                score += 2
            # Company matches get extra weight
            if kw in company_norm:
                score += 2
        if score > 0:
            scores[industry] = score

    if scores:
        best_industry = max(scores, key=scores.get)
        best_score = scores[best_industry]

        # If the best score is clear (at least 2+ points ahead of second), use it
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) >= 2 and (sorted_scores[0] - sorted_scores[1]) >= 2:
            return best_industry
        if best_score >= 3:
            return best_industry

        # ── 3. LLM fallback (optional) ──
        if use_llm:
            return _detect_industry_with_llm(title, company, description)

        # Otherwise return the best guess if score is decent
        if best_score >= 2:
            return best_industry

    return None


def detect_industry_batch(
    items: list[dict],
    use_llm: bool = False,
) -> list[Optional[str]]:
    """
    Detect industries for a batch of opportunity dicts.

    Each dict should have keys: ``title``, ``company``, ``description``.
    Returns a list of industry labels (or None) in the same order.
    """
    results = []
    for item in items:
        results.append(
            detect_industry(
                title=item.get("title", ""),
                company=item.get("company", ""),
                description=item.get("description", ""),
                use_llm=use_llm,
            )
        )
    return results


def _detect_industry_with_llm(
    title: str,
    company: str,
    description: str,
) -> Optional[str]:
    """
    Use the configured LLM to detect the industry for an opportunity.
    Fallback when keyword matching is uncertain.

    Returns None if LLM is unavailable or the call fails.
    """
    llm = get_completion_llm(temperature=0.3)
    if not llm:
        return None

    try:
        from langchain_core.messages import HumanMessage

        all_categories = sorted(INDUSTRY_KEYWORDS.keys())
        categories_str = "\n".join(f"- {c}" for c in all_categories)

        prompt = f"""You are a career opportunity classifier. Given a job posting, determine the most appropriate industry category.

JOB TITLE: {title}
COMPANY: {company}
DESCRIPTION: {description[:500] if description else "N/A"}

Choose the single best industry from this list:
{categories_str}

If none fits, choose the closest match. Respond with ONLY the industry name. No punctuation, no explanation."""

        response = llm.invoke([HumanMessage(content=prompt)])
        result = str(response.content).strip()

        # Validate against known categories
        if result in INDUSTRY_KEYWORDS:
            return result

        # Fuzzy match
        for cat in all_categories:
            if result.lower() in cat.lower() or cat.lower() in result.lower():
                return cat

        logger.debug("LLM returned unknown industry: %s", result)
        return None

    except Exception as e:
        logger.debug("LLM industry detection failed: %s", e)
        return None
