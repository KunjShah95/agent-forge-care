from decimal import Decimal
from datetime import date, timezone
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import (
    Profile, Opportunity, MatchScore, MemoryEntry,
)
from app.services.profile_service import ProfileService
from app.services.rerank_service import get_reranker

logger = logging.getLogger("agentforge.match")


class MatchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._reranker = None

    @property
    def reranker(self):
        """Lazy-load the reranker singleton."""
        if self._reranker is None:
            self._reranker = get_reranker()
        return self._reranker

    async def calculate_match(self, user_id: str, opportunity: Opportunity) -> dict:
        """Calculate match score for a single opportunity."""
        profile_service = ProfileService(self.db)
        profile = await profile_service.get_or_create_profile(user_id)
        skills = await profile_service.get_skill_names(profile.id)

        # Get memory preferences
        mem_result = await self.db.execute(
            select(MemoryEntry).where(
                MemoryEntry.user_id == user_id,
                MemoryEntry.key == "preferences",
            )
        )
        preferences = mem_result.scalar_one_or_none()

        # Skills match
        profile_skills = set(s.lower() for s in skills)
        required_skills = set(s.lower() for s in (opportunity.skills_required or []))
        skill_match = (
            len(profile_skills & required_skills) / max(len(required_skills), 1) * 100
        )

        # Location match
        location_match = 100.0
        if opportunity.location:
            preferred = [l.lower() for l in (profile.target_locations or [])]
            opp_loc = opportunity.location.lower()
            if "remote" not in opp_loc and opp_loc not in preferred and "remote" not in preferred:
                location_match = 40.0

        # Company size match
        pref_sizes = profile.company_sizes or []
        company_match = 100.0
        if pref_sizes and opportunity.company_size:
            if opportunity.company_size not in pref_sizes:
                company_match = 60.0

        # Calculate weighted score
        weights = {"skills": 0.35, "location": 0.20, "company": 0.15}
        overall = (
            weights["skills"] * skill_match
            + weights["location"] * location_match
            + weights["company"] * company_match
        )
        overall = min(100.0, overall)

        # Generate reasons
        reasons = []
        if skill_match >= 70:
            matched = profile_skills & required_skills
            reasons.append(f"Skills match: {', '.join(matched)[:60]}")
        if location_match >= 80:
            reasons.append("Location preference aligned")
        if opportunity.remote:
            reasons.append("Remote-friendly")

        return {
            "overall": round(overall, 1),
            "breakdown": {
                "skills": round(skill_match, 1),
                "location": round(location_match, 1),
                "company": round(company_match, 1),
            },
            "reasons": reasons[:5],
        }

    async def score_all_active(self, user_id: str) -> int:
        """Score all active opportunities for a user."""
        result = await self.db.execute(
            select(Opportunity).where(
                Opportunity.user_id == user_id,
                Opportunity.is_active == True,
            )
        )
        opportunities = result.scalars().all()

        scored_count = 0
        for opp in opportunities:
            match_data = await self.calculate_match(user_id, opp)

            # Upsert match score
            existing = await self.db.execute(
                select(MatchScore).where(
                    MatchScore.opportunity_id == opp.id,
                    MatchScore.user_id == user_id,
                )
            )
            ms = existing.scalar_one_or_none()
            if ms:
                ms.overall_score = Decimal(str(match_data["overall"]))
                ms.skill_score = Decimal(str(match_data["breakdown"]["skills"]))
                ms.location_score = Decimal(str(match_data["breakdown"]["location"]))
                ms.company_score = Decimal(str(match_data["breakdown"]["company"]))
                ms.reasons = match_data["reasons"]
            else:
                ms = MatchScore(
                    opportunity_id=opp.id,
                    user_id=user_id,
                    overall_score=Decimal(str(match_data["overall"])),
                    skill_score=Decimal(str(match_data["breakdown"]["skills"])),
                    location_score=Decimal(str(match_data["breakdown"]["location"])),
                    company_score=Decimal(str(match_data["breakdown"]["company"])),
                    reasons=match_data["reasons"],
                )
                self.db.add(ms)
            scored_count += 1

        await self.db.flush()
        return scored_count

    async def rerank_and_blend(
        self,
        user_id: str,
        query: str,
        items: list[dict],
        blend_weight: float = 0.4,
    ) -> list[dict]:
        """
        Rerank opportunity items with Cohere and blend scores.

        Takes items returned by discover_internships/discover_jobs,
        reranks them semantically against the user's query, and blends
        the Cohere relevance score with the rule-based match_score.

        Args:
            user_id: User identifier for context.
            query: The original search query/goal.
            items: List of opportunity dicts with 'title', 'company',
                   'description', 'match_score' keys.
            blend_weight: How much weight to give the rerank score
                          (0.0 = pure rule-based, 1.0 = pure rerank).

        Returns:
            Items sorted by blended score, each with added
            'relevance_score', 'rerank_score', and 'final_score' fields.
        """
        if not items or not query:
            return items

        # Rerank with Cohere
        reranked = await self.reranker.rerank_with_scores(
            query=query,
            documents=items,
            top_n=len(items),
        )

        # Blend scores
        for item in reranked:
            orig_score = item.get("match_score", 0) or 0
            rerank_score = item.get("rerank_score")
            item["final_score"] = self.reranker.blend_scores(
                orig_score, rerank_score, blend_weight
            )

        # Sort by final score descending
        reranked.sort(key=lambda d: d.get("final_score", 0), reverse=True)

        # Update the match_score to reflect the blended score
        for item in reranked:
            item["match_score"] = item.get("final_score", item.get("match_score", 0))

        logger.debug(
            "Reranked %d items for user %s (query=%s, blend=%.1f)",
            len(reranked), user_id, query[:50], blend_weight,
        )

        return reranked
