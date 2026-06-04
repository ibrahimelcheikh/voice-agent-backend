"""Patients API — clinic patient directory."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.models import Patient

router = APIRouter()


class CreatePatient(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    insurance_provider: Optional[str] = None
    notes: Optional[str] = None


def _serialize(p: Patient) -> dict:
    return {"id": p.id, "name": p.name, "phone": p.phone, "email": p.email,
            "date_of_birth": p.date_of_birth, "insurance_provider": p.insurance_provider,
            "notes": p.notes}


@router.get("/")
async def list_patients(page: int = 1, page_size: int = 20,
                        db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Patient))).scalar() or 0
    rows = (await db.execute(
        select(Patient).order_by(desc(Patient.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [_serialize(p) for p in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@router.get("/by-phone/{phone}")
async def patient_by_phone(phone: str, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Patient).where(Patient.phone == phone))).scalars().first()
    if not p:
        raise HTTPException(404, "Patient not found")
    return {"data": _serialize(p)}


@router.post("/")
async def create_patient(data: CreatePatient, db: AsyncSession = Depends(get_db)):
    p = Patient(**data.model_dump())
    db.add(p)
    await db.commit()
    return {"success": True, "data": _serialize(p)}
