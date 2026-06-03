"""
Dedicated LiveKit agent worker — the canonical livekit-agents architecture.

Run as its OWN process / Railway service:
    python -m app.agents.agent_worker start

The worker registers with LiveKit and is dispatched to each new room
automatically (no agent_name => automatic dispatch), so when a SIP call creates
a `call-*` room the worker joins it and runs Aria (STT → LLM → TTS, Silero VAD,
barge-in, and the Golden Fork booking/order/FAQ tools).

NOTE: use EITHER this worker OR the in-process room watcher
(ENABLE_ROOM_WATCHER in the web service), not both — otherwise two agents join
each call. When you deploy this worker, set ENABLE_ROOM_WATCHER=false on the web
service.

The 1.x livekit-agents API is used (AgentSession + Agent). The old
`livekit.agents.voice_assistant.VoiceAssistant` API no longer exists.
"""
from livekit.agents import WorkerOptions, cli

# Reuse the exact entrypoint (agent + 7 tools + greeting) validated in pipecat_agent.
from app.agents.pipecat_agent import _entrypoint


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=_entrypoint))
