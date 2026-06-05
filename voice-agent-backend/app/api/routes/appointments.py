"""Appointments API — back-office view of the bookings the voice agent creates."""
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.models import Appointment, Patient, Doctor, Service, Clinic, AppointmentStatus

router = APIRouter()


class CreateAppointment(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    service_id: Optional[str] = None
    date: str
    time: str
    reason: Optional[str] = None


class QuickAppointment(BaseModel):
    """Plain-values appointment for testing outbound reminders — no pre-existing IDs."""
    patient_name: str
    phone: str
    doctor_name: str
    date: str               # YYYY-MM-DD
    time: str               # HH:MM (24h)
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


@router.post("/quick")
async def quick_create_appointment(data: QuickAppointment, db: AsyncSession = Depends(get_db)):
    """Create an appointment from plain values (no pre-existing IDs) — a forgiving helper
    for testing outbound reminders.

    - Patient: looked up by phone; created with name+phone if not found.
    - Doctor: fuzzy (ILIKE) match on the existing doctors by name (the 'Dr.' prefix is
      optional). A clear error is returned if no doctor matches.
    - Service: any service matching the doctor's specialty, else the first service.
    """
    clinic = (await db.execute(select(Clinic))).scalars().first()
    clinic_id = clinic.id if clinic else None

    # Patient — find by phone, create on miss.
    patient = (await db.execute(
        select(Patient).where(Patient.phone == data.phone)
    )).scalars().first()
    if not patient:
        patient = Patient(clinic_id=clinic_id, name=data.patient_name, phone=data.phone)
        db.add(patient)
        await db.flush()

    # Doctor — fuzzy match by name (drop a leading 'Dr.'/'Doctor' so 'Karim Nassar' hits
    # 'Dr. Karim Nassar'). Match name OR specialty so 'dentist' also works.
    needle = data.doctor_name.strip()
    for stop in ("Dr.", "Dr ", "Doctor ", "dr.", "dr ", "doctor "):
        if needle.lower().startswith(stop.lower()):
            needle = needle[len(stop):].strip()
            break
    doctor = (await db.execute(
        select(Doctor).where(
            Doctor.is_active == True,  # noqa: E712
            or_(Doctor.name.ilike(f"%{needle}%"), Doctor.specialty.ilike(f"%{needle}%")),
        )
    )).scalars().first()
    if not doctor:
        roster = (await db.execute(
            select(Doctor).where(Doctor.is_active == True)  # noqa: E712
        )).scalars().all()
        raise HTTPException(422, {
            "error": "doctor_not_found",
            "message": f"No doctor matches '{data.doctor_name}'.",
            "available_doctors": [{"name": d.name, "specialty": d.specialty} for d in roster],
        })

    # Service — prefer one whose name relates to the doctor's specialty (stem match, so
    # 'Dentist' hits 'Dental Cleaning'), else the first available service. Best-effort; the
    # reminder flow doesn't require a service.
    services = (await db.execute(select(Service).order_by(Service.name))).scalars().all()

    def _stems(text: str) -> set[str]:
        # 4-char stems so 'dentist'/'dental' and 'cardiologist'/'cardiac' relate.
        return {w[:4] for w in re.split(r"\W+", (text or "").lower()) if len(w) > 3}

    specialty_stems = _stems(doctor.specialty)
    service = None
    for s in services:
        if specialty_stems & _stems(s.name):
            service = s
            break
    service = service or (services[0] if services else None)

    appt = Appointment(
        clinic_id=clinic_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        service_id=service.id if service else None,
        date=data.date,
        time=data.time,
        status=AppointmentStatus.booked,
        reason=data.reason,
        created_via="test",
    )
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
