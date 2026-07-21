"""
Read + light-write dashboard endpoints for the merchant app, scoped by tenant slug (= the
tenant id, e.g. "apx-divinia"). NO AUTH for now (per Phase 2) — the slug is the key.

Built entirely on the existing tables (calls, appointments, patients, services, tenants,
clinics). Booking reuses the SAME book_appointment the phone agent uses, so a dashboard
booking and a voice booking are identical (patient upsert, service match, service_id set).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.db.database import get_db
from app.models.models import (
    Tenant, Call, Appointment, AppointmentStatus, Patient, Service, CallOutcome,
)
from app.agents.clinic_functions import book_appointment, _money, _match_service

router = APIRouter()


async def _tenant_or_404(db: AsyncSession, slug: str) -> Tenant:
    t = await db.get(Tenant, slug)
    if not t:
        raise HTTPException(status_code=404, detail=f"tenant '{slug}' not found")
    return t


def _tz(t: Tenant) -> ZoneInfo:
    try:
        return ZoneInfo(t.timezone or "Asia/Riyadh")
    except Exception:
        return ZoneInfo("Asia/Riyadh")


def _local(dt, tz: ZoneInfo):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _display_dt(dt, tz: ZoneInfo):
    """Human time in the clinic's timezone: '1:12 PM' for today, else 'Jul 20, 1:12 PM'.
    Call timestamps are stored in UTC, so this converts them to local clinic time for display."""
    lc = _local(dt, tz)
    if lc is None:
        return None
    h = lc.hour % 12 or 12
    ap = "AM" if lc.hour < 12 else "PM"
    t = f"{h}:{lc.minute:02d} {ap}"
    if lc.date() == datetime.now(tz).date():
        return t
    return f"{_MONTHS[lc.month - 1]} {lc.day}, {t}"


# ── Summary (Overview counts) ────────────────────────────────────────────────
@router.get("/tenants/{slug}/summary")
async def summary(slug: str, db: AsyncSession = Depends(get_db)):
    t = await _tenant_or_404(db, slug)
    tz = _tz(t)
    now = datetime.now(tz)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    calls = (await db.execute(select(Call).where(Call.tenant_id == slug))).scalars().all()

    def after_hours(lc) -> bool:
        # Clinic open Sat–Thu 1:00 PM–9:00 PM; Friday (weekday 4) closed.
        if lc is None:
            return False
        return lc.weekday() == 4 or lc.hour < 13 or lc.hour >= 21

    calls_month = 0
    after = 0
    for c in calls:
        lc = _local(c.started_at, tz)
        if lc and lc >= month_start:
            calls_month += 1
            if after_hours(lc):
                after += 1

    appts = (await db.execute(select(Appointment).where(Appointment.tenant_id == slug))).scalars().all()
    booked = sum(1 for a in appts
                 if a.status in (AppointmentStatus.booked, AppointmentStatus.confirmed))

    return {
        "tenant": t.business_name,
        "calls_this_month": calls_month,
        "appointments_booked": booked,
        "after_hours_calls": after,
    }


# ── Conversations (real calls + transcripts) ─────────────────────────────────
@router.get("/tenants/{slug}/conversations")
async def conversations(slug: str, limit: int = 40, db: AsyncSession = Depends(get_db)):
    t = await _tenant_or_404(db, slug)
    currency = (t.config or {}).get("currency")
    tz = _tz(t)
    calls = (await db.execute(
        select(Call).where(Call.tenant_id == slug).order_by(Call.started_at.desc()).limit(limit)
    )).scalars().all()

    items = []
    for c in calls:
        booking = None
        if c.caller_number:
            patient = (await db.execute(
                select(Patient).where(Patient.tenant_id == slug, Patient.phone == c.caller_number)
            )).scalars().first()
            if patient:
                appt = (await db.execute(
                    select(Appointment).where(
                        Appointment.tenant_id == slug, Appointment.patient_id == patient.id
                    ).order_by(Appointment.created_at.desc())
                )).scalars().first()
                if appt and appt.service_id:
                    svc = await db.get(Service, appt.service_id)
                    if svc:
                        booking = {"service": svc.name, "price": _money(svc.price, currency)}
        transcript = c.transcript or ""
        ai_summary = (c.ai_analysis or {}).get("summary")
        # Prefer the AI summary; fall back to the first line/slice of the transcript.
        summary = ai_summary or (transcript.split("\n")[0] if transcript else "")
        items.append({
            "id": c.id,
            "caller_number": c.caller_number,
            "time": _display_dt(c.started_at, tz) or "",
            "language": c.language,
            "duration_seconds": c.duration_seconds,
            "summary": summary,
            "transcript": transcript,
            "urgent": bool(c.outcome and c.outcome == CallOutcome.escalated),
            "booking": booking,
        })
    return {"items": items}


# ── Appointments (list / create / delete) ────────────────────────────────────
def _serialize_appt(a: Appointment, patient: Patient | None, svc: Service | None, currency) -> dict:
    status = a.status.value if a.status else "booked"
    # A date/time change surfaces as "rescheduled" — but a cancelled/completed appt keeps that status.
    if status not in ("cancelled", "completed") and (a.reminder_outcome or "").lower() == "rescheduled":
        status = "rescheduled"
    return {
        "id": a.id,
        "name": patient.name if patient else None,
        "phone": patient.phone if patient else None,
        "service": svc.name if svc else None,
        "price": _money(svc.price, currency) if svc else None,
        "date": a.date,
        "time": a.time,
        "status": status,
        "via": a.created_via,
    }


@router.get("/tenants/{slug}/appointments")
async def list_appointments(slug: str, db: AsyncSession = Depends(get_db)):
    t = await _tenant_or_404(db, slug)
    currency = (t.config or {}).get("currency")
    rows = (await db.execute(
        select(Appointment).where(Appointment.tenant_id == slug)
        .order_by(Appointment.date, Appointment.time)
    )).scalars().all()
    items = []
    for a in rows:
        patient = await db.get(Patient, a.patient_id) if a.patient_id else None
        svc = await db.get(Service, a.service_id) if a.service_id else None
        items.append(_serialize_appt(a, patient, svc, currency))
    return {"items": items}


class NewAppointment(BaseModel):
    name: str
    phone: str
    service: str | None = None
    date: str            # YYYY-MM-DD
    time: str            # HH:MM (24h)


@router.post("/tenants/{slug}/appointments")
async def create_appointment(slug: str, body: NewAppointment, db: AsyncSession = Depends(get_db)):
    t = await _tenant_or_404(db, slug)
    # Reuse the phone agent's booking so behaviour is identical (patient upsert, service match).
    res = await book_appointment(
        patient_name=body.name, phone=body.phone, service=body.service,
        date=body.date, time=body.time, tenant_id=slug,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res)
    currency = (t.config or {}).get("currency")
    appt = await db.get(Appointment, res["appointment_id"])
    patient = await db.get(Patient, appt.patient_id) if appt and appt.patient_id else None
    svc = await db.get(Service, appt.service_id) if appt and appt.service_id else None
    return _serialize_appt(appt, patient, svc, currency)


class EditAppointment(BaseModel):
    date: str | None = None       # YYYY-MM-DD
    time: str | None = None       # HH:MM
    service: str | None = None
    status: str | None = None     # booked | confirmed | cancelled | completed | rescheduled


_STATUS_MAP = {
    "booked": AppointmentStatus.booked, "confirmed": AppointmentStatus.confirmed,
    "cancelled": AppointmentStatus.cancelled, "canceled": AppointmentStatus.cancelled,
    "completed": AppointmentStatus.completed,
}


@router.patch("/tenants/{slug}/appointments/{appt_id}")
async def modify_appointment(slug: str, appt_id: str, body: EditAppointment,
                             db: AsyncSession = Depends(get_db)):
    t = await _tenant_or_404(db, slug)
    appt = await db.get(Appointment, appt_id)
    if not appt or appt.tenant_id != slug:
        raise HTTPException(status_code=404, detail="appointment not found")

    moved = False
    if body.date and body.date != appt.date:
        appt.date = body.date
        moved = True
    if body.time and body.time != appt.time:
        appt.time = body.time
        moved = True
    if body.service:
        svc = await _match_service(db, body.service, slug)
        if svc:
            appt.service_id = svc.id
    if body.status:
        st = (body.status or "").lower()
        if st == "rescheduled":
            moved = True
        elif st in _STATUS_MAP:
            appt.status = _STATUS_MAP[st]
    # Surface a date/time change as "rescheduled" in the list (no enum value needed).
    if moved and appt.status not in (AppointmentStatus.cancelled, AppointmentStatus.completed):
        appt.reminder_outcome = "rescheduled"
    await db.commit()

    currency = (t.config or {}).get("currency")
    patient = await db.get(Patient, appt.patient_id) if appt.patient_id else None
    svc = await db.get(Service, appt.service_id) if appt.service_id else None
    return _serialize_appt(appt, patient, svc, currency)


@router.delete("/tenants/{slug}/appointments/{appt_id}")
async def delete_appointment(slug: str, appt_id: str, db: AsyncSession = Depends(get_db)):
    await _tenant_or_404(db, slug)
    appt = await db.get(Appointment, appt_id)
    if not appt or appt.tenant_id != slug:
        raise HTTPException(status_code=404, detail="appointment not found")
    await db.delete(appt)
    await db.commit()
    return {"success": True, "id": appt_id}
