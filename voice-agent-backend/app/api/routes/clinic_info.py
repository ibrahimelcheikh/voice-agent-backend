"""Clinic info API — clinic profile, doctors, services, insurance providers.

This is the same data the voice agent reads from; exposing it over REST lets the
dashboard show (and the team verify) exactly what the agent is allowed to say.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.database import get_db
from app.models.models import Clinic, Doctor, Service, InsuranceProvider
from app.services.tenant_service import resolve_tenant_id

router = APIRouter()


@router.get("/")
async def get_clinic(tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id(db, tenant_id)
    q = select(Clinic)
    if tid:
        q = q.where(Clinic.tenant_id == tid)
    c = (await db.execute(q)).scalars().first()
    if not c:
        return {"data": None}
    return {"data": {"id": c.id, "name": c.name, "address": c.address,
                     "phone": c.phone, "hours": c.hours, "timezone": c.timezone}}


@router.get("/doctors")
async def list_doctors(tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id(db, tenant_id)
    q = select(Doctor).where(Doctor.is_active == True)  # noqa: E712
    if tid:
        q = q.where(Doctor.tenant_id == tid)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [{"id": d.id, "name": d.name, "specialty": d.specialty,
                       "available_days": d.available_days, "available_hours": d.available_hours}
                      for d in rows]}


@router.get("/services")
async def list_services(tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id(db, tenant_id)
    q = select(Service).order_by(Service.name)
    if tid:
        q = q.where(Service.tenant_id == tid)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [{"id": s.id, "name": s.name, "duration_minutes": s.duration_minutes,
                       "price_cents": s.price, "price": f"${s.price / 100:.2f}",
                       "description": s.description} for s in rows]}


@router.get("/insurance")
async def list_insurance(tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id(db, tenant_id)
    q = select(InsuranceProvider)
    if tid:
        q = q.where(InsuranceProvider.tenant_id == tid)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [{"id": p.id, "name": p.name, "accepted": p.accepted, "notes": p.notes}
                      for p in rows]}
