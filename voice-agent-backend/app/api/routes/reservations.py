"""Reservations API — back-office view of the table reservations the agent creates,
plus a /quick helper to create one from plain values for testing (mirrors
/appointments/quick). All reads/writes are tenant-scoped.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.models import Reservation, ReservationStatus
from app.services.tenant_service import resolve_tenant_id_for_niche
from app.agents.restaurant_functions import create_reservation

router = APIRouter()

_RESTAURANT_NICHES = {"restaurant"}


class QuickReservation(BaseModel):
    customer_name: str
    phone: str
    party_size: int = 2
    date: str               # YYYY-MM-DD
    time: str               # HH:MM (24h)
    notes: Optional[str] = None
    tenant_id: Optional[str] = None   # defaults to the first restaurant tenant


def _serialize(r: Reservation) -> dict:
    return {"id": r.id, "customer_name": r.customer_name, "phone": r.phone,
            "party_size": r.party_size, "date": r.date, "time": r.time,
            "notes": r.notes, "status": r.status.value, "created_via": r.created_via}


@router.get("/")
async def list_reservations(page: int = 1, page_size: int = 20,
                            status: Optional[str] = None, tenant_id: Optional[str] = None,
                            db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id_for_niche(db, tenant_id, _RESTAURANT_NICHES)
    q = select(Reservation)
    if tid:
        q = q.where(Reservation.tenant_id == tid)
    if status:
        q = q.where(Reservation.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    rows = (await db.execute(
        q.order_by(desc(Reservation.date)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [_serialize(r) for r in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size,
            "tenant_id": tid}


@router.post("/quick")
async def quick_create_reservation(data: QuickReservation, db: AsyncSession = Depends(get_db)):
    """Create a reservation from plain values (test helper). Runs the SAME create_reservation
    function the voice agent uses, so it exercises the real (tenant-scoped) code path."""
    tid = await resolve_tenant_id_for_niche(db, data.tenant_id, _RESTAURANT_NICHES)
    if not tid:
        raise HTTPException(404, "No restaurant tenant found — create one via POST /tenants")
    result = await create_reservation(
        customer_name=data.customer_name, phone=data.phone, party_size=data.party_size,
        date=data.date, time=data.time, notes=data.notes, tenant_id=tid)
    if not result.get("success"):
        raise HTTPException(422, result)
    return {"success": True, "data": result, "tenant_id": tid}
