import json
import logging
import re
from datetime import UTC

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.hiring_agent.pdf_extractor import (
    convert_resume_to_evaluation_text,
    extract_pdf_text,
    parse_resume_sections,
)
from app.hiring_agent.schemas import (
    ATSScore,
    EvaluationData,
    ExtractedResume,
    ImprovementItem,
    JDMatchResult,
    PipelineResult,
)
from app.models.user import MemoryEntry
from app.services.memory_service import MemoryService
from app.services.model_manager import get_completion_llm

logger = logging.getLogger("agentforge.hiring_agent.service")

TECH_KEYWORDS = [
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "golang",
    "rust",
    "c++",
    "c#",
    "ruby",
    "swift",
    "kotlin",
    "scala",
    "php",
    "perl",
    "r",
    "matlab",
    "sql",
    "bash",
    "shell",
    "react",
    "angular",
    "vue",
    "next.js",
    "node.js",
    "express",
    "django",
    "flask",
    "spring",
    "fastapi",
    "graphql",
    "rest",
    "api",
    "docker",
    "kubernetes",
    "k8s",
    "aws",
    "azure",
    "gcp",
    "terraform",
    "ansible",
    "jenkins",
    "ci/cd",
    "git",
    "linux",
    "nginx",
    "redis",
    "mongodb",
    "postgresql",
    "mysql",
    "elasticsearch",
    "kafka",
    "rabbitmq",
    "grpc",
    "websocket",
    "machine learning",
    "deep learning",
    "ai",
    "llm",
    "nlp",
    "computer vision",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "langchain",
    "rag",
    "vector database",
    "openai",
    "hugging face",
    "llama",
    "gpt",
    "bert",
    "transformer",
    "agent",
    "autogen",
    "crewai",
    "tailwind",
    "sass",
    "redux",
    "webpack",
    "vite",
    "jest",
    "cypress",
    "pandas",
    "numpy",
    "jupyter",
    "spark",
    "hadoop",
    "airflow",
    "dbt",
    "microservices",
    "serverless",
    "lambda",
    "containers",
    "orchestration",
    "oauth",
    "jwt",
    "saml",
    "ldap",
    "ssl",
    "tls",
    "https",
    "agile",
    "scrum",
    "kanban",
    "jira",
    "confluence",
    "tableau",
    "power bi",
    "looker",
    "datadog",
    "grafana",
    "prometheus",
]


class HiringAgentService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id
        self.memory = MemoryService(db)

    async def _llm_call(self, section_name: str, prompt: str, return_model_cls=None) -> dict | None:
        llm = get_completion_llm(temperature=0.1, preferred_provider="openai")
        if not llm:
            return None
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            system = f"You are an expert resume parser. Extract {section_name} from the resume text. Return ONLY valid JSON. No markdown, no explanations."
            response = await llm.ainvoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(content=prompt),
                ]
            )
            text = response.content.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                text = text[json_start : json_end + 1]
            data = json.loads(text)
            from app.hiring_agent.transform import transform_parsed_data

            return transform_parsed_data(data)
        except Exception as e:
            logger.warning("LLM section extraction failed for %s: %s", section_name, e)
            return None

    async def extract_resume(self, pdf_content: bytes) -> ExtractedResume:
        text = extract_pdf_text(pdf_content)
        resume = parse_resume_sections(text, self._llm_call)
        return resume

    async def enrich_github(self, github_url: str) -> dict:
        username = self._extract_github_username(github_url)
        if not username:
            return {"error": "Could not extract GitHub username"}
        headers = {"User-Agent": "AgentForge-CareerOS", "Accept": "application/vnd.github.v3+json"}
        if settings.github_token:
            headers["Authorization"] = f"token {settings.github_token}"
        result = {"username": username, "profile": {}, "repositories": [], "contributions": {}}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                user_resp = await client.get(f"https://api.github.com/users/{username}", headers=headers)
                if user_resp.status_code == 200:
                    u = user_resp.json()
                    result["profile"] = {
                        "name": u.get("name"),
                        "bio": u.get("bio"),
                        "location": u.get("location"),
                        "company": u.get("company"),
                        "followers": u.get("followers", 0),
                        "public_repos": u.get("public_repos", 0),
                        "created_at": u.get("created_at"),
                        "blog": u.get("blog"),
                        "html_url": u.get("html_url"),
                        "hireable": u.get("hireable"),
                    }

                repos_resp = await client.get(
                    f"https://api.github.com/users/{username}/repos",
                    params={"sort": "stars", "direction": "desc", "per_page": 50, "type": "owner"},
                    headers=headers,
                )
                if repos_resp.status_code == 200:
                    repos_raw = repos_resp.json()
                    result["repositories"] = [
                        {
                            "name": r.get("name"),
                            "full_name": r.get("full_name"),
                            "description": r.get("description"),
                            "language": r.get("language"),
                            "stars": r.get("stargazers_count", 0),
                            "forks": r.get("forks_count", 0),
                            "topics": r.get("topics", []),
                            "is_fork": r.get("fork", False),
                            "html_url": r.get("html_url"),
                            "homepage": r.get("homepage"),
                        }
                        for r in repos_raw
                    ]

                search_resp = await client.get(
                    "https://api.github.com/search/issues",
                    params={"q": f"author:{username} type:pr", "per_page": 100},
                    headers=headers,
                )
                if search_resp.status_code == 200:
                    items = search_resp.json().get("items", [])
                    result["contributions"] = {
                        "total_prs": len(items),
                        "merged": sum(
                            1
                            for i in items
                            if any(label.get("name") == "merged" for label in i.get("labels", []))
                            or i.get("pull_request", {}).get("merged_at")
                        ),
                        "repos_contributed": len(set(i.get("repository_url", "") for i in items)),
                    }
        except Exception as e:
            logger.warning("GitHub enrichment failed: %s", e)
            result["error"] = str(e)
        return result

    async def enrich_portfolio(self, portfolio_url: str) -> dict:
        if not portfolio_url or not portfolio_url.startswith(("http://", "https://")):
            return {"error": "Invalid URL"}
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(
                    portfolio_url, headers={"User-Agent": "Mozilla/5.0 (compatible; AgentForge/1.0)"}
                )
                if resp.status_code != 200:
                    return {"error": f"HTTP {resp.status_code}"}
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                meta_desc = ""
                mt = soup.find("meta", attrs={"name": "description"})
                if mt and mt.get("content"):
                    meta_desc = mt["content"].strip()
                body = soup.get_text(separator="\n", strip=True)[:8000]
                headings = [
                    h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if h.get_text(strip=True)
                ][:15]
                detected = [kw for kw in TECH_KEYWORDS if kw.lower() in body.lower()]
                return {
                    "title": title,
                    "meta_description": meta_desc,
                    "headings": headings,
                    "technologies_detected": list(set(detected))[:20],
                    "text_snippet": body[:2000],
                }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except Exception as e:
            return {"error": str(e)}

    async def check_live_demos(self, urls: list[str]) -> list[dict]:
        results = []
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = await client.get(url, headers={"User-Agent": "AgentForge/1.0"})
                    results.append(
                        {"url": url, "status": "ok" if resp.status_code == 200 else "broken", "code": resp.status_code}
                    )
                except httpx.TimeoutError:
                    results.append({"url": url, "status": "timeout", "code": None})
                except Exception as e:
                    results.append({"url": url, "status": "error", "code": str(e)})
        results.sort(key=lambda x: ("ok" != x["status"], x["url"]))
        return results

    async def evaluate_resume(
        self, resume_text: str, position_type: str = None, live_demo_text: str = ""
    ) -> EvaluationData | None:
        llm = get_completion_llm(temperature=0.3, preferred_provider="openai")
        if not llm:
            return None
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            system = """You are an expert technical recruiter evaluating resumes. You must be fair and unbiased.
IMPORTANT: Scores must NOT be influenced by the candidate's name, gender, institution name, grades, or location.
Focus ONLY on demonstrated skills, project complexity, and real achievements.

Score each category strictly. Return ONLY valid JSON matching the schema."""
            prompt = f"""Evaluate this candidate's resume. Score each category from 0 to max.

POSITION TYPE: {position_type or "Not specified"}

RESUME:
{resume_text}

{live_demo_text}

Return a JSON object with EXACTLY this structure:
{{
    "scores": {{
        "open_source": {{"score": <int 0-35>, "max": 35, "evidence": "..."}},
        "self_projects": {{"score": <int 0-30>, "max": 30, "evidence": "..."}},
        "production": {{"score": <int 0-25>, "max": 25, "evidence": "..."}},
        "technical_skills": {{"score": <int 0-10>, "max": 10, "evidence": "..."}}
    }},
    "bonus_points": {{
        "total": <float 0-20>,
        "breakdown": "Breakdown of bonus points"
    }},
    "deductions": {{
        "total": <float 0-100>,
        "reasons": "Reasons for deductions"
    }},
    "key_strengths": ["strength1", "strength2", "strength3"],
    "areas_for_improvement": ["area1", "area2", "area3"]
}}

SCORING GUIDELINES:
- Open Source (0-35): GitHub contributions, PRs to other projects, open source repos with stars, community involvement
- Self Projects (0-30): Personal projects, hackathon projects, portfolio projects, project complexity and originality
- Production Experience (0-25): Work experience, internships, real-world impact, team collaboration
- Technical Skills (0-10): Breadth and depth of technical skills, relevant technologies
- Bonus (0-20): GSoC (+5), startup founder (+3-5), portfolio (+2), LinkedIn (+1), technical blogs (+1-3), working live demos (+1 each max +5)
- Deductions: Simple tutorial projects, missing links, projects without substance

Be specific in your evidence. Reference actual project names, technologies, and achievements from the resume."""
            response = await llm.ainvoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(content=prompt),
                ]
            )
            text = response.content.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                text = text[json_start : json_end + 1]
            data = json.loads(text)
            return EvaluationData(**data)
        except Exception as e:
            logger.error("Resume evaluation failed: %s", e)
            return None

    async def compute_ats_analysis(self, resume_text: str, jd_text: str) -> ATSScore:
        text_lower = resume_text.lower()
        jd_lower = jd_text.lower()
        resume_kws = {kw for kw in TECH_KEYWORDS if re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", text_lower)}
        jd_kws = {kw for kw in TECH_KEYWORDS if re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", jd_lower)}
        matched = resume_kws & jd_kws
        missing = jd_kws - resume_kws
        coverage = (len(matched) / max(len(jd_kws), 1)) * 100

        exp_patterns = [r"(\d+)\+?\s*(?:years?|yrs?)", r"experience\s*(?:of\s+)?(\d+)\+?\s*(?:years?|yrs?)"]
        jd_years = next((int(m.group(1)) for p in exp_patterns for m in [re.search(p, jd_lower)] if m), None)
        resume_years = next((int(m.group(1)) for p in exp_patterns for m in [re.search(p, text_lower)] if m), None)

        suggestions = []
        if missing:
            suggestions.append(f"Add missing keywords: {', '.join(sorted(missing)[:10])}")
        if coverage < 50:
            suggestions.append("Keyword coverage is below 50% — add relevant skills and technologies")
        if jd_years and resume_years and jd_years > resume_years:
            suggestions.append(f"JD requires {jd_years}+ years of experience")

        return ATSScore(
            keyword_coverage_pct=round(coverage, 1),
            matched_keywords=sorted(matched),
            missing_keywords=sorted(missing),
            matched_count=len(matched),
            missing_count=len(missing),
            suggestions=suggestions,
            experience_years=jd_years,
            resume_experience_years=resume_years,
        )

    async def match_jd(
        self, resume_text: str, jd_text: str, github_text: str = "", portfolio_text: str = ""
    ) -> JDMatchResult | None:
        llm = get_completion_llm(temperature=0.2, preferred_provider="openai")
        if not llm:
            return None
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            context = ""
            if github_text:
                context += f"\nGITHUB DATA:\n{github_text}\n"
            if portfolio_text:
                context += f"\nPORTFOLIO DATA:\n{portfolio_text}\n"
            prompt = f"""Evaluate the match between this candidate and the job description.

JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}{context}

Return a JSON object with EXACTLY this structure:
{{
    "skill_match": {{"score": <int 0-40>, "matched": ["skill1"], "missing": ["skill2"]}},
    "experience_match": {{"score": <int 0-25>, "evidence": "..."}},
    "education_match": {{"score": <int 0-15>, "evidence": "..."}},
    "project_relevance": {{"score": <int 0-20>, "evidence": "..."}},
    "overall_assessment": "2-3 sentence assessment",
    "gap_analysis": ["gap1", "gap2"]
}}

Scoring: Skill Match 0-40, Experience Match 0-25, Education Match 0-15, Project Relevance 0-20.
Return ONLY valid JSON."""
            response = await llm.ainvoke(
                [
                    SystemMessage(content="You are a precise resume-job matching evaluator. Return ONLY valid JSON."),
                    HumanMessage(content=prompt),
                ]
            )
            text = response.content.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                text = text[json_start : json_end + 1]
            data = json.loads(text)
            sm = data.get("skill_match", {})
            em = data.get("experience_match", {})
            edm = data.get("education_match", {})
            pr = data.get("project_relevance", {})
            overall = (
                min(sm.get("score", 0), 40)
                + min(em.get("score", 0), 25)
                + min(edm.get("score", 0), 15)
                + min(pr.get("score", 0), 20)
            )
            return JDMatchResult(
                skill_match=sm,
                experience_match=em,
                education_match=edm,
                project_relevance=pr,
                overall_score=overall,
                overall_assessment=data.get("overall_assessment", ""),
                gap_analysis=data.get("gap_analysis", []),
            )
        except Exception as e:
            logger.error("JD matching failed: %s", e)
            return None

    async def generate_cover_letter(
        self,
        resume_text: str,
        jd_text: str,
        candidate_name: str = None,
        company_name: str = None,
        tone: str = "professional",
        length: str = "medium",
    ) -> str | None:
        llm = get_completion_llm(temperature=0.7, preferred_provider="openai")
        if not llm:
            return None
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            length_guide = {
                "short": "3-4 sentences, very concise",
                "medium": "3-4 paragraphs",
                "long": "5-6 paragraphs",
            }.get(length, "3-4 paragraphs")
            system = f"You are an expert career coach. Generate a {tone} cover letter that is {length_guide}. Be specific, use concrete examples from the resume, and avoid generic phrases. Return ONLY the letter text."
            company_str = f"\nCOMPANY: {company_name}" if company_name else ""
            prompt = f"""Generate a tailored cover letter.

CANDIDATE NAME: {candidate_name or "The candidate"}
{company_str}

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Highlight specific skills and experiences that make this candidate a strong fit. Use project names and technologies from the resume."""
            response = await llm.ainvoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(content=prompt),
                ]
            )
            letter = response.content.strip().strip('"').strip("'")
            return letter
        except Exception as e:
            logger.error("Cover letter generation failed: %s", e)
            return None

    async def generate_improvements(self, evaluation: EvaluationData) -> list[ImprovementItem]:
        llm = get_completion_llm(temperature=0.4, preferred_provider="openai")
        if not llm:
            return self._fallback_improvements(evaluation)
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            scores_text = "\n".join(
                f"- {cat}: {getattr(evaluation.scores, cat).score}/{getattr(evaluation.scores, cat).max} - {getattr(evaluation.scores, cat).evidence}"
                for cat in ["open_source", "self_projects", "production", "technical_skills"]
                if getattr(evaluation.scores, cat, None)
            )
            prompt = f"""Given this resume evaluation, generate specific improvement suggestions.

SCORES:
{scores_text}

AREAS FOR IMPROVEMENT:
{chr(10).join(f"- {a}" for a in evaluation.areas_for_improvement)}

KEY STRENGTHS:
{chr(10).join(f"- {s}" for s in evaluation.key_strengths)}

Return a JSON array of improvement objects. Each object has:
- "category": "open_source" | "self_projects" | "production" | "technical_skills"
- "suggestion": detailed actionable suggestion (1-3 sentences)
- "impact": "high" | "medium" | "low"
- "effort": "high" | "medium" | "low"
- "priority_score": integer 0-10

Generate 2-4 suggestions per category. Prioritize suggestions that address low scores.
Return ONLY valid JSON array."""
            response = await llm.ainvoke(
                [
                    SystemMessage(content="You are an expert resume improvement advisor. Return ONLY valid JSON."),
                    HumanMessage(content=prompt),
                ]
            )
            text = response.content.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            if isinstance(data, dict):
                items = []
                for cat_items in data.values():
                    if isinstance(cat_items, list):
                        items.extend(cat_items)
                return [ImprovementItem(**i) for i in items if isinstance(i, dict)]
            elif isinstance(data, list):
                return [ImprovementItem(**i) for i in data if isinstance(i, dict)]
            return []
        except Exception as e:
            logger.warning("Improvement generation failed, using fallback: %s", e)
            return self._fallback_improvements(evaluation)

    def _fallback_improvements(self, evaluation: EvaluationData) -> list[ImprovementItem]:
        items = []
        for cat in ["open_source", "self_projects", "production", "technical_skills"]:
            cs = getattr(evaluation.scores, cat, None)
            if cs and cs.score / max(cs.max, 1) < 0.7:
                items.append(
                    ImprovementItem(
                        category=cat,
                        suggestion=f"Improve your {cat.replace('_', ' ')} score by working on more substantial projects in this area.",
                        impact="medium",
                        effort="medium",
                        priority_score=5,
                    )
                )
        return items

    def _extract_github_username(self, url: str) -> str | None:
        if not url:
            return None
        m = re.search(r"github\.com/([A-Za-z0-9_.-]+)", url)
        return m.group(1) if m else None

    async def run_pipeline(
        self,
        pdf_content: bytes,
        jd_text: str = None,
        position_type: str = None,
        github_url: str = None,
        portfolio_url: str = None,
    ) -> PipelineResult | None:
        resume = await self.extract_resume(pdf_content)
        if not resume or not resume.raw_text:
            return None

        github_data = {}
        portfolio_data = {}
        if github_url:
            github_data = await self.enrich_github(github_url)
        if portfolio_url:
            portfolio_data = await self.enrich_portfolio(portfolio_url)

        github_text = ""
        if github_data.get("profile"):
            p = github_data["profile"]
            repos = github_data.get("repositories", [])
            top_repos = sorted(
                [r for r in repos if not r.get("is_fork")], key=lambda r: r.get("stars", 0), reverse=True
            )[:5]
            github_text = (
                f"\nGitHub: {p.get('name', '')} - {p.get('followers', 0)} followers, {p.get('public_repos', 0)} repos"
            )
            if top_repos:
                github_text += "\nTop repos:\n" + "\n".join(
                    f"- {r['name']} (⭐{r['stars']}) - {r.get('description', '')}" for r in top_repos
                )
            contribs = github_data.get("contributions", {})
            if contribs:
                github_text += f"\nPRs: {contribs.get('total_prs', 0)} total, {contribs.get('merged', 0)} merged"

        portfolio_text = ""
        if portfolio_data.get("title"):
            portfolio_text = f"\nPortfolio: {portfolio_data.get('title', '')}"
            detected = portfolio_data.get("technologies_detected", [])
            if detected:
                portfolio_text += f"\nTechnologies: {', '.join(detected[:10])}"

        all_urls = []
        if github_data.get("repositories"):
            all_urls.extend(r.get("homepage") for r in github_data["repositories"] if r.get("homepage"))
        live_demos = []
        if all_urls:
            live_demos = await self.check_live_demos(all_urls)

        live_demo_text = ""
        if live_demos:
            working = sum(1 for r in live_demos if r["status"] == "ok")
            live_demo_text = f"\nLive Demos: {working}/{len(live_demos)} working (+{min(working, 5)} bonus)"

        eval_text = convert_resume_to_evaluation_text(resume, github_text, portfolio_text, live_demo_text)
        evaluation = await self.evaluate_resume(eval_text, position_type, live_demo_text)

        improvements = []
        if evaluation:
            improvements = await self.generate_improvements(evaluation)

        name = resume.basics.name if resume.basics else "Candidate"

        if jd_text:
            await self.compute_ats_analysis(eval_text, jd_text)
            await self.match_jd(eval_text, jd_text, github_text, portfolio_text)
            await self.generate_cover_letter(eval_text, jd_text, name)

        total_score = 0
        max_score = 0
        if evaluation:
            for cat in ["open_source", "self_projects", "production", "technical_skills"]:
                cs = getattr(evaluation.scores, cat, None)
                if cs:
                    total_score += min(cs.score, cs.max)
                    max_score += cs.max
            total_score += evaluation.bonus_points.total
            total_score -= evaluation.deductions.total
            max_possible = max_score + 20
            if total_score > max_possible:
                total_score = max_possible

        # Store results in memory
        try:
            from datetime import datetime

            await self.memory.set_memory(
                self.user_id,
                "hiring_agent_last_eval",
                {
                    "name": name,
                    "overall_score": total_score,
                    "max_score": max_score,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                weight=0.9,
            )
        except Exception as e:
            logger.debug("Failed to store evaluation memory: %s", e)

        return PipelineResult(
            name=name,
            resume=resume,
            overall_score=total_score,
            max_score=max_score,
            evaluation=evaluation,
            improvements=improvements,
            live_demo_status=live_demos,
            github_summary={
                "repos": len(github_data.get("repositories", [])),
                "total_stars": sum(r.get("stars", 0) for r in github_data.get("repositories", [])),
                "contributions": github_data.get("contributions", {}),
            }
            if github_data.get("profile")
            else None,
            portfolio_summary=portfolio_data if portfolio_data.get("title") else None,
        )

    async def get_history(self, limit: int = 10) -> list[dict]:
        try:
            from sqlalchemy import desc, select

            result = await self.db.execute(
                select(MemoryEntry)
                .where(
                    MemoryEntry.user_id == self.user_id,
                    MemoryEntry.key == "hiring_agent_last_eval",
                )
                .order_by(desc(MemoryEntry.created_at))
                .limit(limit)
            )
            entries = result.scalars().all()
            return [{"id": str(e.id), **e.value} for e in entries if e.value]
        except Exception as e:
            logger.warning("Failed to load history: %s", e)
            return []

    async def generate_report_html(self, result: PipelineResult) -> str:
        evaluation = result.evaluation
        if not evaluation:
            return "<html><body><p>No evaluation data.</p></body></html>"
        pct = round(result.overall_score / max(result.max_score, 1) * 100)
        gradient = "green" if pct >= 80 else "orange" if pct >= 50 else "red"
        strengths = "".join(f"<li>{s}</li>" for s in evaluation.key_strengths)
        improvements = "".join(f"<li>{s}</li>" for s in evaluation.areas_for_improvement)
        improvs = ""
        for imp in result.improvements[:6]:
            improvs += f"""
            <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:12px;margin-bottom:8px;">
                <div style="font-size:13px;color:#94a3b8;">[{imp.category}]</div>
                <div style="margin-top:4px;color:#e2e8f0;">{imp.suggestion}</div>
                <div style="margin-top:4px;font-size:11px;color:#64748b;">
                    Impact: <b>{imp.impact.upper()}</b> | Effort: <b>{imp.effort.upper()}</b> | Priority: {imp.priority_score}/10
                </div>
            </div>"""
        demos = ""
        for d in result.live_demo_status[:10]:
            icon = {"ok": "✅", "broken": "❌", "timeout": "⏰"}.get(d["status"], "⚠️")
            demos += f'<div style="font-size:12px;margin:2px 0;">{icon} {d["url"]}</div>'
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Resume Evaluation - {result.name}</title></head>
<body style="background:#0f172a;color:#e2e8f0;font-family:system-ui,sans-serif;padding:20px;">
<div style="max-width:900px;margin:0 auto;">
<h1 style="margin-bottom:4px;">{result.name}</h1>
<div style="font-size:14px;color:#64748b;margin-bottom:24px;">Comprehensive Resume Evaluation</div>
<div style="display:flex;gap:24px;margin-bottom:32px;flex-wrap:wrap;">
<div style="background:#1e293b;border-radius:16px;padding:24px;text-align:center;min-width:200px;">
    <div style="font-size:48px;font-weight:700;color:{gradient};">{pct}%</div>
    <div style="font-size:13px;color:#64748b;">{result.overall_score}/{result.max_score} + bonuses</div>
</div>
<div style="flex:1;">
{
            "".join(
                f'''
<div style="margin-bottom:12px;">
    <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">
        <span>{cat.replace("_", " ").title()}</span>
        <span>{min(getattr(eval.scores, cat).score, getattr(eval.scores, cat).max)}/{getattr(eval.scores, cat).max}</span>
    </div>
    <div style="height:8px;background:#334155;border-radius:4px;overflow:hidden;">
        <div style="height:100%;width:{min(getattr(eval.scores, cat).score / getattr(eval.scores, cat).max * 100, 100)}%;background:linear-gradient(90deg,#3b82f6,#8b5cf6);border-radius:4px;"></div>
    </div>
</div>'''
                for cat in ["open_source", "self_projects", "production", "technical_skills"]
                if hasattr(eval.scores, cat)
            )
        }
</div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px;">
<div style="background:#1e293b;border-radius:12px;padding:16px;">
    <h3 style="margin:0 0 12px 0;font-size:15px;">✅ Key Strengths</h3>
    <ul style="margin:0;font-size:13px;color:#94a3b8;">{strengths}</ul>
</div>
<div style="background:#1e293b;border-radius:12px;padding:16px;">
    <h3 style="margin:0 0 12px 0;font-size:15px;">🔧 Areas for Improvement</h3>
    <ul style="margin:0;font-size:13px;color:#94a3b8;">{improvements}</ul>
</div>
</div>
<div style="background:#1e293b;border-radius:12px;padding:16px;margin-bottom:24px;">
    <h3 style="margin:0 0 12px 0;font-size:15px;">⭐ Bonus & Deductions</h3>
    <div style="font-size:13px;color:#94a3b8;">Bonus: +{eval.bonus_points.total} — {eval.bonus_points.breakdown}</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:4px;">Deductions: -{eval.deductions.total} — {
            eval.deductions.reasons
        }</div>
</div>
{
            f'<div style="background:#1e293b;border-radius:12px;padding:16px;margin-bottom:24px;"><h3 style="margin:0 0 12px 0;font-size:15px;">📡 Live Demos</h3>{demos}</div>'
            if demos
            else ""
        }
{
            f'<div style="background:#1e293b;border-radius:12px;padding:16px;"><h3 style="margin:0 0 12px 0;font-size:15px;">💡 Improvement Recommendations</h3>{improvs}</div>'
            if improvs
            else ""
        }
</div>
</body></html>"""
