"""Patients API — clinic patient directory."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.models import Patient
from app.services.tenant_service import resolve_tenant_id

router = APIRouter()


class CreatePatient(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    insurance_provider: Optional[str] = None
    notes: Optional[str] = None
    tenant_id: Optional[str] = None


def _serialize(p: Patient) -> dict:
    return {"id": p.id, "name": p.name, "phone": p.phone, "email": p.email,
            "date_of_birth": p.date_of_birth, "insurance_provider": p.insurance_provider,
            "notes": p.notes}


@router.get("/")
async def list_patients(page: int = 1, page_size: int = 20,
                        tenant_id: Optional[str] = None,
                        db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id(db, tenant_id)
    base = select(Patient)
    if tid:
        base = base.where(Patient.tenant_id == tid)
    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0
    rows = (await db.execute(
        base.order_by(desc(Patient.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [_serialize(p) for p in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@router.get("/by-phone/{phone}")
async def patient_by_phone(phone: str, tenant_id: Optional[str] = None,
                           db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id(db, tenant_id)
    q = select(Patient).where(Patient.phone == phone)
    if tid:
        q = q.where(Patient.tenant_id == tid)
    p = (await db.execute(q)).scalars().first()
    if not p:
        raise HTTPException(404, "Patient not found")
    return {"data": _serialize(p)}


@router.post("/")
async def create_patient(data: CreatePatient, db: AsyncSession = Depends(get_db)):
    payload = data.model_dump()
    tid = await resolve_tenant_id(db, payload.pop("tenant_id", None))
    p = Patient(tenant_id=tid, **payload)
    db.add(p)
    await db.commit()
    return {"success": True, "data": _serialize(p)}
