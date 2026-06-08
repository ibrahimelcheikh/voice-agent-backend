"""
LiveKit webhooks — fired by LiveKit Cloud on room/participant events.

This web service does NOT spawn voice agents. Agent join is owned exclusively by
the dedicated agent_worker process (LiveKit automatic dispatch), so there is
exactly one agent per call. Here we only log SIP joins and close out the Call
record on room_finished as a safety net.

Set the webhook URL in LiveKit Dashboard → Settings → Webhooks:
    {PUBLIC_URL}/livekit/webhook
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Call, CallOutcome
from app.core.config import settings
from datetime import datetime

router = APIRouter()


def _is_sip_participant(participant) -> bool:
    """Detect a real phone caller (SIP) vs. our own agent participant."""
    try:
        from livekit.protocol import models as m
        if participant.kind == m.ParticipantInfo.Kind.SIP:
            return True
    except Exception:
        pass
    identity = (getattr(participant, "identity", "") or "").lower()
    return "sip" in identity


@router.post("/webhook")
async def livekit_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        from livekit import api
        receiver = api.WebhookReceiver(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        body = await request.body()
        auth_token = request.headers.get("Authorization", "")
        event = receiver.receive(body.decode("utf-8"), auth_token)

        if event.event == "participant_joined" and _is_sip_participant(event.participant):
            # The web service does NOT spawn agents. The dedicated agent_worker
            # process joins the room (via LiveKit automatic dispatch) and owns the
            # Call record. We only log here so there is exactly one agent per call.
            # Dump every SIP attribute present on the join so the dialed/caller numbers
            # the agent will read are visible at this hop too.
            attrs = dict(getattr(event.participant, "attributes", None) or {})
            print(f"[LK-HOOK] SIP caller {event.participant.identity!r} joined "
                  f"room {event.room.name!r} — SIP attributes={attrs!r} "
                  "(agent_worker will handle it)", flush=True)

        elif event.event == "room_finished":
            room_name = event.room.name
            call = (await db.execute(
                select(Call).where(Call.livekit_room == room_name,
                                   Call.outcome == CallOutcome.in_progress)
            )).scalars().first()
            if call:
                call.outcome = CallOutcome.resolved
                call.ended_at = datetime.utcnow()
                if call.started_at:
                    call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())
                await db.commit()
                print(f"[LK-HOOK] room {room_name!r} finished, call closed", flush=True)

    except Exception as e:
        print(f"[LK-HOOK] webhook error: {type(e).__name__}: {e}", flush=True)

    return {"status": "ok"}
