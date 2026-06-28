import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import Profile, ProfileSkill, Skill

logger = logging.getLogger("agentforge.services.profile")


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_profile(self, user_id: str) -> Profile:
        try:
            result = await self.db.execute(
                select(Profile).where(Profile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if not profile:
                profile = Profile(user_id=user_id)
                self.db.add(profile)
                await self.db.flush()
            return profile
        except Exception as e:
            logger.error("Failed to get or create profile for user %s: %s", user_id, str(e))
            raise

    async def get_profile_skills(self, profile_id: str) -> list[ProfileSkill]:
        try:
            result = await self.db.execute(
                select(ProfileSkill).where(ProfileSkill.profile_id == profile_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Failed to get skills for profile %s: %s", profile_id, str(e))
            raise

    async def add_skill(
        self, profile_id: str, name: str, proficiency: str = "intermediate"
    ) -> ProfileSkill:
        try:
            if not name or not isinstance(name, str) or len(name.strip()) < 1:
                raise ValueError("Skill name must be a non-empty string")

            skill_result = await self.db.execute(select(Skill).where(Skill.name == name))
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

            ps = ProfileSkill(
                profile_id=profile_id, skill_id=skill.id, proficiency=proficiency
            )
            self.db.add(ps)
            await self.db.flush()
            return ps
        except Exception as e:
            logger.error("Failed to add skill '%s' to profile %s: %s", name, profile_id, str(e))
            raise

    async def get_skill_names(self, profile_id: str) -> list[str]:
        try:
            result = await self.db.execute(
                select(Skill.name)
                .join(ProfileSkill, ProfileSkill.skill_id == Skill.id)
                .where(ProfileSkill.profile_id == profile_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Failed to get skill names for profile %s: %s", profile_id, str(e))
            raise
