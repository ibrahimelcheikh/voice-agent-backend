"""
Dedicated LiveKit agent worker for the clinic receptionist.

Run it directly:
    python -m app.agents.agent_worker dev      # local dev with hot reload
    python -m app.agents.agent_worker start     # production
    python -m app.agents.agent_worker           # defaults to `start`

NOTE: the livekit-agents framework REQUIRES a subcommand (`dev`/`start`/`console`).
Bare `python -m app.agents.agent_worker` is mapped to `start` below.

The worker registers with LiveKit and, via AUTOMATIC dispatch, is offered a job for
every new room; `_request_fnc` accepts only `call-*` rooms (the SIP dispatch rule's
prefix) and rejects the rest. Each accepted job runs `clinic_agent.entrypoint`, which
connects to the room and runs the full guarded AgentSession.

Deployment note: this worker is the ONLY thing that joins call rooms. The main web
service (uvicorn) serves the REST API only and spawns NO agents, guaranteeing exactly
one agent per call. Run this as a single, separate Railway service — never two copies,
or two agents would answer the same call.

Explicit dispatch alternative: give WorkerOptions an `agent_name="clinic-agent"` and add
`RoomConfiguration(agents=[RoomAgentDispatch(agent_name="clinic-agent")])` to the SIP
dispatch rule (see scripts/setup_livekit_sip.py). Automatic dispatch (the default below)
needs no rule change, which is why it's used here.
"""
import os
import sys

from app.core.config import settings

# Expose credentials to the livekit-agents CLI and the plugins, which read them from
# the environment. Only set non-empty values so we never clobber real env vars
# (e.g. on Railway) with blanks.
for _key, _val in {
    "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    "DEEPGRAM_API_KEY": settings.DEEPGRAM_API_KEY,
    "LIVEKIT_URL": settings.LIVEKIT_URL,
    "LIVEKIT_API_KEY": settings.LIVEKIT_API_KEY,
    "LIVEKIT_API_SECRET": settings.LIVEKIT_API_SECRET,
}.items():
    if _val:
        os.environ[_key] = _val

from livekit.agents import WorkerOptions, JobRequest, cli  # noqa: E402

from app.agents.clinic_agent import entrypoint  # noqa: E402


async def _request_fnc(req: JobRequest):
    """Accept only SIP call rooms (prefixed `call-`); reject anything else."""
    room_name = (req.room.name if req.room else "") or ""
    if room_name.startswith("call-"):
        print(f"[worker] accepting job for room {room_name}")
        await req.accept()
    else:
        print(f"[worker] rejecting non-call room {room_name!r}")
        await req.reject()


def main():
    if len(sys.argv) == 1:
        sys.argv.append("start")
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, request_fnc=_request_fnc))


if __name__ == "__main__":
    main()
