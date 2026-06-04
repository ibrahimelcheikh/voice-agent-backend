"""Appointments API — back-office view of the bookings the voice agent creates."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.models import Appointment, Patient, Doctor, Service, AppointmentStatus

router = APIRouter()


class CreateAppointment(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    service_id: Optional[str] = None
    date: str
    time: str
    reason: Optional[str] = None


async def _serialize(db: AsyncSession, a: Appointment) -> dict:
    doc = await db.get(Doctor, a.doctor_id) if a.doctor_id else None
    pat = await db.get(Patient, a.patient_id) if a.patient_id else None
    svc = await db.get(Service, a.service_id) if a.service_id else None
    return {
        "id": a.id, "date": a.date, "time": a.time, "status": a.status.value,
        "reason": a.reason, "created_via": a.created_via,
        "patient": pat.name if pat else None, "patient_phone": pat.phone if pat else None,
        "doctor": doc.name if doc else None, "specialty": doc.specialty if doc else None,
        "service": svc.name if svc else None,
    }


@router.get("/")
async def list_appointments(page: int = 1, page_size: int = 20,
                            status: Optional[str] = None,
                            db: AsyncSession = Depends(get_db)):
    q = select(Appointment)
    if status:
        q = q.where(Appointment.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    rows = (await db.execute(
        q.order_by(desc(Appointment.date)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    items = [await _serialize(db, a) for a in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.get("/by-phone/{phone}")
async def appointments_by_phone(phone: str, db: AsyncSession = Depends(get_db)):
    patient = (await db.execute(select(Patient).where(Patient.phone == phone))).scalars().first()
    if not patient:
        return {"items": []}
    rows = (await db.execute(
        select(Appointment).where(Appointment.patient_id == patient.id)
        .order_by(desc(Appointment.date))
    )).scalars().all()
    return {"items": [await _serialize(db, a) for a in rows]}


@router.post("/")
async def create_appointment(data: CreateAppointment, db: AsyncSession = Depends(get_db)):
    patient = await db.get(Patient, data.patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    appt = Appointment(clinic_id=patient.clinic_id, created_via="manual",
                        **data.model_dump())
    db.add(appt)
    await db.commit()
    return {"success": True, "data": await _serialize(db, appt)}


@router.post("/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    appt.status = AppointmentStatus.cancelled
    await db.commit()
    return {"success": True, "data": await _serialize(db, appt)}
