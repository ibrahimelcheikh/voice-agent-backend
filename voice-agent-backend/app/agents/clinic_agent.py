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
import uuid
from datetime import datetime, date

from app.core.config import settings
from app.agents.guardrail import GuardrailBrain

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
    """Deepgram STT when a key + plugin are available, else OpenAI Whisper (multilingual)."""
    if settings.DEEPGRAM_API_KEY:
        try:
            from livekit.plugins import deepgram
            return deepgram.STT(api_key=settings.DEEPGRAM_API_KEY)
        except Exception as e:
            print(f"[agent] Deepgram unavailable ({type(e).__name__}: {e}); using OpenAI Whisper")
    from livekit.plugins import openai
    # detect_language=True so the caller can speak EN/AR/FR/ES.
    return openai.STT(model="whisper-1", detect_language=True, api_key=settings.OPENAI_API_KEY)


def _build_session(behavior_config: dict):
    from livekit.agents import AgentSession
    from livekit.plugins import openai, silero

    voice = behavior_config.get("voice_id") or "shimmer"
    return AgentSession(
        # Silero VAD with a 0.6s stop window -> natural turn detection / endpointing.
        vad=silero.VAD.load(min_silence_duration=0.6),
        stt=_build_stt(),
        llm=openai.LLM(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY),
        # gpt-4o-mini-tts is multilingual — same voice speaks the LLM's reply language.
        tts=openai.TTS(model="gpt-4o-mini-tts", voice=voice, api_key=settings.OPENAI_API_KEY),
        allow_interruptions=True,   # barge-in: caller speech stops TTS immediately
    )


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
            try:
                await self.session.say(GREETING, allow_interruptions=True)
            except Exception as e:
                print(f"[agent] greeting error: {type(e).__name__}: {e}")

        async def on_user_turn_completed(self, turn_ctx, new_message):
            """Guardrail: classify -> fetch real data -> inject a strict instruction
            BEFORE the LLM responds. The LLM may only state what we provide here."""
            user_text = (new_message.text_content or "").strip()
            if not user_text:
                return
            last_assistant = self._last_assistant(turn_ctx)
            decision = await self._brain.decide(user_text, last_assistant)
            if self._on_state:
                self._on_state(self._brain.snapshot())
            # Strict per-turn instruction with ONLY the real DB data.
            turn_ctx.add_message(role="system", content=decision["instruction"])
            if decision.get("end") and self._on_end:
                asyncio.create_task(self._on_end(decision["end"]))

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
    instructions = (behavior_config or {}).get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    agent = _make_agent_class()(instructions=instructions, on_state=on_state, on_end=on_end)

    room.on("disconnected", lambda *_a: done.set())

    await session.start(agent=agent, room=room, room_input_options=RoomInputOptions())
    print(f"[agent] session started in room {getattr(room, 'name', '?')}")

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
