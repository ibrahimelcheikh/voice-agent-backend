"""
Twilio Webhooks — This is where real phone calls come in
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Call, CallOutcome
from app.core.config import settings
from datetime import datetime

router = APIRouter()


def _livekit_sip_host() -> str:
    """Project SIP host derived from LIVEKIT_URL.
    wss://<proj>.livekit.cloud -> <proj>.sip.livekit.cloud
    (verify in LiveKit Dashboard → Settings → SIP)."""
    host = settings.LIVEKIT_URL.replace("wss://", "").replace("ws://", "").rstrip("/")
    return host.replace(".livekit.cloud", ".sip.livekit.cloud")


def _sip_dial_twiml(called_number: str | None = None) -> str:
    """TwiML that dials the call into the LiveKit SIP trunk. The DIALED number becomes
    the SIP user part so LiveKit carries it as the trunk/called number — that is the
    phone -> tenant routing key the agent reads when it joins the `call-<random>` room."""
    number = called_number or settings.TWILIO_PHONE_NUMBER
    sip_uri = f"sip:{number}@{_livekit_sip_host()};transport=tcp"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>{sip_uri}</Sip>
    </Dial>
</Response>"""


def _not_configured_twiml() -> str:
    """Spoken to a caller who dialed a number that no tenant owns, then hang up."""
    return ("""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Thank you for calling. This number is not yet configured. """
            """Please contact support. Goodbye.</Say>
    <Hangup/>
</Response>""")


@router.post("/inbound")
async def handle_inbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio hits this when someone calls one of our numbers.

    PHONE -> TENANT ROUTING: the dialed number (`To`) identifies the tenant. If a tenant
    owns it, we bridge the call into the LiveKit SIP trunk (the agent loads that tenant's
    config when it joins the room). If NO tenant matches, we play a generic 'not
    configured' message and hang up — the call never reaches an agent."""
    from app.services.tenant_service import resolve_tenant_by_number

    form = await request.form()
    called = form.get("To") or settings.TWILIO_PHONE_NUMBER

    tenant = await resolve_tenant_by_number(db, called)
    if not tenant:
        print(f"[twilio] inbound to {called!r} matches no tenant — playing 'not configured'")
        return Response(content=_not_configured_twiml(), media_type="application/xml")

    print(f"[twilio] inbound to {called!r} routed to tenant {tenant.id} ({tenant.business_name})")
    # Use the tenant's own number as the SIP user part so the agent resolves the same
    # tenant from the SIP join (consistent with how `To` matched it here).
    return Response(content=_sip_dial_twiml(tenant.twilio_phone_number or called),
                    media_type="application/xml")


def _hangup_twiml() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n    <Hangup/>\n</Response>'


@router.post("/outbound")
async def handle_outbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Called by Twilio when our outbound reminder call is answered.

    With machine detection enabled, Twilio includes `AnsweredBy` here. If it answered to
    a machine (voicemail), we record the outcome and hang up — no point running the agent
    against an answering machine. A human answer is bridged into the LiveKit SIP trunk
    (same path as inbound), where the agent worker joins and runs the reminder script."""
    form = await request.form()
    call_sid = form.get("CallSid")
    answered_by = form.get("AnsweredBy")  # human / machine_start / machine_end_beep / fax / unknown

    if answered_by and (answered_by.startswith("machine") or answered_by == "fax"):
        try:
            from app.services.reminder_service import record_reminder_result_by_sid
            await record_reminder_result_by_sid(call_sid, answered_by=answered_by)
        except Exception as e:
            print(f"[twilio] voicemail record error: {type(e).__name__}: {e}")
        print(f"[twilio] outbound call {call_sid} answered by {answered_by} — hanging up")
        return Response(content=_hangup_twiml(), media_type="application/xml")

    return Response(content=_sip_dial_twiml(), media_type="application/xml")

@router.post("/status")
async def call_status_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio calls this when call status changes (completed, failed, etc)"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus")
    duration = form_data.get("CallDuration", 0)
    answered_by = form_data.get("AnsweredBy")  # present on AMD status callbacks

    # For outbound reminder calls, map no-answer / busy / failed / voicemail onto the
    # appointment's reminder_outcome (without overriding a human result the agent set).
    try:
        from app.services.reminder_service import record_reminder_result_by_sid
        await record_reminder_result_by_sid(call_sid, twilio_status=call_status,
                                            answered_by=answered_by)
    except Exception as e:
        print(f"[twilio] reminder status record error: {type(e).__name__}: {e}")

    result = await db.execute(select(Call).where(Call.twilio_call_sid == call_sid))
    call = result.scalars().first()

    if call:
        try:
            call.duration_seconds = int(duration)
        except (TypeError, ValueError):
            pass
        call.ended_at = datetime.utcnow()
        # Don't clobber a terminal outcome already recorded (e.g. voicemail/no_answer
        # from AMD, or the agent's resolution) with a generic status mapping.
        if call.outcome == CallOutcome.in_progress:
            if call_status == "completed":
                call.outcome = CallOutcome.resolved
            elif call_status in ["no-answer", "busy"]:
                call.outcome = CallOutcome.no_answer
            elif call_status == "failed":
                call.outcome = CallOutcome.abandoned
        await db.commit()

    return Response(content="OK", media_type="text/plain")
