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


def _sip_dial_twiml() -> str:
    """TwiML that dials the call into the LiveKit SIP trunk. LiveKit matches the
    inbound trunk by the called number, then the dispatch rule drops it into a
    `call-<random>` room where the Aria agent joins."""
    sip_uri = f"sip:{settings.TWILIO_PHONE_NUMBER}@{_livekit_sip_host()};transport=tcp"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>{sip_uri}</Sip>
    </Dial>
</Response>"""


@router.post("/inbound")
async def handle_inbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio hits this when someone calls the number. We bridge the call into the
    LiveKit SIP trunk via <Dial><Sip>. The Call record is created by the LiveKit
    `participant_joined` webhook (see livekit_webhooks.py), so we don't duplicate it."""
    return Response(content=_sip_dial_twiml(), media_type="application/xml")


@router.post("/outbound")
async def handle_outbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Called by Twilio when our outbound call is answered — bridge into LiveKit SIP."""
    return Response(content=_sip_dial_twiml(), media_type="application/xml")

@router.post("/status")
async def call_status_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio calls this when call status changes (completed, failed, etc)"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus")
    duration = form_data.get("CallDuration", 0)

    result = await db.execute(select(Call).where(Call.twilio_call_sid == call_sid))
    call = result.scalars().first()

    if call:
        call.duration_seconds = int(duration)
        call.ended_at = datetime.utcnow()
        if call_status == "completed":
            call.outcome = CallOutcome.resolved
        elif call_status in ["no-answer", "busy"]:
            call.outcome = CallOutcome.no_answer
        elif call_status == "failed":
            call.outcome = CallOutcome.abandoned
        await db.commit()

    return Response(content="OK", media_type="text/plain")
