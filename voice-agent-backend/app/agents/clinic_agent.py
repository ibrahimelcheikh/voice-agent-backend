"""
Clinic receptionist voice agent — Pipecat pipeline (FILE 1).

Architecture:  Twilio (SIP) -> LiveKit Room -> Pipecat Pipeline -> Agent

Pipecat orchestrates everything. Pipeline order:

    transport.input()
      -> STT (Deepgram if key exists, else OpenAI Whisper)
      -> user context aggregator
      -> IntentGuardrailProcessor   (anti-hallucination wrapper)
      -> LLM (GPT-4o-mini, locked)
      -> TTS (OpenAI, multilingual)
      -> transport.output()
      -> assistant context aggregator

Features: Silero VAD (stop_secs=0.6) for natural turn-taking, allow_interruptions
for barge-in (TTS stops the instant the caller speaks), metrics, prerecorded
greeting/goodbye, intelligent call ending, and multi-language support.

Shared entry point `run_clinic_agent(room_name, ...)` is used by both the
dedicated worker (agent_worker.py) and the webhook/room-watcher fallbacks.
"""
import asyncio
from datetime import datetime, date

from app.core.config import settings
from app.agents import audio as audio_clips

# The locked system prompt. The guardrail rebuilds a tighter instruction every
# turn, but this is the baseline contract for the LLM.
DEFAULT_SYSTEM_PROMPT = (
    "You are a clinic receptionist AI. You may ONLY state information provided to you in "
    "the function results. NEVER invent appointment times, prices, doctor names, or policies. "
    "If you don't have the data, offer to connect to staff. Keep responses under 2 sentences. "
    "Be warm and professional."
)

# Rooms handled in THIS process — guards the webhook and room watcher against a
# double-join into the same room.
_active_rooms: set[str] = set()


def generate_agent_token(room_name: str) -> str:
    from livekit import api
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity("clinic-agent")
        .with_name("Clinic Assistant")
        .with_grants(api.VideoGrants(
            room_join=True, room=room_name, can_publish=True, can_subscribe=True))
    )
    return token.to_jwt()


def _build_stt():
    """Deepgram STT when a key + plugin are available, else OpenAI Whisper."""
    if settings.DEEPGRAM_API_KEY:
        try:
            from pipecat.services.deepgram.stt import DeepgramSTTService
            return DeepgramSTTService(api_key=settings.DEEPGRAM_API_KEY)
        except Exception as e:
            print(f"[agent] Deepgram unavailable ({type(e).__name__}: {e}); using OpenAI Whisper")
    from pipecat.services.openai.stt import OpenAISTTService
    return OpenAISTTService(api_key=settings.OPENAI_API_KEY, model="whisper-1")


def _build_tts(voice: str):
    # gpt-4o-mini-tts is multilingual — the same voice speaks EN/AR/FR/ES based
    # on the language the LLM replies in.
    from pipecat.services.openai.tts import OpenAITTSService
    return OpenAITTSService(api_key=settings.OPENAI_API_KEY,
                            voice=voice or "shimmer", model="gpt-4o-mini-tts")


def _build_llm():
    from pipecat.services.openai.llm import OpenAILLMService
    return OpenAILLMService(api_key=settings.OPENAI_API_KEY, model="gpt-4o-mini")


async def run_clinic_agent(room_name: str, behavior_config: dict | None = None,
                           call_id: str | None = None):
    """Join a LiveKit room and run the clinic Pipecat pipeline until the call
    ends. Never raises. Idempotent per room within this process."""
    behavior_config = behavior_config or {}
    if room_name in _active_rooms:
        return
    _active_rooms.add(room_name)
    started_at = datetime.utcnow()
    try:
        await _run(room_name, behavior_config, call_id, started_at)
    except Exception as e:
        print(f"[agent] error in room {room_name}: {type(e).__name__}: {e}")
    finally:
        _active_rooms.discard(room_name)


async def _run(room_name, behavior_config, call_id, started_at):
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.audio.vad.vad_analyzer import VADParams
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask, PipelineParams
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
    from pipecat.transports.services.livekit import LiveKitTransport, LiveKitParams

    from app.agents.guardrail import IntentGuardrailProcessor

    voice = behavior_config.get("voice_id") or "shimmer"
    system_prompt = behavior_config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    max_duration = int(behavior_config.get("max_call_duration") or 300)  # 5 min cap

    # Silero VAD with a 0.6s stop window -> natural turn detection.
    vad = SileroVADAnalyzer(params=VADParams(stop_secs=0.6))

    transport = LiveKitTransport(
        url=settings.LIVEKIT_URL,
        token=generate_agent_token(room_name),
        room_name=room_name,
        params=LiveKitParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=vad,                 # smart endpointing
        ),
    )

    stt = _build_stt()
    tts = _build_tts(voice)
    llm = _build_llm()

    context = OpenAILLMContext(messages=[{"role": "system", "content": system_prompt}])
    aggregator = llm.create_context_aggregator(context)

    # Mutable call state captured by the guardrail callbacks.
    state = {"language": "en", "entities": {}}
    finishing = {"done": False}

    pipeline = None  # set below; referenced by callbacks via closure
    task_ref = {}

    async def on_end_call(reason: str):
        if finishing["done"]:
            return
        finishing["done"] = True
        print(f"[agent] ending call in {room_name}: {reason}")
        asyncio.create_task(_finish(task_ref.get("task"), call_id, state, reason, started_at))

    def on_state(s: dict):
        state.update(s)

    guardrail = IntentGuardrailProcessor(
        openai_api_key=settings.OPENAI_API_KEY,
        today=date.today().isoformat(),
        on_end_call=on_end_call,
        on_state=on_state,
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        aggregator.user(),
        guardrail,
        llm,
        tts,
        transport.output(),
        aggregator.assistant(),
    ])

    task = PipelineTask(pipeline, params=PipelineParams(
        allow_interruptions=True,      # barge-in: caller speech stops TTS immediately
        enable_metrics=True,
        enable_usage_metrics=True,
    ))
    task_ref["task"] = task

    # Greeting: play the prerecorded clip the moment the caller connects.
    @transport.event_handler("on_first_participant_joined")
    async def _greet(_transport, _participant):
        print(f"[agent] caller joined {room_name} — playing greeting")
        await audio_clips.play_clip(task, "greeting")

    # Caller hangs up -> end the task.
    @transport.event_handler("on_participant_disconnected")
    async def _left(_transport, _participant):
        await on_end_call("caller_hung_up")

    @transport.event_handler("on_disconnected")
    async def _disc(_transport):
        await on_end_call("room_disconnected")

    # Hard cap on call duration (default 5 minutes).
    async def _duration_guard():
        await asyncio.sleep(max_duration)
        await on_end_call("max_duration_reached")

    duration_task = asyncio.create_task(_duration_guard())

    print(f"[agent] running clinic pipeline in room {room_name}")
    runner = PipelineRunner(handle_sigint=False)
    try:
        await runner.run(task)
    finally:
        duration_task.cancel()
        if not finishing["done"]:
            await _close_call(call_id, state, "completed", started_at)


async def _finish(task, call_id, state, reason, started_at):
    """Play goodbye, let it finish, then end the pipeline and close the call."""
    try:
        if task is not None:
            await audio_clips.play_clip(task, "goodbye")
            await asyncio.sleep(audio_clips.clip_duration_seconds("goodbye") + 0.6)
            await task.stop_when_done()
    except Exception as e:
        print(f"[agent] finish error: {type(e).__name__}: {e}")
    await _close_call(call_id, state, "resolved", started_at, reason)


async def _close_call(call_id, state, outcome, started_at, reason=None):
    """Persist outcome, duration, detected language, and extracted data."""
    if not call_id:
        return
    try:
        from app.db.database import AsyncSessionLocal
        from app.models.models import Call, CallOutcome
        async with AsyncSessionLocal() as db:
            call = await db.get(Call, call_id)
            if not call:
                return
            call.ended_at = datetime.utcnow()
            call.duration_seconds = int((call.ended_at - started_at).total_seconds())
            call.language = state.get("language", "en")
            data = dict(call.extracted_data or {})
            data.update(state.get("entities", {}))
            if reason:
                data["end_reason"] = reason
            call.extracted_data = data
            if call.outcome == CallOutcome.in_progress:
                call.outcome = (CallOutcome.escalated
                                if reason in ("too_many_unclear",) else CallOutcome(outcome)
                                if outcome in CallOutcome._value2member_map_ else CallOutcome.resolved)
            await db.commit()
    except Exception as e:
        print(f"[agent] close_call error: {type(e).__name__}: {e}")


# ── Backwards-compatible alias used by the LiveKit webhook + room watcher ─────
async def run_agent_in_room(room_name: str, behavior_config: dict | None = None,
                            call_id: str | None = None):
    await run_clinic_agent(room_name, behavior_config, call_id)
