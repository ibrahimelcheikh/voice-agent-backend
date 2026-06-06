"""
Outbound appointment-reminder calls.

The clinic agent normally answers INBOUND calls (Twilio SIP → LiveKit room → agent).
This module lets the clinic *initiate* a call: it dials the patient with Twilio, bridges
the answered call into a LiveKit SIP room (reusing the EXISTING inbound trunk via the
`/twilio/outbound` TwiML), and the same agent worker joins that room — but greets the
patient with a reminder script instead of the inbound greeting and knows which
appointment it's calling about.

Pieces:
  * place_reminder_call(appointment_id)      — dial one patient now (manual API + sweep)
  * find_due_appointments()                  — appointments ~REMINDER_HOURS_BEFORE out, unreminded
  * run_reminder_sweep()                     — APScheduler job: place calls for all due
  * resolve_outbound_context_for_room(room)  — agent side: which appointment is this call?
  * record_reminder_result_by_sid(...)       — Twilio side: mark no-answer / voicemail / failed

Multi-tenant: each reminder is scoped to its appointment's tenant. The Call + agent are
attributed to that tenant, and the reminder context carries tenant_id so the agent only
ever touches that business's data when the patient confirms/reschedules/cancels.
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import select, or_

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.models import (
    Appointment, AppointmentStatus, Patient, Doctor, Agent, AgentType,
    Call, CallDirection, CallOutcome, ReminderOutcome,
)

logger = logging.getLogger("reminders")

# Safety cap so a first sweep over a fresh demo DB can't fan out into hundreds of real
# Twilio calls at once. Anything beyond this is left for the next sweep (and logged, so
# the truncation is never silent).
_MAX_CALLS_PER_SWEEP = 25

# Window (minutes) around a placed call within which the joining agent will associate a
# LiveKit room with a pending outbound reminder. Generous enough to cover ring time.
_RESOLVE_WINDOW_MIN = 5

_TERMINAL_HUMAN = {ReminderOutcome.confirmed.value, ReminderOutcome.rescheduled.value,
                   ReminderOutcome.cancelled.value, ReminderOutcome.answered.value}


# ── date/phone helpers ────────────────────────────────────────────────────────

def _appt_datetime(appt: Appointment) -> datetime | None:
    """Combine an appointment's 'YYYY-MM-DD' date + 'HH:MM' time into a naive datetime.
    Naive/local is consistent with how the rest of the app compares dates (single clinic,
    single timezone)."""
    try:
        return datetime.strptime(f"{appt.date} {appt.time}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        try:
            return datetime.strptime(appt.date, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None


def human_date(date_str: str) -> str:
    """'2026-06-09' -> 'Monday, June 09'. Falls back to the raw string."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %B %d")
    except (ValueError, TypeError):
        return date_str or ""


def human_time(time_str: str) -> str:
    """'15:30' -> '3:30 PM'. Falls back to the raw string."""
    try:
        return datetime.strptime(time_str, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except (ValueError, TypeError):
        return time_str or ""


def _digits(phone: str | None) -> str:
    return re.sub(r"\D", "", phone or "")


def _phones_match(a: str | None, b: str | None) -> bool:
    """Loose phone equality: compare the last 7+ digits so +1-415-555-0142 matches
    4155550142 regardless of country-code / formatting differences."""
    da, db = _digits(a), _digits(b)
    if not da or not db:
        return False
    n = min(len(da), len(db), 10)
    return da[-n:] == db[-n:] and n >= 7


# ── context payload shared with the agent ─────────────────────────────────────

def _build_context(appt: Appointment, patient: Patient, doctor: Doctor | None,
                   call: Call | None) -> dict:
    """The reminder context the agent needs: who to greet, which appointment, and the
    real doctor/date/time it may state (the LLM never invents these)."""
    return {
        "purpose": "reminder",
        "direction": "outbound",
        "call_id": call.id if call else None,
        # Tenant the appointment belongs to — scopes the agent's data on the reminder call.
        "tenant_id": appt.tenant_id,
        "appointment_id": appt.id,
        "patient_name": patient.name if patient else None,
        "phone": patient.phone if patient else None,
        "doctor_name": doctor.name if doctor else None,
        "specialty": doctor.specialty if doctor else None,
        "date": appt.date,
        "time": appt.time,
        "date_human": human_date(appt.date),
        "time_human": human_time(appt.time),
    }


# ── 1. place a single reminder call ───────────────────────────────────────────

async def place_reminder_call(appointment_id: str) -> dict:
    """Dial the patient for one appointment and record the attempt. Returns a result
    dict (success + reason/call_sid). Marks `reminder_sent_at` up front so a concurrent
    sweep can't double-dial the same appointment."""
    async with AsyncSessionLocal() as db:
        appt = await db.get(Appointment, appointment_id)
        if not appt:
            return {"success": False, "reason": "appointment_not_found"}
        if appt.status in (AppointmentStatus.cancelled, AppointmentStatus.completed,
                           AppointmentStatus.no_show):
            return {"success": False, "reason": f"appointment_{appt.status.value}"}
        patient = await db.get(Patient, appt.patient_id) if appt.patient_id else None
        if not patient or not patient.phone:
            return {"success": False, "reason": "no_patient_phone"}
        doctor = await db.get(Doctor, appt.doctor_id) if appt.doctor_id else None

        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN
                and settings.TWILIO_PHONE_NUMBER):
            return {"success": False, "reason": "twilio_not_configured"}

        # Claim the appointment immediately (guards against double dialing) and create
        # the pending outbound Call the agent + Twilio callbacks key off of. The agent is
        # picked within the appointment's tenant so the Call is correctly attributed.
        def _agent_q(agent_type):
            q = select(Agent).where(Agent.type == agent_type, Agent.is_active == True)  # noqa: E712
            if appt.tenant_id:
                q = q.where(Agent.tenant_id == appt.tenant_id)
            return q

        outbound_agent = (await db.execute(_agent_q(AgentType.outbound))).scalars().first()
        if not outbound_agent:
            outbound_agent = (await db.execute(_agent_q(AgentType.inbound))).scalars().first()

        appt.reminder_sent_at = datetime.utcnow()
        appt.reminder_outcome = ReminderOutcome.calling.value
        call = Call(
            tenant_id=appt.tenant_id,
            agent_id=outbound_agent.id if outbound_agent else None,
            appointment_id=appt.id,
            purpose="reminder",
            direction=CallDirection.outbound,
            caller_number=settings.TWILIO_PHONE_NUMBER,   # our number is the caller
            called_number=patient.phone,                   # the patient is called
            outcome=CallOutcome.in_progress,
            started_at=datetime.utcnow(),
        )
        db.add(call)
        await db.commit()
        call_id = call.id
        patient_phone = patient.phone

    # Place the actual Twilio call OFF the event loop (the twilio SDK is blocking).
    try:
        call_sid = await asyncio.to_thread(_twilio_dial, patient_phone)
    except Exception as e:
        logger.error("Twilio dial failed for appt %s: %s: %s",
                     appointment_id, type(e).__name__, e)
        await _mark_call_failed(call_id, appointment_id)
        return {"success": False, "reason": "twilio_error", "detail": str(e)}

    # Save the SID so the status/AMD callbacks (keyed by CallSid) can find this call.
    async with AsyncSessionLocal() as db:
        c = await db.get(Call, call_id)
        if c:
            c.twilio_call_sid = call_sid
            await db.commit()
    logger.info("📞 reminder call placed appt=%s sid=%s -> %s",
                appointment_id, call_sid, patient_phone)
    return {"success": True, "call_id": call_id, "call_sid": call_sid,
            "appointment_id": appointment_id}


def _twilio_dial(to_number: str) -> str:
    """Blocking Twilio call create. When answered, Twilio fetches `/twilio/outbound`
    which bridges the call into the LiveKit SIP trunk (same path as inbound). With
    machine detection on, Twilio includes `AnsweredBy` in that request so we can branch
    voicemail vs. human. Returns the Twilio Call SID."""
    from twilio.rest import Client
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    kwargs = dict(
        to=to_number,
        from_=settings.TWILIO_PHONE_NUMBER,
        url=f"{settings.PUBLIC_URL}/twilio/outbound",
        method="POST",
        status_callback=f"{settings.PUBLIC_URL}/twilio/status",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
        status_callback_method="POST",
        timeout=30,
    )
    if settings.REMINDER_MACHINE_DETECTION:
        # DetectMessageEnd waits for the greeting/beep to finish before returning
        # AnsweredBy, so a voicemail is classified before we'd bridge to the agent.
        kwargs["machine_detection"] = "DetectMessageEnd"
        kwargs["machine_detection_timeout"] = 15
    call = client.calls.create(**kwargs)
    return call.sid


async def _mark_call_failed(call_id: str, appointment_id: str):
    async with AsyncSessionLocal() as db:
        c = await db.get(Call, call_id)
        if c and c.outcome == CallOutcome.in_progress:
            c.outcome = CallOutcome.abandoned
        appt = await db.get(Appointment, appointment_id)
        if appt and appt.reminder_outcome == ReminderOutcome.calling.value:
            appt.reminder_outcome = ReminderOutcome.failed.value
        await db.commit()


# ── 2. find appointments due for a reminder ───────────────────────────────────

async def find_due_appointments(now: datetime | None = None) -> list[Appointment]:
    """Appointments occurring within the next REMINDER_HOURS_BEFORE hours that are still
    active and have not had a reminder placed yet. The `reminder_sent_at IS NULL` guard
    is what stops the same appointment being called twice across sweeps."""
    now = now or datetime.now()
    horizon = now + timedelta(hours=settings.REMINDER_HOURS_BEFORE)
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Appointment).where(
                Appointment.reminder_sent_at.is_(None),
                Appointment.status.in_([AppointmentStatus.booked, AppointmentStatus.confirmed]),
            )
        )).scalars().all()
    due = []
    for a in rows:
        dt = _appt_datetime(a)
        if dt and now <= dt <= horizon:
            due.append(a)
    due.sort(key=lambda a: _appt_datetime(a) or now)
    return due


# ── 3. scheduler sweep ────────────────────────────────────────────────────────

async def run_reminder_sweep() -> dict:
    """APScheduler job: place reminder calls for every due appointment (capped)."""
    try:
        due = await find_due_appointments()
    except Exception as e:
        logger.error("reminder sweep: find_due failed: %s: %s", type(e).__name__, e)
        return {"due": 0, "placed": 0}
    if not due:
        logger.info("reminder sweep: no appointments due in the next %sh",
                    settings.REMINDER_HOURS_BEFORE)
        return {"due": 0, "placed": 0}

    capped = due[:_MAX_CALLS_PER_SWEEP]
    if len(due) > _MAX_CALLS_PER_SWEEP:
        logger.warning("reminder sweep: %d due, calling %d this sweep (cap=%d); the rest "
                       "go out next sweep", len(due), len(capped), _MAX_CALLS_PER_SWEEP)
    placed = 0
    for appt in capped:
        res = await place_reminder_call(appt.id)
        if res.get("success"):
            placed += 1
        else:
            logger.info("reminder sweep: skipped appt %s (%s)", appt.id, res.get("reason"))
    logger.info("reminder sweep: %d due, %d calls placed", len(due), placed)
    return {"due": len(due), "placed": placed}


# ── 4. agent side: resolve which appointment a room's call is about ───────────

def _sip_caller_phone(room) -> str | None:
    """Best-effort phone number of the human on the other end of a LiveKit SIP call.
    LiveKit exposes it via participant attributes (sip.phoneNumber / sip.trunkPhoneNumber)
    or, failing that, embedded in the SIP participant identity."""
    try:
        participants = list(getattr(room, "remote_participants", {}).values())
    except Exception:
        return None
    for p in participants:
        attrs = getattr(p, "attributes", None) or {}
        for key in ("sip.phoneNumber", "sip.from_number", "sip.trunkPhoneNumber",
                    "sip.to_number"):
            if attrs.get(key):
                return attrs[key]
        ident = getattr(p, "identity", "") or ""
        m = re.search(r"(\+?\d{7,})", ident)
        if m:
            return m.group(1)
    return None


async def resolve_outbound_context_for_room(room) -> dict | None:
    """Called by the agent worker when it joins a `call-*` room. Returns the reminder
    context if this room belongs to a pending outbound reminder call, else None (normal
    inbound call → the agent uses its standard inbound greeting).

    Matching: among reminder calls placed in the last few minutes and not yet tied to a
    room, prefer the one whose patient phone matches the SIP caller; otherwise (phone
    unavailable) take the most recent — safe here because the clinic is single-tenant and
    reminder calls are placed sequentially."""
    caller_phone = _sip_caller_phone(room)
    cutoff = datetime.utcnow() - timedelta(minutes=_RESOLVE_WINDOW_MIN)
    async with AsyncSessionLocal() as db:
        candidates = (await db.execute(
            select(Call).where(
                Call.purpose == "reminder",
                Call.direction == CallDirection.outbound,
                Call.outcome == CallOutcome.in_progress,
                Call.started_at >= cutoff,
                or_(Call.livekit_room.is_(None), Call.livekit_room == getattr(room, "name", None)),
            ).order_by(Call.started_at.desc())
        )).scalars().all()
        if not candidates:
            return None

        chosen = None
        if caller_phone:
            for c in candidates:
                if _phones_match(c.called_number, caller_phone):
                    chosen = c
                    break
        chosen = chosen or candidates[0]

        appt = await db.get(Appointment, chosen.appointment_id) if chosen.appointment_id else None
        if not appt:
            return None
        patient = await db.get(Patient, appt.patient_id) if appt.patient_id else None
        doctor = await db.get(Doctor, appt.doctor_id) if appt.doctor_id else None

        # Tie this room to the call so a second join can't grab the same pending call.
        chosen.livekit_room = getattr(room, "name", None)
        await db.commit()

        ctx = _build_context(appt, patient, doctor, chosen)
        logger.info("🔗 room %s resolved to reminder call %s (appt %s, phone match=%s)",
                    getattr(room, "name", "?"), chosen.id, appt.id, bool(caller_phone))
        return ctx


# ── 5. record outcomes ────────────────────────────────────────────────────────

async def finalize_reminder_outcome(appointment_id: str | None, call_id: str | None,
                                    outcome: str):
    """Agent-side: record the human-call result on the appointment + close the Call.
    Never downgrades an already-recorded terminal human outcome."""
    if not appointment_id:
        return
    async with AsyncSessionLocal() as db:
        appt = await db.get(Appointment, appointment_id)
        if appt:
            cur = appt.reminder_outcome
            if cur not in _TERMINAL_HUMAN or outcome in _TERMINAL_HUMAN:
                appt.reminder_outcome = outcome
        if call_id:
            c = await db.get(Call, call_id)
            if c and c.outcome == CallOutcome.in_progress:
                c.outcome = CallOutcome.resolved
        await db.commit()


async def record_reminder_result_by_sid(call_sid: str, *, twilio_status: str | None = None,
                                        answered_by: str | None = None) -> bool:
    """Twilio-side: map a status/AMD callback to a reminder outcome on the appointment.
    Only sets no-answer / voicemail / failed for calls a human never handled — it never
    overrides a confirmed/rescheduled/cancelled/answered result the agent recorded.
    Returns True if this SID belongs to a reminder call (so the caller can stop early)."""
    if not call_sid:
        return False
    async with AsyncSessionLocal() as db:
        call = (await db.execute(
            select(Call).where(Call.twilio_call_sid == call_sid)
        )).scalars().first()
        if not call or call.purpose != "reminder":
            return False

        outcome = None
        if answered_by and answered_by.startswith("machine"):
            outcome = ReminderOutcome.voicemail.value
        elif answered_by == "fax":
            outcome = ReminderOutcome.failed.value
        elif twilio_status in ("no-answer", "busy"):
            outcome = ReminderOutcome.no_answer.value
        elif twilio_status in ("failed", "canceled"):
            outcome = ReminderOutcome.failed.value

        if outcome and call.appointment_id:
            appt = await db.get(Appointment, call.appointment_id)
            if appt and appt.reminder_outcome not in _TERMINAL_HUMAN:
                appt.reminder_outcome = outcome
                # Reflect the machine/no-answer result on the Call too.
                if outcome == ReminderOutcome.voicemail.value:
                    call.outcome = CallOutcome.voicemail
                elif outcome == ReminderOutcome.no_answer.value:
                    call.outcome = CallOutcome.no_answer
                elif outcome == ReminderOutcome.failed.value and call.outcome == CallOutcome.in_progress:
                    call.outcome = CallOutcome.abandoned
                await db.commit()
                logger.info("📋 reminder sid=%s -> outcome=%s (status=%s answered_by=%s)",
                            call_sid, outcome, twilio_status, answered_by)
        return True
