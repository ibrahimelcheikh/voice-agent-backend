"""
LiveKit webhooks — fired by LiveKit Cloud on room/participant events.

When a SIP caller joins a room (Twilio → LiveKit SIP trunk → room), we record
the call and spawn the Aria agent into that room. On room_finished we close out
the call record.

Set the webhook URL in LiveKit Dashboard → Settings → Webhooks:
    {PUBLIC_URL}/livekit/webhook
"""
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Call, Agent, BehaviorConfig, CallDirection, CallOutcome
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


async def _behavior_config_for_inbound(db: AsyncSession):
    agent = (await db.execute(
        select(Agent).where(Agent.type == "inbound", Agent.is_active == True)
    )).scalars().first()
    behavior_config = {}
    if agent and agent.behavior_config_id:
        cfg = (await db.execute(
            select(BehaviorConfig).where(BehaviorConfig.id == agent.behavior_config_id)
        )).scalars().first()
        if cfg:
            behavior_config = {
                "system_prompt": cfg.system_prompt,
                "hard_rules": cfg.hard_rules or [],
                "voice_id": agent.voice_id,
            }
    return agent, behavior_config


@router.post("/webhook")
async def livekit_webhook(request: Request, background_tasks: BackgroundTasks,
                          db: AsyncSession = Depends(get_db)):
    try:
        from livekit import api
        receiver = api.WebhookReceiver(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        body = await request.body()
        auth_token = request.headers.get("Authorization", "")
        event = receiver.receive(body.decode("utf-8"), auth_token)

        if event.event == "participant_joined" and _is_sip_participant(event.participant):
            room_name = event.room.name
            caller = event.participant.identity
            print(f"[livekit] SIP caller {caller} joined room {room_name}")

            agent, behavior_config = await _behavior_config_for_inbound(db)
            call = Call(
                agent_id=agent.id if agent else None,
                livekit_room=room_name,
                direction=CallDirection.inbound,
                caller_number=caller,
                called_number=settings.TWILIO_PHONE_NUMBER,
                outcome=CallOutcome.in_progress,
                started_at=datetime.utcnow(),
            )
            db.add(call)
            await db.commit()

            from app.agents.clinic_agent import run_agent_in_room
            background_tasks.add_task(run_agent_in_room, room_name, behavior_config, call.id)

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
                print(f"[livekit] room {room_name} finished, call closed")

    except Exception as e:
        print(f"[livekit] webhook error: {type(e).__name__}: {e}")

    return {"status": "ok"}
