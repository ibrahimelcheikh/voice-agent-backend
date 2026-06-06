"""Leads API — back-office view of the leads the agent captures (real_estate / automotive /
services tenants), plus a /quick helper to create one from plain values for testing
(mirrors /appointments/quick). All reads/writes are tenant-scoped.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.models import Lead
from app.services.tenant_service import resolve_tenant_id_for_niche
from app.agents.lead_functions import capture_lead

router = APIRouter()

_LEAD_NICHES = {"real_estate", "automotive", "services"}


class QuickLead(BaseModel):
    customer_name: str
    phone: str
    lead_type: Optional[str] = None     # property type / vehicle interest / service needed
    budget: Optional[str] = None
    requirements: Optional[str] = None
    tenant_id: Optional[str] = None     # defaults to the first lead-capture tenant


def _serialize(l: Lead) -> dict:
    return {"id": l.id, "name": l.name, "phone": l.phone, "lead_type": l.lead_type,
            "budget": l.budget, "requirements": l.requirements, "status": l.status.value,
            "created_via": l.created_via}


@router.get("/")
async def list_leads(page: int = 1, page_size: int = 20, status: Optional[str] = None,
                     tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id_for_niche(db, tenant_id, _LEAD_NICHES)
    q = select(Lead)
    if tid:
        q = q.where(Lead.tenant_id == tid)
    if status:
        q = q.where(Lead.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    rows = (await db.execute(
        q.order_by(desc(Lead.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [_serialize(l) for l in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size,
            "tenant_id": tid}


@router.post("/quick")
async def quick_create_lead(data: QuickLead, db: AsyncSession = Depends(get_db)):
    """Create a lead from plain values (test helper). Runs the SAME capture_lead function
    the voice agent uses, so it exercises the real (tenant-scoped) code path."""
    tid = await resolve_tenant_id_for_niche(db, data.tenant_id, _LEAD_NICHES)
    if not tid:
        raise HTTPException(404, "No lead-capture tenant found — create one via POST /tenants")
    result = await capture_lead(
        customer_name=data.customer_name, phone=data.phone, lead_type=data.lead_type,
        budget=data.budget, requirements=data.requirements, tenant_id=tid)
    if not result.get("success"):
        raise HTTPException(422, result)
    return {"success": True, "data": result, "tenant_id": tid}
