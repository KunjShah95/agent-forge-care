import os
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, Profile, Skill, ProfileSkill, AgentTask, AgentType, TaskStatus
from app.schemas.user import (
    ProfileOut,
    ProfileUpdate,
    ProfileSkillOut,
    AddSkillRequest,
)
from app.config import settings

logger = logging.getLogger("agentforge.profile")

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
    try:
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
        # Attach user-level fields from User model for response
        profile.full_name = user.full_name
        profile.avatar_url = user.avatar_url
        return profile
    except Exception as e:
        logger.error("Failed to get profile for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


@router.put("", response_model=ProfileOut)
async def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile (and optionally user's full_name and skills)."""
    try:
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

        # ── Enqueue background scraping for GitHub / portfolio URLs ──
        github_url = update_data.get("github_url")
        portfolio_url = update_data.get("portfolio_url")
        if github_url or portfolio_url:
            try:
                from rq import Queue
                from redis import Redis
                from app.tasks.agent_tasks import process_github_scrape, process_portfolio_scrape

                redis = Redis.from_url(settings.redis_url)
                q = Queue("default", connection=redis)

                if github_url:
                    task = AgentTask(user_id=user.id, agent_type=AgentType.research, status=TaskStatus.queued, input={"query": github_url, "focus": "github_profile"})
                    db.add(task)
                    await db.flush()
                    q.enqueue(process_github_scrape, str(task.id), str(user.id), github_url)
                    logger.info("Enqueued GitHub scraping for user %s: %s", user.id, github_url)

                if portfolio_url:
                    task = AgentTask(user_id=user.id, agent_type=AgentType.research, status=TaskStatus.queued, input={"query": portfolio_url, "focus": "portfolio"})
                    db.add(task)
                    await db.flush()
                    q.enqueue(process_portfolio_scrape, str(task.id), str(user.id), portfolio_url)
                    logger.info("Enqueued portfolio scraping for user %s: %s", user.id, portfolio_url)
            except Exception:
                logger.exception("Failed to enqueue profile scraping tasks")

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
        # Attach user-level fields from User model for response
        profile.full_name = user.full_name
        profile.avatar_url = user.avatar_url
        return profile
    except Exception as e:
        logger.error("Failed to update profile for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


@router.post("/avatar", response_model=ProfileOut)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not file.filename or not isinstance(file.filename, str):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_AVATAR_TYPES)}",
        )
    
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    # Validate file content (magic bytes) in addition to content-type
    _VALID_MAGIC_BYTES = {
        b"\xff\xd8\xff": "image/jpeg",
        b"\x89PNG": "image/png",
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
        b"RIFF": "image/webp",
    }
    is_valid_content = any(content.startswith(magic) for magic in _VALID_MAGIC_BYTES)
    if not is_valid_content:
        raise HTTPException(status_code=400, detail="File content does not match image format")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "png"
    # Only allow safe extensions
    if ext.lower() not in {"jpg", "jpeg", "png", "gif", "webp"}:
        ext = "png"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = AVATAR_DIR / filename
    os.makedirs(AVATAR_DIR, exist_ok=True)
    filepath.write_bytes(content)

    try:
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

        user.avatar_url = f"/uploads/avatars/{filename}"
        profile.full_name = user.full_name
        profile.avatar_url = user.avatar_url
        await db.flush()
        return profile
    except Exception as e:
        logger.error("Failed to upload avatar for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")


@router.get("/skills", response_model=list[ProfileSkillOut])
async def get_skills(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all skills for the current user."""
    try:
        result = await db.execute(
            select(ProfileSkill)
            .options(selectinload(ProfileSkill.skill))
            .join(Skill, ProfileSkill.skill_id == Skill.id)
            .join(Profile, ProfileSkill.profile_id == Profile.id)
            .where(Profile.user_id == user.id)
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error("Failed to get skills for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get skills: {str(e)}")


@router.post("/skills", response_model=ProfileSkillOut, status_code=201)
async def add_skill(
    data: AddSkillRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a skill to the user's profile."""
    # Input validation
    if not data.name or not isinstance(data.name, str) or len(data.name.strip()) < 2:
        raise HTTPException(status_code=422, detail="Skill name must be a non-empty string with at least 2 characters")
    
    if not data.proficiency or not isinstance(data.proficiency, str) or data.proficiency not in ["beginner", "intermediate", "advanced", "expert"]:
        raise HTTPException(status_code=422, detail="Proficiency must be one of: beginner, intermediate, advanced, expert")

    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add skill for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to add skill: {str(e)}")


@router.delete("/skills/{skill_id}", status_code=204)
async def remove_skill(
    skill_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a skill from the user's profile."""
    # Input validation
    if not skill_id or not isinstance(skill_id, str) or len(skill_id.strip()) < 1:
        raise HTTPException(status_code=422, detail="Skill ID must be a non-empty string")

    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove skill for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to remove skill: {str(e)}")
