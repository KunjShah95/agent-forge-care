from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, Profile, Skill, ProfileSkill
from app.schemas.user import ProfileOut, ProfileUpdate, ProfileSkillOut, SkillOut, AddSkillRequest

router = APIRouter()


@router.get("", response_model=ProfileOut)
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's full profile with skills."""
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.flush()
    return profile


@router.put("", response_model=ProfileOut)
async def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile."""
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.flush()

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    await db.flush()
    return profile


@router.get("/skills", response_model=list[ProfileSkillOut])
async def get_skills(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all skills for the current user."""
    result = await db.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []
    await db.flush()
    # Re-fetch with relationship loaded
    profile_result = await db.execute(
        select(Profile).where(Profile.id == profile.id)
    )
    profile = profile_result.scalar_one()
    return profile.skills


@router.post("/skills", response_model=ProfileSkillOut, status_code=201)
async def add_skill(
    data: AddSkillRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a skill to the user's profile."""
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.flush()

    # Find or create the skill
    skill_result = await db.execute(select(Skill).where(Skill.name == data.name))
    skill = skill_result.scalar_one_or_none()
    if not skill:
        skill = Skill(name=data.name)
        db.add(skill)
        await db.flush()

    # Check if already exists
    existing = await db.execute(
        select(ProfileSkill).where(
            ProfileSkill.profile_id == profile.id,
            ProfileSkill.skill_id == skill.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Skill already added")

    ps = ProfileSkill(profile_id=profile.id, skill_id=skill.id, proficiency=data.proficiency)
    db.add(ps)
    await db.flush()
    return ps


@router.delete("/skills/{skill_id}", status_code=204)
async def remove_skill(
    skill_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a skill from the user's profile."""
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    ps_result = await db.execute(
        select(ProfileSkill).where(
            ProfileSkill.profile_id == profile.id,
            ProfileSkill.skill_id == skill_id,
        )
    )
    ps = ps_result.scalar_one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="Skill not found on profile")
    await db.delete(ps)
