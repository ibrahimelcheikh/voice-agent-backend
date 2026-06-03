"""
Dedicated LiveKit agent worker — complete, standalone process.

Run it directly:
    python -m app.agents.agent_worker          # defaults to `start`
    python -m app.agents.agent_worker dev        # local dev with hot reload

The worker registers with LiveKit, accepts only `call-*` rooms (the SIP dispatch
rule's prefix), joins each one automatically, greets the caller, and runs the
full Aria conversation:

    Silero VAD  +  OpenAI STT (whisper-1)  +  GPT-4o-mini  +  OpenAI TTS (alloy)
    + the Golden Fork tools (book / cancel / check reservations, take / check
      orders, answer FAQs, transfer to human)

This is the canonical livekit-agents architecture (the worker waits for jobs and
joins rooms automatically). Run EITHER this worker OR the in-process room watcher
(ENABLE_ROOM_WATCHER on the web service), not both, or two agents join each call.

NOTE: livekit-agents 1.5.1 replaced the old `VoiceAssistant` with
`AgentSession` + `Agent`. The legacy `livekit.agents.voice_assistant.VoiceAssistant`
no longer exists, so this worker uses `AgentSession` (via the shared entrypoint),
which provides the same VAD/STT/LLM/TTS pipeline plus function-calling tools.
"""
import os
import sys

from app.core.config import settings

# Expose credentials to the livekit-agents CLI and the OpenAI plugin, both of
# which read these from the environment. Only set non-empty values so we never
# clobber real env vars (e.g. on Railway) with blanks.
for _key, _val in {
    "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    "LIVEKIT_URL": settings.LIVEKIT_URL,
    "LIVEKIT_API_KEY": settings.LIVEKIT_API_KEY,
    "LIVEKIT_API_SECRET": settings.LIVEKIT_API_SECRET,
}.items():
    if _val:
        os.environ[_key] = _val

from livekit.agents import WorkerOptions, cli, JobRequest  # noqa: E402
from app.agents.pipecat_agent import _entrypoint  # noqa: E402  (shared agent/session/tools)


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
