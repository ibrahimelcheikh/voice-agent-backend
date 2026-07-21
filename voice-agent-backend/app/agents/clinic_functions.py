"""
Clinic data functions — the ONLY source of truth the voice agent may speak from.

Every function hits the real PostgreSQL database and returns structured data.
The guardrail (app/agents/guardrail.py) calls the matching function for the
caller's intent, then hands ONLY the returned data to the LLM. The LLM is a
natural-language formatter of this data — it must never invent any of it.

Each function returns a plain dict. A truthy/empty result lets the guardrail
decide what the LLM is allowed to say (real data vs. "I'll connect you to staff").

MULTI-TENANT: every function takes a `tenant_id` and scopes EVERY query to it, so a
call for one business can never read or write another business's doctors, services,
patients, appointments, or insurance. The guardrail passes the tenant_id resolved from
the dialed phone number into each call. When tenant_id is None (legacy/edge), queries
are unscoped — but the live agent always supplies one.
"""
from datetime import datetime, date, timedelta

from sqlalchemy import select, desc, func as safunc

from app.db.database import AsyncSessionLocal
from app.core.tenant_scope import scope_query as _scope, require_tenant_id
from app.models.models import (
    Tenant, Clinic, Doctor, Service, Patient, Appointment, InsuranceProvider,
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


def _money(amount, currency: str | None) -> str:
    """Format a service price for the tenant's currency.

    Convention: a tenant that declares a non-USD `currency` in its config stores prices as
    WHOLE units of that currency (e.g. Divinia: 900 -> "900 SAR"). Tenants with no currency
    keep the legacy USD-cents convention ("$9.00"), so existing clinics/restaurants are
    unaffected."""
    cur = (currency or "").strip().upper()
    if cur and cur not in ("USD", "$"):
        try:
            return f"{int(amount):,} {cur}"
        except (TypeError, ValueError):
            return f"0 {cur}"
    return _dollars(amount)


async def _clinic(db, tenant_id=None) -> Clinic | None:
    return (await db.execute(_scope(select(Clinic), Clinic, tenant_id))).scalars().first()


async def _match_doctor(db, doctor: str, tenant_id=None, clinic_id=None):
    """Resolve a spoken doctor reference to a real Doctor row.

    Matches on name OR specialty (callers say "Dr. Haddad" or "the dentist").
    Returns None when nothing matches — the agent must not guess a name.
    Scoped to the tenant so only this business's doctors are ever matched.
    """
    if not doctor:
        return None
    needle = doctor.lower().strip()
    for stop in ("dr.", "dr ", "doctor ", "the "):
        needle = needle.replace(stop, "")
    needle = needle.strip()
    q = _scope(select(Doctor).where(Doctor.is_active == True), Doctor, tenant_id)  # noqa: E712
    if clinic_id:
        q = q.where(Doctor.clinic_id == clinic_id)
    doctors = (await db.execute(q)).scalars().all()
    for d in doctors:
        if needle and (needle in d.name.lower() or needle in d.specialty.lower()):
            return d
    return None


async def _match_service(db, name: str, tenant_id=None):
    """Resolve a spoken service/treatment to a real Service row (name match, case-insensitive,
    exact then substring either direction). Returns None when nothing matches or no name given —
    booking still succeeds without a linked service, and the agent never invents one."""
    if not name:
        return None
    needle = name.strip().lower()
    services = (await db.execute(_scope(select(Service), Service, tenant_id))).scalars().all()
    for s in services:
        if s.name.lower() == needle:
            return s
    for s in services:
        n = s.name.lower()
        if needle in n or n in needle:
            return s
    return None


# ── 1. Book ──────────────────────────────────────────────────────────────────

async def book_appointment(patient_name=None, phone=None, doctor=None, service=None, date=None,
                           time=None, reason=None, tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "book_appointment")
    async with AsyncSessionLocal() as db:
        clinic = await _clinic(db, tenant_id)
        if not phone or not patient_name or not date or not time:
            return {"success": False, "missing": [
                k for k, v in {"patient_name": patient_name, "phone": phone,
                               "date": date, "time": time}.items() if not v]}

        doc = await _match_doctor(db, doctor, tenant_id, clinic.id if clinic else None)
        if doctor and not doc:
            return {"success": False, "reason": "doctor_not_found", "requested_doctor": doctor}

        # Link the booked treatment when the caller named one (so the dashboard shows
        # service + price). Unmatched/blank service just leaves service_id NULL — never fails.
        svc = await _match_service(db, service, tenant_id)

        # Find or create the patient by phone — scoped to the tenant so the same number
        # at two different businesses stays two distinct patients.
        patient = (await db.execute(
            _scope(select(Patient).where(Patient.phone == phone), Patient, tenant_id)
        )).scalars().first()
        if not patient:
            patient = Patient(tenant_id=tenant_id, clinic_id=clinic.id if clinic else None,
                              name=patient_name, phone=phone)
            db.add(patient)
            await db.flush()

        appt = Appointment(
            tenant_id=tenant_id,
            clinic_id=clinic.id if clinic else None,
            patient_id=patient.id,
            doctor_id=doc.id if doc else None,
            service_id=svc.id if svc else None,
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
            "service": svc.name if svc else None,
            "date": date,
            "time": time,
            "reason": reason,
        }


# ── 2. Cancel ────────────────────────────────────────────────────────────────

async def cancel_appointment(phone=None, appointment_id=None, tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "cancel_appointment")
    async with AsyncSessionLocal() as db:
        q = _scope(select(Appointment).where(
            Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.completed])
        ), Appointment, tenant_id)
        if appointment_id:
            q = q.where(Appointment.id == appointment_id)
        elif phone:
            patient = (await db.execute(
                _scope(select(Patient).where(Patient.phone == phone), Patient, tenant_id)
            )).scalars().first()
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
                                 appointment_id=None, tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "reschedule_appointment")
    async with AsyncSessionLocal() as db:
        if not new_date or not new_time:
            return {"success": False, "reason": "need_new_date_time"}
        q = _scope(select(Appointment).where(
            Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.completed])
        ), Appointment, tenant_id)
        if appointment_id:
            q = q.where(Appointment.id == appointment_id)
        elif phone:
            patient = (await db.execute(
                _scope(select(Patient).where(Patient.phone == phone), Patient, tenant_id)
            )).scalars().first()
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


# ── 3b. Confirm ──────────────────────────────────────────────────────────────

async def confirm_appointment(phone=None, appointment_id=None, tenant_id=None) -> dict:
    """Mark an appointment confirmed. Used by the outbound reminder agent when the
    patient says they'll keep the appointment. Targets a specific appointment_id when
    known (reminder calls always pass it), else the patient's soonest open appointment."""
    require_tenant_id(tenant_id, "confirm_appointment")
    async with AsyncSessionLocal() as db:
        q = _scope(select(Appointment).where(
            Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.completed])
        ), Appointment, tenant_id)
        if appointment_id:
            q = q.where(Appointment.id == appointment_id)
        elif phone:
            patient = (await db.execute(
                _scope(select(Patient).where(Patient.phone == phone), Patient, tenant_id)
            )).scalars().first()
            if not patient:
                return {"success": False, "reason": "not_found"}
            q = q.where(Appointment.patient_id == patient.id).order_by(Appointment.date)
        else:
            return {"success": False, "reason": "need_phone_or_id"}

        appt = (await db.execute(q)).scalars().first()
        if not appt:
            return {"success": False, "reason": "not_found"}
        appt.status = AppointmentStatus.confirmed
        await db.commit()
        doc = await db.get(Doctor, appt.doctor_id) if appt.doctor_id else None
        return {"success": True, "appointment_id": appt.id, "date": appt.date,
                "time": appt.time, "doctor": doc.name if doc else None}


# ── 4. Check ─────────────────────────────────────────────────────────────────

async def check_appointment(phone=None, tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "check_appointment")
    async with AsyncSessionLocal() as db:
        if not phone:
            return {"success": False, "reason": "need_phone"}
        patient = (await db.execute(
            _scope(select(Patient).where(Patient.phone == phone), Patient, tenant_id)
        )).scalars().first()
        if not patient:
            return {"success": False, "reason": "not_found"}
        today = date.today().isoformat()
        appts = (await db.execute(
            _scope(select(Appointment), Appointment, tenant_id)
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

async def get_clinic_hours(tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "get_clinic_hours")
    async with AsyncSessionLocal() as db:
        clinic = await _clinic(db, tenant_id)
        if not clinic:
            return {"success": False}
        return {"success": True, "clinic": clinic.name, "hours": clinic.hours or {},
                "timezone": clinic.timezone}


# ── 6. Clinic location ───────────────────────────────────────────────────────

async def get_clinic_location(tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "get_clinic_location")
    async with AsyncSessionLocal() as db:
        clinic = await _clinic(db, tenant_id)
        if not clinic:
            return {"success": False}
        return {"success": True, "clinic": clinic.name, "address": clinic.address,
                "phone": clinic.phone}


# ── 7. Services ──────────────────────────────────────────────────────────────

async def get_services(tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "get_services")
    async with AsyncSessionLocal() as db:
        clinic = await _clinic(db, tenant_id)
        tenant = await db.get(Tenant, tenant_id)
        currency = (tenant.config or {}).get("currency") if tenant else None
        services = (await db.execute(
            _scope(select(Service), Service, tenant_id).order_by(Service.name)
        )).scalars().all()
        return {"success": True, "clinic": clinic.name if clinic else None,
                "services": [
                    {"name": s.name, "duration_minutes": s.duration_minutes,
                     "price": _money(s.price, currency), "description": s.description}
                    for s in services]}


# ── 8. Doctor availability ───────────────────────────────────────────────────

async def check_doctor_availability(doctor=None, date=None, tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "check_doctor_availability")
    async with AsyncSessionLocal() as db:
        doc = await _match_doctor(db, doctor or "", tenant_id)
        if not doc:
            # Offer the roster so the agent can read real names, never invent them.
            roster = (await db.execute(
                _scope(select(Doctor).where(Doctor.is_active == True), Doctor, tenant_id)  # noqa: E712
            )).scalars().all()
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

async def check_insurance(insurance_provider=None, tenant_id=None) -> dict:
    require_tenant_id(tenant_id, "check_insurance")
    async with AsyncSessionLocal() as db:
        if not insurance_provider:
            providers = (await db.execute(
                _scope(select(InsuranceProvider).where(InsuranceProvider.accepted == True),  # noqa: E712
                       InsuranceProvider, tenant_id)
            )).scalars().all()
            return {"success": True, "listing": True,
                    "accepted_providers": [p.name for p in providers]}
        needle = insurance_provider.lower().strip()
        providers = (await db.execute(
            _scope(select(InsuranceProvider), InsuranceProvider, tenant_id)
        )).scalars().all()
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
    "confirm_appointment": confirm_appointment,
    "check_appointment": check_appointment,
    "clinic_hours": get_clinic_hours,
    "clinic_location": get_clinic_location,
    "services_offered": get_services,
    "doctor_availability": check_doctor_availability,
    "insurance_question": check_insurance,
}
