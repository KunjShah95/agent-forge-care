import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import Contact, User
from app.schemas.user import ContactCreate, ContactList, ContactOut, ContactUpdate

logger = logging.getLogger("agentforge.contacts")

router = APIRouter()


@router.get("", response_model=ContactList)
async def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all contacts for the current user."""
    try:
        count_result = await db.execute(select(func.count()).select_from(Contact).where(Contact.user_id == user.id))
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
    except Exception as e:
        logger.error("Failed to list contacts for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list contacts: {str(e)}")


@router.post("", response_model=ContactOut, status_code=201)
async def create_contact(
    data: ContactCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new contact."""
    # Input validation
    if not data.name or not isinstance(data.name, str) or len(data.name.strip()) < 2:
        raise HTTPException(status_code=422, detail="Name must be a non-empty string with at least 2 characters")

    try:
        contact = Contact(user_id=user.id, **data.model_dump())
        db.add(contact)
        await db.flush()
        return contact
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create contact for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create contact: {str(e)}")


@router.patch("/{id}", response_model=ContactOut)
async def update_contact(
    id: str,
    data: ContactUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a contact."""
    # Input validation
    if not id or not isinstance(id, str) or len(id.strip()) < 1:
        raise HTTPException(status_code=422, detail="ID must be a non-empty string")

    try:
        result = await db.execute(select(Contact).where(Contact.id == id, Contact.user_id == user.id))
        contact = result.scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(contact, key, value)
        await db.flush()
        return contact
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update contact for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update contact: {str(e)}")


@router.delete("/{id}", status_code=204)
async def delete_contact(
    id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a contact."""
    # Input validation
    if not id or not isinstance(id, str) or len(id.strip()) < 1:
        raise HTTPException(status_code=422, detail="ID must be a non-empty string")

    try:
        result = await db.execute(select(Contact).where(Contact.id == id, Contact.user_id == user.id))
        contact = result.scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        await db.delete(contact)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete contact for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete contact: {str(e)}")
