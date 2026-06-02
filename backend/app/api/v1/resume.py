import logging
import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, MemoryEntry, AgentTask, AgentType, TaskStatus, Profile, Skill, ProfileSkill
from app.schemas.user import ResumeOut, ResumeList
import pypdf
from app.utils.embedding import get_text_embedding
from app.memory.memory_layer import AgentMemory
from app.services.notification_service import create_notification
from app.config import settings

logger = logging.getLogger("agentforge.resume")

ACTION_VERBS = [
    "achieved", "analyzed", "built", "conducted", "created", "delivered",
    "designed", "developed", "established", "evaluated", "executed",
    "expanded", "generated", "identified", "implemented", "improved",
    "increased", "initiated", "integrated", "introduced", "launched",
    "led", "managed", "negotiated", "optimized", "organized", "performed",
    "planned", "produced", "reduced", "reorganized", "resolved",
    "revamped", "streamlined", "strengthened", "structured", "supervised",
    "transformed", "upgraded", "accelerated", "automated", "consolidated",
    "coordinated", "cultivated", "demonstrated", "deployed", "engineered",
    "facilitated", "formulated", "oversaw",
]

SECTION_HEADERS = [
    "experience", "education", "skills", "projects",
    "work experience", "employment", "summary", "objective",
    "certifications", "publications", "leadership",
]

router = APIRouter()


@router.get("", response_model=ResumeList)
async def list_resumes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MemoryEntry)
        .where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.key.like("resume_%"),
        )
        .order_by(MemoryEntry.created_at.desc())
    )
    entries = result.scalars().all()
    items = []
    for e in entries:
        val = e.value or {}
        items.append(
            ResumeOut(
                filename=val.get("filename", e.key.replace("resume_", "")),
                pages=val.get("pages", 0),
                characters=val.get("characters", 0),
                uploaded_at=e.created_at.isoformat() if e.created_at else None,
            )
        )
    return ResumeList(items=items, total=len(items))


@router.get("/ats-analysis")
async def ats_analysis(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze the most recently uploaded resume for ATS keyword/format/verb gaps."""
    result = await db.execute(
        select(MemoryEntry)
        .where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.key.like("resume_%"),
        )
        .order_by(MemoryEntry.created_at.desc())
        .limit(1)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="No resume found. Upload a resume first.")

    resume_text = (entry.value or {}).get("text", "")
    if not resume_text:
        raise HTTPException(status_code=404, detail="Resume text is empty.")

    text_lower = resume_text.lower()
    total_words = max(len(resume_text.split()), 1)

    profile_result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.skills).selectinload(ProfileSkill.skill))
        .where(Profile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()

    skill_names = []
    if profile and profile.skills:
        for ps in profile.skills:
            skill_names.append(ps.skill.name)

    present_keywords = []
    missing_keywords = []
    for name in skill_names:
        if name.lower() in text_lower:
            present_keywords.append(name)
        else:
            missing_keywords.append(name)

    keyword_score = 0
    if skill_names:
        keyword_score = round((len(present_keywords) / len(skill_names)) * 100)

    found_sections = [s for s in SECTION_HEADERS if s in text_lower]
    format_score = min(100, round(len(found_sections) / 7 * 100))

    verb_count = sum(1 for v in ACTION_VERBS if v in text_lower)
    verb_density = verb_count / 50
    action_verb_score = min(100, round(verb_density * 100))

    suggestions = []
    if len(found_sections) < 4:
        missing_sections = [s for s in ["experience", "education", "skills", "projects"] if s not in found_sections]
        suggestions.append(f"Add missing sections: {', '.join(missing_sections)}")
    if verb_count < 8:
        suggestions.append("Use more action verbs to strengthen your bullet points")
    if total_words < 300:
        suggestions.append("Expand resume content for better ATS parsing")
    if "quantif" not in text_lower and "number" not in text_lower and "%" not in text_lower:
        suggestions.append("Add quantifiable results with numbers and percentages")
    if missing_keywords:
        suggestions.append(f"Add missing skills: {', '.join(missing_keywords[:5])}")
    if keyword_score < 50 and not missing_keywords:
        suggestions.append("Tailor your resume with more relevant keywords")
    if not suggestions:
        suggestions.append("Resume looks well-optimized for ATS scanning")

    summary = (
        f"Your resume scores {keyword_score}/100 on keyword match, "
        f"{format_score}/100 on structure, and {action_verb_score}/100 on action verb usage."
    )
    if keyword_score >= 80 and format_score >= 80 and action_verb_score >= 80:
        summary += " Overall, it is well-optimized for ATS systems."
    elif keyword_score < 50:
        summary += " Consider adding more relevant skills and keywords."

    return {
        "format_score": format_score,
        "keyword_score": keyword_score,
        "action_verb_score": action_verb_score,
        "missing_keywords": missing_keywords,
        "present_keywords": present_keywords,
        "suggestions": suggestions,
        "summary": summary,
    }


@router.get("/search")
async def search_resume(
    q: str = Query(..., min_length=2),
    user: User = Depends(get_current_user),
):
    """Search resume chunks using Qdrant and return top matches."""
    try:
        vector = await get_text_embedding(q)
        agent_memory = AgentMemory(str(user.id))
        results = agent_memory.search_vectors("resume_embeddings", vector, limit=10)
        items = []
        for r in results:
            payload = r.payload if hasattr(r, "payload") else {}
            items.append({
                "text": payload.get("text", "")[:800],
                "filename": payload.get("filename"),
                "chunk_index": payload.get("chunk_index"),
                "pages": payload.get("pages"),
                "characters": payload.get("characters"),
                "score": getattr(r, "score", None),
            })
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filename:path}", status_code=204)
async def delete_resume(
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MemoryEntry).where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.key == f"resume_{filename}",
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Resume not found")
    await db.delete(entry)


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")

    if not text.strip():
        raise HTTPException(
            status_code=400, detail="No text could be extracted from the PDF"
        )

    text = text.strip()
    pages = len(pdf_reader.pages)
    chars = len(text)

    result = await db.execute(
        select(MemoryEntry).where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.key == f"resume_{file.filename}",
        )
    )
    entry = result.scalar_one_or_none()
    if entry:
        entry.value = {
            "text": text,
            "filename": file.filename,
            "pages": pages,
            "characters": chars,
        }
    else:
        entry = MemoryEntry(
            user_id=user.id,
            key=f"resume_{file.filename}",
            value={
                "text": text,
                "filename": file.filename,
                "pages": pages,
                "characters": chars,
            },
        )
        db.add(entry)
    await db.flush()

    # --- Chunk resume text and index chunks in Qdrant (vector store) ---
    try:
        CHUNK_SIZE = 1000
        CHUNK_OVERLAP = 200
        agent_memory = AgentMemory(str(user.id))
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            chunk = text[start:end]
            vector = await get_text_embedding(chunk)
            agent_memory.store_vector(
                collection="resume_embeddings",
                text=chunk,
                vector=vector,
                metadata={
                    "filename": file.filename,
                    "pages": pages,
                    "characters": chars,
                    "chunk_index": idx,
                },
            )
            idx += 1
            start += CHUNK_SIZE - CHUNK_OVERLAP
    except Exception:
        # Do not fail the upload if embedding/indexing fails
        logger.exception("Failed to index resume chunks into Qdrant")

    # --- Enqueue background research tasks using RQ (reliable async processing) ---
    try:
        from rq import Queue
        from redis import Redis
        from app.tasks.agent_tasks import process_research_task

        redis = Redis.from_url(settings.redis_url)
        q = Queue("default", connection=redis)

        # fetch latest profile for URLs
        p = await db.execute(select(Profile).where(Profile.user_id == user.id))
        profile = p.scalar_one_or_none()

        if profile and profile.github_url:
            # create AgentTask record in DB (queued)
            task = AgentTask(user_id=user.id, agent_type=AgentType.research, status=TaskStatus.queued, input={"query": profile.github_url, "focus": "company"})
            db.add(task)
            await db.commit()
            # enqueue background job with task id
            q.enqueue(process_research_task, str(task.id), str(user.id), profile.github_url, "company")

        if profile and profile.portfolio_url:
            task = AgentTask(user_id=user.id, agent_type=AgentType.research, status=TaskStatus.queued, input={"query": profile.portfolio_url, "focus": "company"})
            db.add(task)
            await db.commit()
            q.enqueue(process_research_task, str(task.id), str(user.id), profile.portfolio_url, "company")
    except Exception:
        # best-effort; don't block upload
        logger.exception("Failed to enqueue background research tasks")

    return {
        "filename": file.filename,
        "pages": pages,
        "characters": chars,
        "text": text[:5000],
    }
