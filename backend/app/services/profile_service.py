from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import Profile, ProfileSkill, Skill, Opportunity


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_profile(self, user_id: str) -> Profile:
        result = await self.db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            profile = Profile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()
        return profile

    async def get_profile_skills(self, profile_id: str) -> list[ProfileSkill]:
        result = await self.db.execute(
            select(ProfileSkill)
            .where(ProfileSkill.profile_id == profile_id)
        )
        return list(result.scalars().all())

    async def add_skill(self, profile_id: str, name: str, proficiency: str = "intermediate") -> ProfileSkill:
        skill_result = await self.db.execute(
            select(Skill).where(Skill.name == name)
        )
        skill = skill_result.scalar_one_or_none()
        if not skill:
            skill = Skill(name=name)
            self.db.add(skill)
            await self.db.flush()

        ps_result = await self.db.execute(
            select(ProfileSkill).where(
                ProfileSkill.profile_id == profile_id,
                ProfileSkill.skill_id == skill.id,
            )
        )
        existing = ps_result.scalar_one_or_none()
        if existing:
            return existing

        ps = ProfileSkill(profile_id=profile_id, skill_id=skill.id, proficiency=proficiency)
        self.db.add(ps)
        await self.db.flush()
        return ps

    async def get_skill_names(self, profile_id: str) -> list[str]:
        skills = await self.get_profile_skills(profile_id)
        names = []
        for ps in skills:
            skill_result = await self.db.execute(
                select(Skill).where(Skill.id == ps.skill_id)
            )
            skill = skill_result.scalar_one_or_none()
            if skill:
                names.append(skill.name)
        return names
