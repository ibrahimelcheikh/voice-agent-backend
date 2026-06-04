"""
Clinic data functions — the ONLY source of truth the voice agent may speak from.

Every function hits the real PostgreSQL database and returns structured data.
The guardrail (app/agents/guardrail.py) calls the matching function for the
caller's intent, then hands ONLY the returned data to the LLM. The LLM is a
natural-language formatter of this data — it must never invent any of it.

Each function returns a plain dict. A truthy/empty result lets the guardrail
decide what the LLM is allowed to say (real data vs. "I'll connect you to staff").
"""
from datetime import datetime, date, timedelta

from sqlalchemy import select, desc, func as safunc

from app.db.database import AsyncSessionLocal
from app.models.models import (
    Clinic, Doctor, Service, Patient, Appointment, InsuranceProvider,
    AppointmentStatus,
)

_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _weekday_key(date_str: str) -> str | None:
    """mon..sun for an ISO date string, or None if unparseable."""
    try:
        return _WEEKDAYS[datetime.strptime(date_str, "%Y-%m-%d").weekday()]
    except (ValueError, TypeError):
        return None


def _dollars(cents) -> str:
    try:
        return f"${int(cents) / 100:.2f}"
    except (TypeError, ValueError):
        return "$0.00"


async def _clinic(db) -> Clinic | None:
    return (await db.execute(select(Clinic))).scalars().first()


async def _match_doctor(db, doctor: str, clinic_id=None):
    """Resolve a spoken doctor reference to a real Doctor row.

    Matches on name OR specialty (callers say "Dr. Haddad" or "the dentist").
    Returns None when nothing matches — the agent must not guess a name.
    """
    if not doctor:
        return None
    needle = doctor.lower().strip()
    for stop in ("dr.", "dr ", "doctor ", "the "):
        needle = needle.replace(stop, "")
    needle = needle.strip()
    q = select(Doctor).where(Doctor.is_active == True)  # noqa: E712
    if clinic_id:
        q = q.where(Doctor.clinic_id == clinic_id)
    doctors = (await db.execute(q)).scalars().all()
    for d in doctors:
        if needle and (needle in d.name.lower() or needle in d.specialty.lower()):
            return d
    return None


# ── 1. Book ──────────────────────────────────────────────────────────────────

async def book_appointment(patient_name=None, phone=None, doctor=None, date=None,
                           time=None, reason=None) -> dict:
    async with AsyncSessionLocal() as db:
        clinic = await _clinic(db)
        if not phone or not patient_name or not date or not time:
            return {"success": False, "missing": [
                k for k, v in {"patient_name": patient_name, "phone": phone,
                               "date": date, "time": time}.items() if not v]}

        doc = await _match_doctor(db, doctor, clinic.id if clinic else None)
        if doctor and not doc:
            return {"success": False, "reason": "doctor_not_found", "requested_doctor": doctor}

        # Find or create the patient by phone.
        patient = (await db.execute(
            select(Patient).where(Patient.phone == phone)
        )).scalars().first()
        if not patient:
            patient = Patient(clinic_id=clinic.id if clinic else None,
                              name=patient_name, phone=phone)
            db.add(patient)
            await db.flush()

        appt = Appointment(
            clinic_id=clinic.id if clinic else None,
            patient_id=patient.id,
            doctor_id=doc.id if doc else None,
            date=date, time=time,
            status=AppointmentStatus.booked,
            reason=reason,
            created_via="voice",
        )
        db.add(appt)
        await db.commit()
        return {
            "success": True,
            "appointment_id": appt.id,
            "patient_name": patient.name,
            "doctor": doc.name if doc else None,
            "specialty": doc.specialty if doc else None,
            "date": date,
            "time": time,
            "reason": reason,
        }


# ── 2. Cancel ────────────────────────────────────────────────────────────────

async def cancel_appointment(phone=None, appointment_id=None) -> dict:
    async with AsyncSessionLocal() as db:
        q = select(Appointment).where(
            Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.completed])
        )
        if appointment_id:
            q = q.where(Appointment.id == appointment_id)
        elif phone:
            patient = (await db.execute(select(Patient).where(Patient.phone == phone))).scalars().first()
            if not patient:
                return {"success": False, "reason": "not_found"}
            q = q.where(Appointment.patient_id == patient.id).order_by(Appointment.date)
        else:
            return {"success": False, "reason": "need_phone_or_id"}

        appt = (await db.execute(q)).scalars().first()
        if not appt:
            return {"success": False, "reason": "not_found"}
        appt.status = AppointmentStatus.cancelled
        await db.commit()
        doc = await db.get(Doctor, appt.doctor_id) if appt.doctor_id else None
        return {"success": True, "appointment_id": appt.id, "date": appt.date,
                "time": appt.time, "doctor": doc.name if doc else None}


# ── 3. Reschedule ────────────────────────────────────────────────────────────

async def reschedule_appointment(phone=None, new_date=None, new_time=None,
                                 appointment_id=None) -> dict:
    async with AsyncSessionLocal() as db:
        if not new_date or not new_time:
            return {"success": False, "reason": "need_new_date_time"}
        q = select(Appointment).where(
            Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.completed])
        )
        if appointment_id:
            q = q.where(Appointment.id == appointment_id)
        elif phone:
            patient = (await db.execute(select(Patient).where(Patient.phone == phone))).scalars().first()
            if not patient:
                return {"success": False, "reason": "not_found"}
            q = q.where(Appointment.patient_id == patient.id).order_by(Appointment.date)
        else:
            return {"success": False, "reason": "need_phone_or_id"}

        appt = (await db.execute(q)).scalars().first()
        if not appt:
            return {"success": False, "reason": "not_found"}
        old_date, old_time = appt.date, appt.time
        appt.date, appt.time = new_date, new_time
        appt.status = AppointmentStatus.booked
        await db.commit()
        doc = await db.get(Doctor, appt.doctor_id) if appt.doctor_id else None
        return {"success": True, "appointment_id": appt.id,
                "old_date": old_date, "old_time": old_time,
                "new_date": new_date, "new_time": new_time,
                "doctor": doc.name if doc else None}


# ── 4. Check ─────────────────────────────────────────────────────────────────

async def check_appointment(phone=None) -> dict:
    async with AsyncSessionLocal() as db:
        if not phone:
            return {"success": False, "reason": "need_phone"}
        patient = (await db.execute(select(Patient).where(Patient.phone == phone))).scalars().first()
        if not patient:
            return {"success": False, "reason": "not_found"}
        today = date.today().isoformat()
        appts = (await db.execute(
            select(Appointment)
            .where(Appointment.patient_id == patient.id,
                   Appointment.date >= today,
                   Appointment.status.notin_([AppointmentStatus.cancelled]))
            .order_by(Appointment.date, Appointment.time)
        )).scalars().all()
        if not appts:
            return {"success": True, "found": False, "appointments": []}
        out = []
        for a in appts:
            doc = await db.get(Doctor, a.doctor_id) if a.doctor_id else None
            out.append({"appointment_id": a.id, "date": a.date, "time": a.time,
                        "status": a.status.value,
                        "doctor": doc.name if doc else None,
                        "specialty": doc.specialty if doc else None,
                        "reason": a.reason})
        return {"success": True, "found": True, "patient_name": patient.name,
                "appointments": out}


# ── 5. Clinic hours ──────────────────────────────────────────────────────────

async def get_clinic_hours() -> dict:
    async with AsyncSessionLocal() as db:
        clinic = await _clinic(db)
        if not clinic:
            return {"success": False}
        return {"success": True, "clinic": clinic.name, "hours": clinic.hours or {},
                "timezone": clinic.timezone}


# ── 6. Clinic location ───────────────────────────────────────────────────────

async def get_clinic_location() -> dict:
    async with AsyncSessionLocal() as db:
        clinic = await _clinic(db)
        if not clinic:
            return {"success": False}
        return {"success": True, "clinic": clinic.name, "address": clinic.address,
                "phone": clinic.phone}


# ── 7. Services ──────────────────────────────────────────────────────────────

async def get_services() -> dict:
    async with AsyncSessionLocal() as db:
        clinic = await _clinic(db)
        services = (await db.execute(select(Service).order_by(Service.name))).scalars().all()
        return {"success": True, "clinic": clinic.name if clinic else None,
                "services": [
                    {"name": s.name, "duration_minutes": s.duration_minutes,
                     "price": _dollars(s.price), "description": s.description}
                    for s in services]}


# ── 8. Doctor availability ───────────────────────────────────────────────────

async def check_doctor_availability(doctor=None, date=None) -> dict:
    async with AsyncSessionLocal() as db:
        doc = await _match_doctor(db, doctor or "")
        if not doc:
            # Offer the roster so the agent can read real names, never invent them.
            roster = (await db.execute(select(Doctor).where(Doctor.is_active == True))).scalars().all()  # noqa: E712
            return {"success": False, "reason": "doctor_not_found",
                    "available_doctors": [{"name": d.name, "specialty": d.specialty} for d in roster]}
        result = {"success": True, "doctor": doc.name, "specialty": doc.specialty,
                  "available_days": doc.available_days or [],
                  "available_hours": doc.available_hours or {}}
        if date:
            wk = _weekday_key(date)
            result["date"] = date
            result["available_on_date"] = bool(wk and wk in (doc.available_days or []))
        return result


# ── 9. Insurance ─────────────────────────────────────────────────────────────

async def check_insurance(insurance_provider=None) -> dict:
    async with AsyncSessionLocal() as db:
        if not insurance_provider:
            providers = (await db.execute(
                select(InsuranceProvider).where(InsuranceProvider.accepted == True)  # noqa: E712
            )).scalars().all()
            return {"success": True, "listing": True,
                    "accepted_providers": [p.name for p in providers]}
        needle = insurance_provider.lower().strip()
        providers = (await db.execute(select(InsuranceProvider))).scalars().all()
        for p in providers:
            if needle in p.name.lower() or p.name.lower() in needle:
                return {"success": True, "provider": p.name, "accepted": p.accepted,
                        "notes": p.notes}
        return {"success": True, "provider": insurance_provider, "accepted": None,
                "reason": "not_in_list"}


# Registry used by the guardrail (intent -> coroutine) and the demo simulator.
CLINIC_FUNCTIONS = {
    "book_appointment": book_appointment,
    "cancel_appointment": cancel_appointment,
    "reschedule_appointment": reschedule_appointment,
    "check_appointment": check_appointment,
    "clinic_hours": get_clinic_hours,
    "clinic_location": get_clinic_location,
    "services_offered": get_services,
    "doctor_availability": check_doctor_availability,
    "insurance_question": check_insurance,
}
