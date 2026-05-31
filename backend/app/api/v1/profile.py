import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, Profile, Skill, ProfileSkill
from app.schemas.user import (
    ProfileOut,
    ProfileUpdate,
    ProfileSkillOut,
    SkillOut,
    AddSkillRequest,
)

AVATAR_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "uploads" / "avatars"
)

router = APIRouter()


@router.get("", response_model=ProfileOut)
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's full profile with skills."""
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.skills).selectinload(ProfileSkill.skill))
        .where(Profile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.flush()
        result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.skills).selectinload(ProfileSkill.skill))
            .where(Profile.id == profile.id)
        )
        profile = result.scalar_one_or_none() or profile
    return profile


@router.put("", response_model=ProfileOut)
async def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile (and optionally user's full_name and skills)."""
    if data.full_name is not None:
        user.full_name = data.full_name

    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.flush()

    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("full_name", None)
    skills_data = update_data.pop("skills", None)

    for key, value in update_data.items():
        setattr(profile, key, value)

    if skills_data:
        existing = await db.execute(
            select(ProfileSkill).where(ProfileSkill.profile_id == profile.id)
        )
        existing_skills = {ps.skill_id: ps for ps in existing.scalars().all()}

        for skill_req in skills_data:
            skill_name = getattr(skill_req, "name", None)
            if skill_name is None and isinstance(skill_req, dict):
                skill_name = skill_req.get("name")

            proficiency = getattr(skill_req, "proficiency", None)
            if proficiency is None and isinstance(skill_req, dict):
                proficiency = skill_req.get("proficiency", "intermediate")
            if proficiency is None:
                proficiency = "intermediate"

            if not skill_name:
                continue

            skill_result = await db.execute(
                select(Skill).where(Skill.name == skill_name)
            )
            skill = skill_result.scalar_one_or_none()
            if not skill:
                skill = Skill(name=skill_name)
                db.add(skill)
                await db.flush()

            if skill.id in existing_skills:
                existing_skills[skill.id].proficiency = proficiency
                continue

            ps = ProfileSkill(
                profile_id=profile.id,
                skill_id=skill.id,
                proficiency=proficiency,
            )
            db.add(ps)

    await db.flush()
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.skills).selectinload(ProfileSkill.skill))
        .where(Profile.id == profile.id)
    )
    profile = result.scalar_one_or_none() or profile
    return profile


ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


@router.post("/avatar", response_model=ProfileOut)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_AVATAR_TYPES)}",
        )
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "png"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = AVATAR_DIR / filename
    filepath.write_bytes(content)

    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.skills).selectinload(ProfileSkill.skill))
        .where(Profile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.flush()

    profile.avatar_url = f"/uploads/avatars/{filename}"
    await db.flush()
    return profile


@router.get("/skills", response_model=list[ProfileSkillOut])
async def get_skills(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all skills for the current user."""
    result = await db.execute(
        select(ProfileSkill)
        .options(selectinload(ProfileSkill.skill))
        .join(Skill, ProfileSkill.skill_id == Skill.id)
        .join(Profile, ProfileSkill.profile_id == Profile.id)
        .where(Profile.user_id == user.id)
    )
    return list(result.scalars().all())


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

    ps = ProfileSkill(
        profile_id=profile.id, skill_id=skill.id, proficiency=data.proficiency
    )
    ps.skill = skill
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
