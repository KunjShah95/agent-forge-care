from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import get_current_user, limiter
from app.models.user import User, MemoryEntry
import PyPDF2
import io

router = APIRouter()


@router.post("/upload")
@limiter.limit("5/minute")
async def upload_resume(
    request: Request,
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

    result = await db.execute(
        select(MemoryEntry).where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.key == f"resume_{file.filename}",
        )
    )
    entry = result.scalar_one_or_none()
    if entry:
        entry.value = {"text": text, "filename": file.filename}
    else:
        entry = MemoryEntry(
            user_id=user.id,
            key=f"resume_{file.filename}",
            value={"text": text, "filename": file.filename},
        )
        db.add(entry)
    await db.flush()

    return {
        "filename": file.filename,
        "pages": len(pdf_reader.pages),
        "characters": len(text),
        "text": text[:5000],
    }
