from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, Contact
from app.schemas.user import ContactCreate, ContactUpdate, ContactOut, ContactList

router = APIRouter()


@router.get("", response_model=ContactList)
async def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all contacts for the current user."""
    count_result = await db.execute(
        select(func.count()).select_from(Contact).where(Contact.user_id == user.id)
    )
    total = count_result.scalar()

    offset = (page - 1) * limit
    result = await db.execute(
        select(Contact)
        .where(Contact.user_id == user.id)
        .order_by(desc(Contact.created_at))
        .offset(offset)
        .limit(limit)
    )
    contacts = result.scalars().all()
    return ContactList(
        items=[ContactOut.model_validate(c) for c in contacts],
        total=total,
        page=page,
    )


@router.post("", response_model=ContactOut, status_code=201)
async def create_contact(
    data: ContactCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new contact."""
    contact = Contact(user_id=user.id, **data.model_dump())
    db.add(contact)
    await db.flush()
    return contact


@router.patch("/{id}", response_model=ContactOut)
async def update_contact(
    id: str,
    data: ContactUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a contact."""
    result = await db.execute(
        select(Contact).where(Contact.id == id, Contact.user_id == user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    await db.flush()
    return contact


@router.delete("/{id}", status_code=204)
async def delete_contact(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a contact."""
    result = await db.execute(
        select(Contact).where(Contact.id == id, Contact.user_id == user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(contact)
