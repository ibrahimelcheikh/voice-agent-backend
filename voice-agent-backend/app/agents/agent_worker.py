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
    """ALWAYS accept the job. Logged BEFORE any tenant logic so the worker log shows every
    job the worker is offered.

    The tenant is NOT carried in job metadata — it is resolved later, at agent start, from
    the DIALED number (see clinic_agent.entrypoint). So this handler must never decline based
    on tenant/metadata. With explicit dispatch (agent_name set) the worker is only offered
    jobs the dispatch rule routed to it (inbound `call-*` SIP rooms), so accepting them all
    is correct. If you see NO '◀ JOB REQUEST' line on an inbound call, the dispatch rule is
    not routing the room to this agent_name (name mismatch) or no room was created — the
    problem is upstream of this handler."""
    room_name = (req.room.name if req.room else "") or ""
    print(f"[WORKER] ◀ JOB REQUEST received for room {room_name!r} — accepting", flush=True)
    await req.accept()


def main():
    if len(sys.argv) == 1:
        sys.argv.append("start")
    _prewarm_models()  # ensure the EOU model is cached before we start taking calls

    # EXPLICIT dispatch by agent_name (default "clinic-agent") so the worker matches the
    # LiveKit SIP dispatch rule, which routes inbound `call-*` rooms to that agent name.
    # An automatic-dispatch worker (no agent_name) is NEVER offered a job for a room whose
    # dispatch rule names a specific agent — that mismatch is the inbound-dispatch failure.
    # Set AGENT_NAME="" to fall back to automatic dispatch (only if the rule has no agent).
    opts = dict(entrypoint_fnc=entrypoint, request_fnc=_request_fnc)
    if settings.AGENT_NAME:
        opts["agent_name"] = settings.AGENT_NAME
        print(f"[WORKER] registering with agent_name={settings.AGENT_NAME!r} "
              "(EXPLICIT dispatch — must match the SIP dispatch rule's agent name)",
              flush=True)
    else:
        print("[WORKER] registering with NO agent_name (AUTOMATIC dispatch — offered every "
              "room; only correct if the dispatch rule has no explicit agent)", flush=True)
    cli.run_app(WorkerOptions(**opts))


if __name__ == "__main__":
    main()
