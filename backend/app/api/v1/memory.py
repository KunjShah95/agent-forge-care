from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, MemoryEntry
from app.schemas.user import MemoryCreate, MemoryUpdate, MemoryOut, MemoryList

router = APIRouter()


@router.get("", response_model=MemoryList)
async def list_memory(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all memory entries for the current user."""
    count_result = await db.execute(
        select(func.count())
        .select_from(MemoryEntry)
        .where(MemoryEntry.user_id == user.id)
    )
    total = count_result.scalar()

    offset = (page - 1) * limit
    result = await db.execute(
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user.id)
        .order_by(desc(MemoryEntry.updated_at))
        .offset(offset)
        .limit(limit)
    )
    entries = result.scalars().all()
    return MemoryList(
        items=[MemoryOut.model_validate(e) for e in entries],
        total=total,
        page=page,
    )


@router.post("", response_model=MemoryOut, status_code=201)
async def create_memory(
    data: MemoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new memory entry."""
    entry = MemoryEntry(
        user_id=user.id,
        key=data.key,
        value=data.value,
        weight=data.weight,
    )
    db.add(entry)
    await db.flush()
    return entry


@router.patch("/{id}", response_model=MemoryOut)
async def update_memory(
    id: str,
    data: MemoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a memory entry."""
    result = await db.execute(
        select(MemoryEntry).where(MemoryEntry.id == id, MemoryEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Memory entry not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)
    await db.flush()
    return entry


@router.delete("/{id}", status_code=204)
async def delete_memory(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a memory entry."""
    result = await db.execute(
        select(MemoryEntry).where(MemoryEntry.id == id, MemoryEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    await db.delete(entry)


@router.get("/context")
async def get_memory_context(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get condensed memory context for agent system use."""
    result = await db.execute(select(MemoryEntry).where(MemoryEntry.user_id == user.id))
    entries = result.scalars().all()

    context = {}
    for entry in entries:
        context[entry.key] = entry.value
    return context
