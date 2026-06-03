"""
Twilio Webhooks — This is where real phone calls come in
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Call, Agent, CallDirection, CallOutcome
from app.core.config import settings
from datetime import datetime

router = APIRouter()


def _media_stream_url() -> str:
    """wss URL of the Twilio Media Streams endpoint, derived from PUBLIC_URL."""
    base = settings.PUBLIC_URL.replace("https://", "wss://").replace("http://", "ws://").rstrip("/")
    return f"{base}/twilio/media-stream"


def _media_stream_twiml(call_sid: str) -> str:
    """Bidirectional Media Streams TwiML — bridges the call audio to our WebSocket."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{_media_stream_url()}">
            <Parameter name="callSid" value="{call_sid}"/>
        </Stream>
    </Connect>
</Response>"""


@router.post("/inbound")
async def handle_inbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio hits this when someone calls +16575347796. We persist the call and
    return TwiML that bridges the audio to our Media Streams WebSocket."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    caller = form_data.get("From", "unknown")
    called = form_data.get("To", settings.TWILIO_PHONE_NUMBER)

    agent = (await db.execute(
        select(Agent).where(Agent.type == "inbound", Agent.is_active == True)
    )).scalars().first()

    call = Call(
        agent_id=agent.id if agent else None,
        twilio_call_sid=call_sid,
        direction=CallDirection.inbound,
        caller_number=caller,
        called_number=called,
        outcome=CallOutcome.in_progress,
        started_at=datetime.utcnow(),
    )
    db.add(call)
    await db.commit()

    return Response(content=_media_stream_twiml(call_sid), media_type="application/xml")


@router.post("/outbound")
async def handle_outbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Called by Twilio when our outbound call is answered — bridge to Media Streams."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")

    call = (await db.execute(
        select(Call).where(Call.twilio_call_sid == call_sid)
    )).scalars().first()
    if call and call.outcome == CallOutcome.in_progress and not call.started_at:
        call.started_at = datetime.utcnow()
        await db.commit()

    return Response(content=_media_stream_twiml(call_sid), media_type="application/xml")

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
