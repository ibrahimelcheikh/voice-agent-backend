"""/api/v1/leads — public "Book a demo" capture from the marketing website (no auth),
plus an operator list. Reuses the existing Lead table."""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Lead, LeadStatus
from .deps import Principal, require_operator

router = APIRouter()


class LeadIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None
    source: Optional[str] = "website"


@router.post("")
async def create_lead(data: LeadIn, db: AsyncSession = Depends(get_db)):
    """Public — the website posts demo requests here. No tenant, no auth."""
    lead = Lead(
        tenant_id=None,
        name=data.name,
        phone=data.phone or "",
        email=data.email,
        lead_type="demo",
        requirements=data.message,
        status=LeadStatus.new,
        created_via="web",
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return {"success": True, "id": lead.id}


@router.get("")
async def list_leads(principal: Principal = Depends(require_operator),
                     db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Lead).where(Lead.created_via == "web").order_by(desc(Lead.created_at))
    )).scalars().all()
    return {"items": [{"id": l.id, "name": l.name, "email": l.email, "phone": l.phone,
                       "message": l.requirements, "status": l.status.value,
                       "created_at": str(l.created_at)} for l in rows]}
