"""
Opportunity Agent Service — class-based service for discovering, scoring,
analyzing, and generating feedback on job/internship opportunities.

Follows the same pattern as HiringAgentService for consistency.
"""

import json
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import (
    Opportunity,
    MatchScore,
    AlertConfig,
    AgentType,
)
from app.services.profile_service import ProfileService
from app.services.memory_service import MemoryService
from app.services.match_service import MatchService
from app.services.model_manager import get_completion_llm
from app.search.adapters import SearchAdapter
from app.memory.memory_layer import AgentMemory
from app.utils.embedding import get_text_embedding
from app.utils.location import parse_location
from app.utils.industry import detect_industry
from app.utils.work_mode import infer_work_type, categorize_search_keyword
from app.opportunity_agent.schemas import (
    ScoredOpportunityItem,
    OpportunityFeedback,
    OpportunityAnalysis,
    OpportunityResult,
    OpportunityScanResult,
)
from app.opportunity_agent.prompts.template_manager import load_template, render_template

logger = logging.getLogger("agentforge.opportunity_agent.service")


class OpportunityAgentService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id
        self.memory_service = MemoryService(db)
        self.profile_service = ProfileService(db)
        self.match_service = MatchService(db)
        self.search_adapter = SearchAdapter()

    # ─── Core Discovery ──────────────────────────────────────

    async def discover(
        self,
        query: str,
        location: Optional[str] = None,
        skills: Optional[list[str]] = None,
        limit: int = 20,
        source_filter: str = "job",
        opp_type: str = "Full-time",
    ) -> OpportunityResult:
        skills = skills or []
        profile = await self.profile_service.get_or_create_profile(self.user_id)
        profile_skills = await self.profile_service.get_skill_names(profile.id)
        all_skills = list(set(skills + profile_skills))

        raw_results = await self._search_external(query, location, all_skills, limit, source_filter)
        items = await self._process_results(raw_results, limit, all_skills, opp_type, source_filter)

        if items and query:
            reranked = await self.match_service.rerank_and_blend(
                self.user_id, query, items, blend_weight=0.4
            )
            items = reranked

        analysis = self._compute_analysis(items)
        feedback = await self._generate_feedback(
            items, query, source_filter, all_skills, profile
        )

        await self._store_memory(query, location, items, source_filter)

        return OpportunityResult(
            items=[ScoredOpportunityItem(**i) for i in items],
            total=len(items),
            agent=source_filter,
            message=f"Found {len(items)} {source_filter} opportunities",
            summary=f"Discovered {len(items)} {source_filter}s matching your skills in {', '.join(all_skills[:3])}",
            analysis=analysis,
            feedback=feedback,
            search_metadata={
                "query": query,
                "location": location,
                "skills": all_skills,
                "limit": limit,
            },
        )

    # ─── Monitor Scan ────────────────────────────────────────

    async def run_scan(
        self,
        search_query: Optional[str] = None,
        keywords: Optional[list[str]] = None,
    ) -> OpportunityScanResult:
        if not keywords:
            result = await self.db.execute(
                select(AlertConfig).where(
                    AlertConfig.user_id == self.user_id,
                    AlertConfig.is_active.is_(True),
                )
            )
            alert_configs = result.scalars().all()
            keywords = []
            for config in alert_configs:
                keywords.extend(config.keywords or [])

        if not keywords:
            profile = await self.profile_service.get_or_create_profile(self.user_id)
            keywords = profile.role_types or ["internship", "job"]

        if search_query and search_query not in keywords:
            keywords.insert(0, search_query)

        all_new_items = []
        for keyword in keywords[:3]:
            kw = (keyword or "").strip()
            if not kw:
                continue
            category = categorize_search_keyword(kw)
            try:
                results = await self.search_adapter.search(
                    query=kw, limit=8, source_filter=category
                )
                for r in results:
                    r.setdefault("_category", category)
                all_new_items.extend(results)
            except Exception as e:
                logger.debug("Monitor scan error for %s: %s", kw, e)

        if not all_new_items:
            # No real results found — return empty rather than generating fake data
            pass

        existing_keys = await self._get_existing_keys()
        seen_keys = set()
        stored_items = []
        profile = await self.profile_service.get_or_create_profile(self.user_id)
        all_skills = await self.profile_service.get_skill_names(profile.id)

        for item in all_new_items[:20]:
            title = item.get("title", "")
            if not title:
                continue
            company = item.get("company", "Tech Company")
            key = (title.lower().strip(), (company or "").lower().strip())
            if key in seen_keys or key in existing_keys:
                continue
            seen_keys.add(key)

            opp = await self._create_opportunity(item, all_skills)
            if not opp:
                continue

            match_data = await self.match_service.calculate_match(self.user_id, opp)
            await self._store_match_score(opp, match_data)

            stored_items.append({
                "id": str(opp.id),
                "title": opp.title,
                "company": opp.company,
                "location": opp.location,
                "description": opp.description or "",
                "skills_required": opp.skills_required or [],
                "match_score": match_data["overall"],
                "reason": match_data["reasons"][0] if match_data["reasons"] else "",
                "type": opp.type,
            })

        scored_count = await self.match_service.score_all_active(self.user_id)

        alerts = await self._generate_alerts(stored_items)

        await self._store_scan_memory(stored_items, scored_count, len(alerts))

        analysis = OpportunityAnalysis(
            total_found=len(stored_items),
            high_match_count=sum(1 for i in stored_items if i["match_score"] >= 80),
            average_score=round(sum(i["match_score"] for i in stored_items) / max(len(stored_items), 1), 1),
        )

        feedback = None
        if stored_items:
            feedback = await self._generate_scan_feedback(stored_items, all_skills, profile)

        return OpportunityScanResult(
            items=[ScoredOpportunityItem(**i) for i in stored_items],
            total=len(stored_items),
            scored=scored_count,
            alerts=alerts[:10],
            message=f"Scan completed: {len(stored_items)} new items, {scored_count} scored, {len(alerts)} high-match alerts",
            analysis=analysis,
            feedback=feedback,
        )

    # ─── Internal: Search ────────────────────────────────────

    async def _search_external(
        self, query: str, location: Optional[str],
        skills: list[str], limit: int, source_filter: str,
    ) -> list[dict]:
        try:
            raw = await self.search_adapter.search(
                query=query, location=location, skills=skills,
                limit=limit, source_filter=source_filter,
            )
            if raw:
                return raw
        except Exception as e:
            logger.warning("External search failed: %s", e)

        # Return empty list instead of demo data — never mix fake data with real results
        return []

    async def _get_existing_keys(self) -> set:
        result = await self.db.execute(
            select(Opportunity.title, Opportunity.company).where(
                Opportunity.user_id == self.user_id
            )
        )
        return {
            (t.lower().strip(), (c or "").lower().strip())
            for t, c in result.all() if t
        }

    async def _process_results(
        self, raw_results: list[dict], limit: int,
        all_skills: list[str], opp_type: str, source_filter: str,
    ) -> list[dict]:
        profile = await self.profile_service.get_or_create_profile(self.user_id)
        salary_min = profile.salary_min
        existing_keys = await self._get_existing_keys()

        items = []
        seen_keys = set()
        for r in raw_results[:limit]:
            job_salary_min = r.get("salary_min")
            if salary_min and job_salary_min and job_salary_min < salary_min * 0.7:
                continue

            title = r.get("title", "Untitled Position")
            company = r.get("company", "Unknown")
            key = (title.lower().strip(), (company or "").lower().strip())
            if key in seen_keys or key in existing_keys:
                continue
            seen_keys.add(key)

            opp = await self._create_opportunity(r, all_skills, opp_type)
            if not opp:
                continue

            match_data = await self.match_service.calculate_match(self.user_id, opp)
            await self._store_match_score(opp, match_data)
            await self._store_opportunity_embedding(self.user_id, opp, match_data)

            items.append({
                "id": str(opp.id),
                "title": opp.title,
                "company": opp.company,
                "location": opp.location,
                "description": opp.description or "",
                "skills_required": opp.skills_required or [],
                "match_score": match_data["overall"],
                "reason": match_data["reasons"][0] if match_data["reasons"] else "",
                "industry": opp.industry,
                "work_type": opp.work_type,
                "salary_min": opp.salary_min,
                "salary_max": opp.salary_max,
                "apply_url": opp.apply_url,
                "company_size": opp.company_size,
                "source": opp.source,
            })

        await self.db.flush()
        return items

    async def _create_opportunity(
        self, r: dict, all_skills: list[str], opp_type: Optional[str] = None
    ) -> Optional[Opportunity]:
        title = r.get("title", "Untitled Position") if not r.get("title") else r.get("title")
        company = r.get("company", "Unknown")
        loc_raw = r.get("location")
        parsed = parse_location(loc_raw)

        industry = detect_industry(
            title=title,
            company=company,
            description=r.get("description", ""),
        )
        remote = r.get("remote", False)
        work_type = r.get("work_type") or infer_work_type(
            remote, title, r.get("description"), loc_raw
        )

        actual_type = opp_type or r.get("type") or (
            "Internship" if r.get("_category") == "internship" else "Full-time"
        )

        opp = Opportunity(
            user_id=self.user_id,
            title=title,
            company=company,
            company_logo=r.get("logo"),
            location=loc_raw,
            city=parsed["city"],
            state=parsed["state"],
            country=parsed["country"],
            industry=industry,
            remote=remote,
            work_type=work_type,
            type=actual_type,
            salary_min=r.get("salary_min"),
            salary_max=r.get("salary_max"),
            description=r.get("description"),
            apply_url=r.get("apply_url"),
            company_size=r.get("company_size"),
            skills_required=r.get("skills", all_skills),
            source=r.get("source", "opportunity_agent"),
            posted_date=r.get("posted_date"),
            deadline=r.get("deadline"),
        )
        self.db.add(opp)
        await self.db.flush()
        return opp

    async def _store_match_score(self, opp: Opportunity, match_data: dict):
        ms = MatchScore(
            opportunity_id=opp.id,
            user_id=self.user_id,
            overall_score=Decimal(str(match_data["overall"])),
            skill_score=Decimal(str(match_data["breakdown"]["skills"])),
            location_score=Decimal(str(match_data["breakdown"]["location"])),
            company_score=Decimal(str(match_data["breakdown"]["company"])),
            experience_score=Decimal(str(match_data["breakdown"]["experience"])),
            reasons=match_data["reasons"],
        )
        self.db.add(ms)

    # ─── LLM Feedback ────────────────────────────────────────

    async def _generate_feedback(
        self, items: list[dict], query: str, agent_type: str,
        all_skills: list[str], profile,
    ) -> OpportunityFeedback:
        llm = get_completion_llm(temperature=0.3, preferred_provider="openai")
        if not llm or not items:
            return self._fallback_feedback(items, query)

        top_items = sorted(items, key=lambda x: x.get("match_score", 0), reverse=True)[:5]
        template = load_template("opportunity_feedback.jinja")
        prompt = render_template(
            template,
            user_skills=", ".join(all_skills) or "not specified",
            target_locations=", ".join(profile.target_locations or ["Remote"]),
            role_types=", ".join(profile.role_types or [agent_type]),
            career_goal=profile.career_goal or "Not defined",
            search_query=query,
            agent_type=agent_type,
            total_results=len(items),
            top_items=top_items,
        )

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            response = await llm.ainvoke([
                SystemMessage(content="You are an expert career opportunity analyst. Return ONLY valid JSON."),
                HumanMessage(content=prompt),
            ])
            text = response.content.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                text = text[json_start:json_end + 1]
            data = json.loads(text)
            return OpportunityFeedback(**data)
        except Exception as e:
            logger.warning("LLM feedback generation failed: %s", e)
            return self._fallback_feedback(items, query)

    async def _generate_scan_feedback(
        self, items: list[dict], all_skills: list[str], profile,
    ) -> Optional[OpportunityFeedback]:
        llm = get_completion_llm(temperature=0.3, preferred_provider="openai")
        if not llm or not items:
            return None

        high_match = [i for i in items if i.get("match_score", 0) >= 80]
        template = load_template("scan_feedback.jinja")
        prompt = render_template(
            template,
            user_skills=", ".join(all_skills) or "not specified",
            target_locations=", ".join(profile.target_locations or ["Remote"]),
            career_goal=profile.career_goal or "Not defined",
            new_items_count=len(items),
            high_match_count=len(high_match),
            avg_score=round(sum(i.get("match_score", 0) for i in items) / max(len(items), 1), 1),
            new_items=items[:10],
        )

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            response = await llm.ainvoke([
                SystemMessage(content="You are an expert career monitor analyst. Return ONLY valid JSON."),
                HumanMessage(content=prompt),
            ])
            text = response.content.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                text = text[json_start:json_end + 1]
            data = json.loads(text)
            return OpportunityFeedback(**data)
        except Exception as e:
            logger.warning("Scan feedback generation failed: %s", e)
            return None

    def _fallback_feedback(self, items: list[dict], query: str) -> OpportunityFeedback:
        high_match = [i for i in items if i.get("match_score", 0) >= 80]
        return OpportunityFeedback(
            overall_assessment=f"Found {len(items)} opportunities matching your search.",
            top_matches_summary=f"{len(high_match)} high-match opportunities identified." if high_match else "No high-match opportunities found.",
            skill_gaps=[],
            improvement_suggestions=[
                "Try broadening your search keywords",
                "Add more skills to your profile for better matching",
                "Consider remote opportunities for wider selection",
            ],
            search_refinements=[
                f"Try different keywords related to '{query}'",
                "Expand location preferences",
            ],
            market_insight=None,
        )

    # ─── Analysis ────────────────────────────────────────────

    def _compute_analysis(self, items: list[dict]) -> OpportunityAnalysis:
        if not items:
            return OpportunityAnalysis(total_found=0, high_match_count=0, average_score=0.0)

        scores = [i.get("match_score", 0) or 0 for i in items]
        industries = [i.get("industry") for i in items if i.get("industry")]
        skills = []
        for i in items:
            skills.extend(i.get("skills_required", []) or [])
        from collections import Counter
        top_industries = [ind for ind, _ in Counter(industries).most_common(5)] if industries else []
        common_skills = [s for s, _ in Counter(s.lower() for s in skills).most_common(10)] if skills else []
        remote_ratio = sum(1 for i in items if i.get("work_type") == "remote" or i.get("remote")) / max(len(items), 1)

        return OpportunityAnalysis(
            total_found=len(items),
            high_match_count=sum(1 for s in scores if s >= 80),
            average_score=round(sum(scores) / len(scores), 1),
            top_industries=top_industries,
            common_skills=common_skills,
            remote_ratio=round(remote_ratio, 2),
        )

    # ─── Alerts ──────────────────────────────────────────────

    async def _generate_alerts(self, items: list[dict]) -> list[dict]:
        from app.services.notification_service import create_notification
        from app.models.user import User

        alerts = []
        for item in items:
            if item.get("match_score", 0) >= 80:
                alerts.append({
                    "opportunity_id": item["id"],
                    "title": item["title"],
                    "company": item["company"],
                    "match_score": item["match_score"],
                    "message": f"High match: {item['title']} @ {item['company']} ({item['match_score']:.0f}%)",
                })

        user_result = await self.db.execute(select(User).where(User.id == self.user_id))
        user = user_result.scalar_one_or_none()

        for alert in alerts[:10]:
            await create_notification(
                self.db, self.user_id,
                title=f"High match: {alert['title']} @ {alert['company']}",
                body=alert["message"],
                type="success",
                to_email=user.email if (user and user.email) else None,
            )
        return alerts

    # ─── Memory ──────────────────────────────────────────────

    async def _store_memory(self, query: str, location: Optional[str], items: list[dict], agent_type: str):
        key = f"last_{agent_type}_search"
        await self.memory_service.set_memory(
            self.user_id, key,
            {
                "query": query,
                "location": location,
                "results_count": len(items),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            weight=0.8,
        )

    async def _store_scan_memory(self, items: list[dict], scored_count: int, alert_count: int):
        await self.memory_service.set_memory(
            self.user_id, "last_daily_scan",
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "new_items": len(items),
                "scored": scored_count,
                "alerts": alert_count,
            },
            weight=0.6,
        )

    async def _store_opportunity_embedding(self, user_id: str, opp: Opportunity, match_data: dict):
        try:
            agent_memory = AgentMemory(user_id)
            text = f"{opp.title} at {opp.company}. {opp.description or ''}"
            vector = await get_text_embedding(text)
            agent_memory.store_vector(
                collection="opportunity_embeddings",
                text=text,
                vector=vector,
                metadata={
                    "title": opp.title,
                    "company": opp.company,
                    "type": opp.type,
                    "match_score": match_data["overall"],
                    "opportunity_id": str(opp.id),
                },
            )
        except Exception as e:
            logger.debug("Failed to store opportunity embedding: %s", e)

    # ─── Recommendations ─────────────────────────────────────

    async def get_recommendations(self, opp_type: str, limit: int = 10) -> list[dict]:
        from sqlalchemy import desc

        result = await self.db.execute(
            select(Opportunity, MatchScore)
            .join(MatchScore, Opportunity.id == MatchScore.opportunity_id)
            .where(
                Opportunity.user_id == self.user_id,
                Opportunity.type == opp_type,
                Opportunity.is_active.is_(True),
            )
            .order_by(desc(MatchScore.overall_score))
            .limit(limit)
        )
        rows = result.all()

        return [
            {
                "id": str(opp.id),
                "title": opp.title,
                "company": opp.company,
                "location": opp.location,
                "remote": opp.remote,
                "match_score": float(ms.overall_score),
                "reasons": ms.reasons or [],
            }
            for opp, ms in rows
        ]

    # ─── New: enhanced feedback with reasoning ───────────────

    async def analyze_opportunity_fit(self, opportunity_id: str) -> dict:
        """Generate detailed LLM-based analysis of why an opportunity fits the user."""
        result = await self.db.execute(
            select(Opportunity, MatchScore)
            .join(MatchScore, Opportunity.id == MatchScore.opportunity_id)
            .where(
                Opportunity.id == opportunity_id,
                Opportunity.user_id == self.user_id,
            )
        )
        row = result.one_or_none()
        if not row:
            return {"error": "Opportunity not found"}

        opp, ms = row
        profile = await self.profile_service.get_or_create_profile(self.user_id)
        all_skills = await self.profile_service.get_skill_names(profile.id)

        llm = get_completion_llm(temperature=0.4, preferred_provider="openai")
        if not llm:
            return {
                "id": str(opp.id),
                "title": opp.title,
                "company": opp.company,
                "match_score": float(ms.overall_score),
                "reasons": ms.reasons or [],
                "detailed_analysis": None,
            }

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            prompt = f"""Analyze the fit between this candidate and the opportunity.

CANDIDATE SKILLS: {', '.join(all_skills)}
CAREER GOAL: {profile.career_goal or 'Not defined'}

OPPORTUNITY: {opp.title} @ {opp.company}
DESCRIPTION: {opp.description or 'N/A'}
REQUIRED SKILLS: {', '.join(opp.skills_required or [])}
INDUSTRY: {opp.industry or 'N/A'}
LOCATION: {opp.location or 'Remote'}
WORK TYPE: {opp.work_type or 'N/A'}

MATCH SCORE: {float(ms.overall_score)}/100
MATCH REASONS: {'; '.join(ms.reasons or [])}

Return a JSON object with:
{{
    "detailed_analysis": "2-3 paragraph analysis of why this is a good (or poor) fit",
    "strengths": ["Array of 2-3 specific strengths the candidate brings"],
    "weaknesses": ["Array of 1-2 gaps or concerns"],
    "preparation_tips": ["Array of 2-3 tips for applying to this specific role"],
    "recommendation": "strong_apply" | "apply" | "consider" | "skip"
}}

Be specific — reference actual skills, technologies, and job requirements.
Return ONLY valid JSON. No markdown."""
            response = await llm.ainvoke([
                SystemMessage(content="You are an expert career fit analyst. Return ONLY valid JSON."),
                HumanMessage(content=prompt),
            ])
            text = response.content.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                text = text[json_start:json_end + 1]
            data = json.loads(text)

            return {
                "id": str(opp.id),
                "title": opp.title,
                "company": opp.company,
                "match_score": float(ms.overall_score),
                "reasons": ms.reasons or [],
                **data,
            }
        except Exception as e:
            logger.warning("Opportunity fit analysis failed: %s", e)
            return {
                "id": str(opp.id),
                "title": opp.title,
                "company": opp.company,
                "match_score": float(ms.overall_score),
                "reasons": ms.reasons or [],
                "detailed_analysis": None,
            }
