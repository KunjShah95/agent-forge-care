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
from fastapi import Query

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
        logger = __import__("logging").getLogger("agentforge.resume")
        logger.exception("Failed to index resume chunks into Qdrant")

    # --- Enqueue background research tasks using RQ (reliable async processing) ---
    try:
        from rq import Queue
        from redis import Redis
        from app.tasks.agent_tasks import process_research_task

        redis = Redis.from_url(__import__("app").config.settings.redis_url)
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
        logger = __import__("logging").getLogger("agentforge.resume")
        logger.exception("Failed to enqueue background research tasks")

    return {
        "filename": file.filename,
        "pages": pages,
        "characters": chars,
        "text": text[:5000],
    }
