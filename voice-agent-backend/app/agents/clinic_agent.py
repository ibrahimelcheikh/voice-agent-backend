"""
Clinic receptionist voice agent — native livekit-agents AgentSession (1.x).

Flow:  Twilio (SIP) -> LiveKit SIP trunk -> `call-<random>` room -> this agent joins.

Why AgentSession (not a raw Pipecat transport): livekit-agents' AgentSession is the
proven path for actually connecting to a LiveKit room — it wires Silero VAD + STT +
LLM + TTS with built-in turn detection and barge-in, and joins the room via the
framework. The anti-hallucination guardrail is preserved by overriding
`on_user_turn_completed`: after the caller's turn is transcribed (and before the LLM
responds) we classify intent, fetch REAL data from the DB via GuardrailBrain, and
inject a strict instruction so the LLM may ONLY state that data.

The dedicated worker is the ONLY agent-spawn path:
  * entrypoint(ctx)              — dedicated worker (agent_worker.py); uses ctx.connect()
The web service spawns no agents, so exactly one agent answers each call.

`run_agent_in_room(room,...)` remains as a manual/standalone utility (connects a
livekit.rtc.Room directly) but is no longer wired to any in-process trigger. It
includes a cross-process guard so it never double-joins a room the worker is in.
"""
import asyncio
import os
import uuid
from datetime import datetime, date

from app.core.config import settings
from app.agents.guardrail import GuardrailBrain


def _log(msg: str) -> None:
    """Single logging surface so every pipeline step is visible in Railway logs.
    flush=True so lines appear immediately even under buffered stdout."""
    print(f"[agent] {msg}", flush=True)


# Plugins (Deepgram/Cartesia/OpenAI) read their keys from the environment. The
# dedicated worker sets these, but the in-process path may import this module first;
# export them here too so a TTS/STT plugin always finds its key regardless of entry
# point. Only non-empty values are set so real Railway env vars are never clobbered.
for _k, _v in {
    "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    "DEEPGRAM_API_KEY": settings.DEEPGRAM_API_KEY,
    "CARTESIA_API_KEY": settings.CARTESIA_API_KEY,
}.items():
    if _v and not os.environ.get(_k):
        os.environ[_k] = _v

# Unique-per-process agent identity. Every agent participant identity starts with
# "clinic-agent" so the double-join guard can detect an agent that is already in a
# room, while the random suffix keeps each worker instance distinct.
AGENT_IDENTITY_PREFIX = "clinic-agent"
_WORKER_ID = uuid.uuid4().hex[:8]
AGENT_IDENTITY = f"{AGENT_IDENTITY_PREFIX}-{_WORKER_ID}"

DEFAULT_SYSTEM_PROMPT = (
    "You are a clinic receptionist AI. You may ONLY state information provided to you in "
    "the function results. NEVER invent appointment times, prices, doctor names, or policies. "
    "If you don't have the data, offer to connect to staff. Keep responses under 2 sentences. "
    "Be warm and professional."
)
GREETING = (
    "Thank you for calling Prime Health Clinic. This is the AI assistant, how may I help you?"
)

# Rooms handled in THIS process — guards the webhook and room watcher against a
# double-join into the same room.
_active_rooms: set[str] = set()


def generate_agent_token(room_name: str) -> str:
    from livekit import api
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(AGENT_IDENTITY)
        .with_name("Clinic Assistant")
        .with_grants(api.VideoGrants(
            room_join=True, room=room_name, can_publish=True, can_subscribe=True))
    )
    return token.to_jwt()


async def _agent_already_in_room(room_name: str) -> bool:
    """True if a participant whose identity starts with the agent prefix is already
    in the room. Cross-process double-join guard: prevents a second agent (e.g. the
    dedicated worker AND a stray in-process join) from both answering one call."""
    try:
        from livekit import api as lkapi
        lk = lkapi.LiveKitAPI(
            url=settings.LIVEKIT_URL.replace("wss://", "https://"),
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
        try:
            res = await lk.room.list_participants(
                lkapi.ListParticipantsRequest(room=room_name))
            return any((p.identity or "").startswith(AGENT_IDENTITY_PREFIX)
                       for p in res.participants)
        finally:
            await lk.aclose()
    except Exception as e:
        print(f"[agent] participant check failed: {type(e).__name__}: {e}")
        return False


def _build_stt():
    """Streaming Deepgram STT (real-time, built for live calls) when a key + plugin are
    available, else the fastest available OpenAI Whisper config. Deepgram is strongly
    recommended — Whisper is batch (not streaming) and is the main STT latency source."""
    if settings.DEEPGRAM_API_KEY:
        try:
            from livekit.plugins import deepgram
            _log(f"STT: Deepgram {settings.DEEPGRAM_STT_MODEL} (streaming, multi, endpointing=300ms)")
            return deepgram.STT(
                model=settings.DEEPGRAM_STT_MODEL or "nova-2-general",
                language="multi",          # caller may speak en/ar/fr/es
                interim_results=True,       # partials stream as the caller talks
                punctuate=True,
                smart_format=True,
                endpointing_ms=300,         # fast end-of-speech detection
                api_key=settings.DEEPGRAM_API_KEY,
            )
        except Exception as e:
            _log(f"Deepgram STT unavailable ({type(e).__name__}: {e}); falling back to Whisper")
    from livekit.plugins import openai
    # No Deepgram key/plugin -> fastest Whisper we can. NOTE: whisper-1 is BATCH, not
    # streaming; Deepgram is strongly recommended to cut STT latency.
    _log("STT: OpenAI Whisper-1 (BATCH fallback — set DEEPGRAM_API_KEY for streaming/low latency)")
    return openai.STT(model="whisper-1", detect_language=True, api_key=settings.OPENAI_API_KEY)


def _build_tts(behavior_config: dict):
    """Pick the fastest available streaming TTS.

    Order honours TTS_PROVIDER: Deepgram aura (lowest latency, ENGLISH-ONLY) by default,
    Cartesia sonic (fast AND multilingual — use for ar/fr/es callers), else OpenAI
    gpt-4o-mini-tts (multilingual but slow). Each tier degrades gracefully to the next."""
    provider = (settings.TTS_PROVIDER or "deepgram").lower()
    voice = behavior_config.get("voice_id") or "shimmer"

    if provider == "cartesia" and settings.CARTESIA_API_KEY:
        try:
            from livekit.plugins import cartesia
            kwargs = {"model": settings.CARTESIA_TTS_MODEL or "sonic-2",
                      "api_key": settings.CARTESIA_API_KEY}
            if settings.CARTESIA_VOICE:
                kwargs["voice"] = settings.CARTESIA_VOICE
            _log(f"TTS: Cartesia {kwargs['model']} (streaming, multilingual)")
            return cartesia.TTS(**kwargs)
        except Exception as e:
            _log(f"Cartesia TTS unavailable ({type(e).__name__}: {e}); trying Deepgram")

    if provider in ("deepgram", "cartesia") and settings.DEEPGRAM_API_KEY:
        try:
            from livekit.plugins import deepgram
            _log(f"TTS: Deepgram {settings.DEEPGRAM_TTS_MODEL} (streaming, ENGLISH-ONLY — "
                 "non-English replies will be mispronounced; switch TTS_PROVIDER=cartesia for ar/fr/es)")
            return deepgram.TTS(model=settings.DEEPGRAM_TTS_MODEL or "aura-asteria-en",
                                api_key=settings.DEEPGRAM_API_KEY)
        except Exception as e:
            _log(f"Deepgram TTS unavailable ({type(e).__name__}: {e}); falling back to OpenAI")

    from livekit.plugins import openai
    _log("TTS: OpenAI gpt-4o-mini-tts (multilingual fallback — slower)")
    return openai.TTS(model="gpt-4o-mini-tts", voice=voice, api_key=settings.OPENAI_API_KEY)


def _build_turn_detection():
    """Optional end-of-utterance (EOU) model for sharper, faster turn-taking than VAD
    alone. Multilingual model matches the clinic's en/ar/fr/es. Degrades gracefully to
    pure VAD endpointing when livekit-plugins-turn-detector / its model isn't installed."""
    try:
        from livekit.plugins.turn_detector.multilingual import MultilingualModel
        _log("turn detection: MultilingualModel (EOU)")
        return MultilingualModel()
    except Exception as e:
        _log(f"turn_detector unavailable ({type(e).__name__}: {e}); using VAD endpointing")
        return None


def _build_session(behavior_config: dict):
    from livekit.agents import AgentSession
    from livekit.plugins import openai, silero

    session_kwargs = dict(
        # Tight VAD windows -> fast endpointing without clipping the caller.
        vad=silero.VAD.load(min_silence_duration=0.3, min_speech_duration=0.1),
        stt=_build_stt(),
        # AgentSession streams LLM tokens straight into the TTS as they generate.
        llm=openai.LLM(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY),
        tts=_build_tts(behavior_config),
        allow_interruptions=True,        # barge-in: caller speech stops TTS immediately
        min_endpointing_delay=0.5,       # don't cut the caller off mid-thought
        max_endpointing_delay=3.0,       # but never hang waiting forever
        preemptive_generation=True,      # LLM starts before the caller fully stops
    )
    td = _build_turn_detection()
    if td is not None:
        session_kwargs["turn_detection"] = td
    return AgentSession(**session_kwargs)


def _wire_session_logging(session) -> None:
    """Log every pipeline step (Railway) so a stall is visible: STT result, LLM/assistant
    message, agent speaking (TTS), and pipeline errors. Bound defensively so an unknown
    event name on a future plugin version can never crash the agent."""
    def _bind(name, fn):
        try:
            session.on(name, fn)
        except Exception as e:
            _log(f"could not bind event {name!r}: {e}")

    _bind("agent_state_changed",
          lambda ev: _log(f"agent_state -> {getattr(ev, 'new_state', ev)}"))  # 'speaking' = TTS playing
    _bind("user_state_changed",
          lambda ev: _log(f"user_state -> {getattr(ev, 'new_state', ev)}"))
    _bind("user_input_transcribed",
          lambda ev: _log(f"STT: {getattr(ev, 'transcript', '')!r} final={getattr(ev, 'is_final', '?')}"))
    _bind("conversation_item_added",
          lambda ev: _log(f"msg: role={getattr(getattr(ev, 'item', None), 'role', '?')} "
                          f"text={getattr(getattr(ev, 'item', None), 'text_content', '')!r}"))
    _bind("error", lambda ev: _log(f"session error: {getattr(ev, 'error', ev)}"))


def _make_agent_class():
    """Build the Agent subclass lazily so livekit-agents imports stay lazy."""
    from livekit.agents import Agent

    class ClinicAgent(Agent):
        def __init__(self, *, instructions, on_state=None, on_end=None):
            super().__init__(instructions=instructions)
            self._brain = GuardrailBrain(openai_api_key=settings.OPENAI_API_KEY,
                                         today=date.today().isoformat())
            self._on_state = on_state
            self._on_end = on_end

        async def on_enter(self):
            # Brief pause so the agent's audio track is fully published/subscribed
            # before we speak — otherwise the first word(s) of the greeting get cut.
            # session.say() with a fixed string is more reliable/instant than
            # generate_reply() for a known greeting.
            try:
                await asyncio.sleep(0.3)
                _log("greeting: speaking")
                await self.session.say(GREETING, allow_interruptions=True)
                _log("greeting: done")
            except Exception as e:
                _log(f"greeting error: {type(e).__name__}: {e}")

        async def on_user_turn_completed(self, turn_ctx, new_message):
            """Guardrail: classify -> fetch real data -> inject a strict instruction
            BEFORE the LLM responds. The LLM may only state what we provide here.
            Wrapped so an STT/classify/DB failure recovers (ask to repeat) instead of
            leaving the caller in silence."""
            user_text = (new_message.text_content or "").strip()
            _log(f"STT (final, user said): {user_text!r}")
            if not user_text:
                return
            try:
                last_assistant = self._last_assistant(turn_ctx)
                decision = await self._brain.decide(user_text, last_assistant)
                if self._on_state:
                    self._on_state(self._brain.snapshot())
                # Strict per-turn instruction with ONLY the real DB data.
                turn_ctx.add_message(role="system", content=decision["instruction"])
                _log(f"guardrail: intent={decision.get('intent')} end={decision.get('end')}")
                if decision.get("end") and self._on_end:
                    asyncio.create_task(self._on_end(decision["end"]))
            except Exception as e:
                _log(f"turn handling error: {type(e).__name__}: {e}; asking caller to repeat")
                turn_ctx.add_message(role="system", content=(
                    "There was a brief technical issue understanding the caller. Apologise in one "
                    "short sentence and ask them to please repeat what they said."))

        @staticmethod
        def _last_assistant(turn_ctx) -> str:
            for item in reversed(getattr(turn_ctx, "items", [])):
                if getattr(item, "type", None) == "message" and getattr(item, "role", None) == "assistant":
                    return (item.text_content or "").strip()
            return ""

    return ClinicAgent


async def _serve(room, behavior_config, call_id, started_at, *, is_worker):
    """Build the session + guarded agent, start it on the (already-connected) room,
    and run until the call ends (caller hangs up, agent ends it, or max duration)."""
    from livekit.agents import RoomInputOptions

    max_duration = int((behavior_config or {}).get("max_call_duration") or 300)  # 5 min cap
    state = {"language": "en", "entities": {}}
    end_reason = {"r": None}
    done = asyncio.Event()

    async def on_end(reason: str):
        if end_reason["r"]:
            return
        end_reason["r"] = reason
        print(f"[agent] ending call ({reason}) — letting goodbye play")
        await asyncio.sleep(5)   # let the goodbye/transfer line finish speaking
        done.set()

    def on_state(snap: dict):
        state.update(snap)

    session = _build_session(behavior_config or {})
    _wire_session_logging(session)
    instructions = (behavior_config or {}).get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    agent = _make_agent_class()(instructions=instructions, on_state=on_state, on_end=on_end)

    room.on("disconnected", lambda *_a: done.set())

    await session.start(agent=agent, room=room, room_input_options=RoomInputOptions())
    _log(f"session started in room {getattr(room, 'name', '?')}")

    try:
        await asyncio.wait_for(done.wait(), timeout=max_duration)
    except asyncio.TimeoutError:
        end_reason["r"] = end_reason["r"] or "max_duration_reached"

    try:
        await session.aclose()
    except Exception:
        pass
    if not is_worker:
        try:
            await room.disconnect()
        except Exception:
            pass
    await _close_call(call_id, state, end_reason["r"] or "completed", started_at)


# ── Entry point 1: dedicated worker (livekit-agents dispatches a job) ─────────
async def entrypoint(ctx):
    from livekit.agents import AutoSubscribe
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    room_name = ctx.room.name

    # Double-join guard: if another agent participant is already in this room, bail
    # out so only one agent ever answers a call.
    others = [p for p in ctx.room.remote_participants.values()
              if (getattr(p, "identity", "") or "").startswith(AGENT_IDENTITY_PREFIX)]
    if others:
        print(f"[worker] agent already in {room_name} ({others[0].identity}); skipping join")
        await ctx.room.disconnect()
        return

    print(f"[worker] connected to room {room_name} as {AGENT_IDENTITY}")
    agent_row, behavior_config = await _load_behavior()
    call_id = await _create_call_record(agent_row, room_name, None)
    await _serve(ctx.room, behavior_config, call_id, datetime.utcnow(), is_worker=True)


# ── Entry point 2: in-process (room watcher / LiveKit webhook) ────────────────
async def run_agent_in_room(room_name: str, behavior_config: dict | None = None,
                            call_id: str | None = None):
    """Join a LiveKit room and run the clinic agent until the call ends. Never raises.
    Idempotent per room within this process."""
    if room_name in _active_rooms:
        return
    # Cross-process double-join guard: don't join if an agent is already in the room
    # (e.g. the dedicated worker has already answered this call).
    if await _agent_already_in_room(room_name):
        print(f"[agent] agent already present in {room_name}; not joining")
        return
    _active_rooms.add(room_name)
    try:
        from livekit import rtc
        room = rtc.Room()
        await room.connect(settings.LIVEKIT_URL, generate_agent_token(room_name))
        print(f"[agent] connected to room {room_name} as {AGENT_IDENTITY}")
        await _serve(room, behavior_config or {}, call_id, datetime.utcnow(), is_worker=False)
    except Exception as e:
        print(f"[agent] error in room {room_name}: {type(e).__name__}: {e}")
    finally:
        _active_rooms.discard(room_name)


# ── Shared DB helpers ─────────────────────────────────────────────────────────

async def _load_behavior():
    """Active inbound agent + its behavior lock config (best effort)."""
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
                    return agent, {"system_prompt": cfg.system_prompt,
                                   "voice_id": agent.voice_id,
                                   "max_call_duration": cfg.max_call_duration}
            return agent, {}
    except Exception as e:
        print(f"[agent] behavior load failed: {type(e).__name__}: {e}")
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
        print(f"[agent] call record create failed: {type(e).__name__}: {e}")
        return None


async def _close_call(call_id, state, reason, started_at):
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
            data["end_reason"] = reason
            call.extracted_data = data
            if call.outcome == CallOutcome.in_progress:
                call.outcome = (CallOutcome.escalated if reason == "too_many_unclear"
                                else CallOutcome.resolved)
            await db.commit()
    except Exception as e:
        print(f"[agent] close_call error: {type(e).__name__}: {e}")
