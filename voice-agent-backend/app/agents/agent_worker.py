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


def _prewarm_models():
    """Download the turn-detector (smart end-of-utterance) model into the local cache so
    the MultilingualModel loads at call time instead of failing with 'languages.json not
    found' and silently falling back to dumb VAD (which cuts callers off mid-sentence).

    There is no Dockerfile here (Railway builds via Nixpacks), so we fetch at worker
    startup rather than at image build. download_files() is the same routine the
    `download-files` CLI runs; it no-ops when the files are already cached. Never fatal —
    on failure the agent still runs with VAD endpointing."""
    try:
        from livekit.plugins import turn_detector  # noqa: F401 — registers the EOU plugin
        from livekit.agents import Plugin
        for p in Plugin.registered_plugins:
            if "turn_detector" in (p.package or ""):
                print(f"[worker] prewarming model: {p.package}")
                p.download_files()
        print("[worker] turn-detector model ready")
    except Exception as e:
        print(f"[worker] model prewarm failed ({type(e).__name__}: {e}); "
              "agent will use VAD endpointing")


async def _request_fnc(req: JobRequest):
    """Auto-accept inbound SIP call rooms (prefixed `call-`); reject anything else.

    This is the same auto-accept behavior the worker had before the multi-tenant refactor —
    it does NOT look at tenant/metadata; the tenant is resolved later, at agent start, from
    the dialed number. The log line below fires for EVERY job request the worker is offered,
    so if an inbound call produces no '◀ JOB REQUEST' line, no room was created for it
    (the SIP trunk rejected the call) — the problem is upstream, not here."""
    room_name = (req.room.name if req.room else "") or ""
    print(f"[worker] ◀ JOB REQUEST received for room {room_name!r}", flush=True)
    if room_name.startswith("call-"):
        print(f"[worker] ✅ accepting job for room {room_name}", flush=True)
        await req.accept()
    else:
        print(f"[worker] rejecting non-call room {room_name!r}", flush=True)
        await req.reject()


def main():
    if len(sys.argv) == 1:
        sys.argv.append("start")
    _prewarm_models()  # ensure the EOU model is cached before we start taking calls
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, request_fnc=_request_fnc))


if __name__ == "__main__":
    main()
