"""
Dedicated LiveKit agent worker for the clinic receptionist (FILE 9).

Run it directly:
    python -m app.agents.agent_worker          # defaults to `start`
    python -m app.agents.agent_worker dev      # local dev with hot reload

The worker registers with LiveKit, accepts only `call-*` rooms (the SIP dispatch
rule's prefix), and for each one runs the full Pipecat clinic pipeline
(Silero VAD + STT + GPT-4o-mini wrapped by the IntentGuardrailProcessor +
multilingual OpenAI TTS) via app.agents.clinic_agent.run_clinic_agent.

This is the canonical architecture (the worker waits for jobs and joins rooms
automatically). Run EITHER this worker OR the in-process room watcher
(ENABLE_ROOM_WATCHER on the web service), not both, or two agents join a call.
"""
import os
import sys
from datetime import datetime

from app.core.config import settings

# Expose credentials to the livekit-agents CLI and the plugins, which read them
# from the environment. Only set non-empty values so we never clobber real env
# vars (e.g. on Railway) with blanks.
for _key, _val in {
    "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    "DEEPGRAM_API_KEY": settings.DEEPGRAM_API_KEY,
    "LIVEKIT_URL": settings.LIVEKIT_URL,
    "LIVEKIT_API_KEY": settings.LIVEKIT_API_KEY,
    "LIVEKIT_API_SECRET": settings.LIVEKIT_API_SECRET,
}.items():
    if _val:
        os.environ[_key] = _val

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, JobRequest  # noqa: E402,F401

from app.agents.clinic_agent import run_clinic_agent  # noqa: E402


async def _behavior_config():
    """Load the active inbound agent's behavior lock config (best effort)."""
    try:
        from sqlalchemy import select
        from app.db.database import AsyncSessionLocal
        from app.models.models import Agent, BehaviorConfig
        async with AsyncSessionLocal() as db:
            agent = (await db.execute(
                select(Agent).where(Agent.type == "inbound", Agent.is_active == True)  # noqa: E712
            )).scalars().first()
            if agent and agent.behavior_config_id:
                cfg = (await db.execute(
                    select(BehaviorConfig).where(BehaviorConfig.id == agent.behavior_config_id)
                )).scalars().first()
                if cfg:
                    return agent, {
                        "system_prompt": cfg.system_prompt,
                        "hard_rules": cfg.hard_rules or [],
                        "voice_id": agent.voice_id,
                        "max_call_duration": cfg.max_call_duration,
                    }
            return agent, {}
    except Exception as e:
        print(f"[worker] behavior config load failed: {type(e).__name__}: {e}")
        return None, {}


async def _create_call_record(agent, room_name, caller):
    try:
        from app.db.database import AsyncSessionLocal
        from app.models.models import Call, CallDirection, CallOutcome
        async with AsyncSessionLocal() as db:
            call = Call(
                agent_id=agent.id if agent else None,
                livekit_room=room_name,
                direction=CallDirection.inbound,
                caller_number=caller or "sip-caller",
                called_number=settings.TWILIO_PHONE_NUMBER,
                outcome=CallOutcome.in_progress,
                started_at=datetime.utcnow(),
            )
            db.add(call)
            await db.commit()
            return call.id
    except Exception as e:
        print(f"[worker] call record create failed: {type(e).__name__}: {e}")
        return None


async def _entrypoint(ctx: JobContext):
    room_name = ctx.room.name if ctx.room else (ctx.job.room.name if ctx.job and ctx.job.room else "")
    print(f"[worker] handling room {room_name}")

    # Pipecat's LiveKitTransport connects as the agent participant itself, so we
    # do NOT call ctx.connect() here (that would create a second participant).
    agent, behavior_config = await _behavior_config()
    call_id = await _create_call_record(agent, room_name, None)
    await run_clinic_agent(room_name, behavior_config, call_id)


async def _request_fnc(req: JobRequest):
    """Accept only SIP call rooms (prefixed `call-`); reject anything else."""
    room_name = (req.room.name if req.room else "") or ""
    if room_name.startswith("call-"):
        print(f"[worker] accepting job for room {room_name}")
        await req.accept()
    else:
        await req.reject()


def main():
    # Allow bare `python -m app.agents.agent_worker` (no subcommand) -> `start`.
    if len(sys.argv) == 1:
        sys.argv.append("start")
    cli.run_app(WorkerOptions(entrypoint_fnc=_entrypoint, request_fnc=_request_fnc))


if __name__ == "__main__":
    main()
