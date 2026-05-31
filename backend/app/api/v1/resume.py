from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, MemoryEntry
from app.schemas.user import ResumeOut, ResumeList
import PyPDF2
import io
from app.utils.embedding import get_text_embedding
from app.memory.memory_layer import AgentMemory
from app.models.user import AgentTask, AgentType, TaskStatus, Profile
from app.agents.research_agent import conduct_research
from app.services.notification_service import create_notification

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
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
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

    # --- Index resume text in Qdrant (vector store) ---
    try:
        vector = await get_text_embedding(text)
        agent_memory = AgentMemory(str(user.id))
        agent_memory.store_vector(
            collection="resume_embeddings",
            text=text,
            vector=vector,
            metadata={"filename": file.filename, "pages": pages, "characters": chars},
        )
    except Exception:
        # Do not fail the upload if embedding/indexing fails
        logger = __import__("logging").getLogger("agentforge.resume")
        logger.exception("Failed to index resume into Qdrant")

    # --- Optionally kick off background analysis tasks for GitHub / portfolio ---
    try:
        # fetch latest profile for URLs
        p = await db.execute(select(Profile).where(Profile.user_id == user.id))
        profile = p.scalar_one_or_none()
        # GitHub analysis
        if profile and profile.github_url:
            task = AgentTask(user_id=user.id, agent_type=AgentType.research, status=TaskStatus.running, input={"query": profile.github_url, "focus": "company"})
            db.add(task)
            await db.commit()
            try:
                res = await conduct_research(str(user.id), {"query": profile.github_url, "focus": "company"}, db)
                task.status = TaskStatus.completed
                task.output = res
                await db.commit()
                await create_notification(db, user.id, title="GitHub analysis complete", body=f"GitHub analysis for {profile.github_url} finished", type="success")
            except Exception as e:
                task.status = TaskStatus.failed
                task.error = str(e)
                await db.commit()
                await create_notification(db, user.id, title="GitHub analysis failed", body=str(e)[:200], type="error")

        # Portfolio analysis
        if profile and profile.portfolio_url:
            task = AgentTask(user_id=user.id, agent_type=AgentType.research, status=TaskStatus.running, input={"query": profile.portfolio_url, "focus": "company"})
            db.add(task)
            await db.commit()
            try:
                res = await conduct_research(str(user.id), {"query": profile.portfolio_url, "focus": "company"}, db)
                task.status = TaskStatus.completed
                task.output = res
                await db.commit()
                await create_notification(db, user.id, title="Portfolio analysis complete", body=f"Portfolio analysis for {profile.portfolio_url} finished", type="success")
            except Exception as e:
                task.status = TaskStatus.failed
                task.error = str(e)
                await db.commit()
                await create_notification(db, user.id, title="Portfolio analysis failed", body=str(e)[:200], type="error")
    except Exception:
        # best-effort; don't block upload
        pass

    return {
        "filename": file.filename,
        "pages": pages,
        "characters": chars,
        "text": text[:5000],
    }
