from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, MemoryEntry
from app.schemas.user import ResumeOut, ResumeList
import PyPDF2
import io

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

    return {
        "filename": file.filename,
        "pages": pages,
        "characters": chars,
        "text": text[:5000],
    }
