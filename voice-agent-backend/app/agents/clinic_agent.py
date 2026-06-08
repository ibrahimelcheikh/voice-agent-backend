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
import logging
import os
import sys
import time
import uuid
from datetime import datetime, date

from app.core.config import settings
from app.agents.guardrail import GuardrailBrain

# Emoji-laden logs must not crash a Windows cp1252 console (Railway is Linux — fine).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# INFO-level logging surfaces both our pipeline logs AND livekit-agents' own internal
# logs (STT/LLM/TTS activity, errors) in the Railway log stream.
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("clinic-agent")
logger.setLevel(logging.INFO)


def _log(msg: str) -> None:
    """Single logging surface so every pipeline step is visible in Railway logs."""
    logger.info(msg)


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
    "You are a clinic receptionist AI on a PHONE call. You may ONLY state information provided "
    "to you in the function results. NEVER invent appointment times, prices, doctor names, or "
    "policies. When a patient says a relative date like 'next Monday' or 'tomorrow', the actual "
    "calendar date is computed for you — confirm it back and NEVER ask them for a specific "
    "calendar date. Keep every response to ONE short sentence, maximum 15 words. Never list more "
    "than 2 items; if listing services or insurance providers, say only the top 2-3 then ask if "
    "they want more. Be brief and natural, like a real receptionist. If you don't have the data, "
    "offer to connect to staff."
)
GREETING = (
    "Thank you for calling Prime Health Clinic. This is the AI assistant, how may I help you?"
)

# Outbound reminder calls open with this script instead of the inbound greeting. The
# system prompt still forbids inventing any detail — only the real appointment data
# (passed in via call_context) may be spoken.
REMINDER_SYSTEM_PROMPT = (
    "You are a clinic receptionist AI on an OUTBOUND reminder PHONE call: YOU called the "
    "patient to remind them of an upcoming appointment. You may ONLY state the appointment "
    "details provided to you in the function results — NEVER invent appointment times, "
    "prices, doctor names, or policies. The patient may confirm, reschedule, or cancel; "
    "handle whichever they choose. Keep every response to ONE short sentence, maximum 15 "
    "words, warm and natural like a real receptionist. If they want something you don't "
    "have data for, offer to connect them to staff."
)


def build_reminder_greeting(ctx: dict) -> str:
    """First line the agent speaks on an outbound reminder call, built from the REAL
    appointment data (no invented details)."""
    doctor = ctx.get("doctor_name")
    when_date = ctx.get("date_human") or ctx.get("date") or ""
    when_time = ctx.get("time_human") or ctx.get("time") or ""
    with_doctor = f" with {doctor}" if doctor else ""
    when = ""
    if when_date:
        when = f" on {when_date}"
        if when_time:
            when += f" at {when_time}"
    elif when_time:
        when = f" at {when_time}"
    return (
        "Hello, this is the AI assistant from Prime Health Clinic calling to remind you of "
        f"your appointment{with_doctor}{when}. "
        "Would you like to confirm, reschedule, or cancel?"
    )


# ── Phase 3a: language selection (English names; Arabic-voiced prompt comes later) ──
_LANG_NAMES_EN = {"en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish"}


def _normalize_languages(raw) -> list[str]:
    """Tenant's supported language codes, normalized (lowercase 2-letter, de-duped, order
    preserved). The FIRST entry is the PRIMARY/default language. Always non-empty (falls
    back to ['en']) so the flow is English-safe even for a misconfigured tenant."""
    langs: list[str] = []
    for x in (raw or ["en"]):
        c = str(x).strip().lower()[:2]
        if c and c not in langs:
            langs.append(c)
    return langs or ["en"]


def _build_language_prompt(business_name: str | None, languages: list[str]) -> str:
    """Short bilingual keypad prompt, e.g. 'Welcome to Golden Fork. For English, press 1.
    For Arabic, press 2.' Spoken with the current (English) TTS in this phase — an
    Arabic-voiced prompt comes in 3b. Digit N maps to the Nth supported language."""
    parts = [f"Welcome to {business_name}." if business_name else "Welcome."]
    for i, lang in enumerate(languages):
        parts.append(f"For {_LANG_NAMES_EN.get(lang, lang)}, press {i + 1}.")
    return " ".join(parts)


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
            _log(f"STT: Deepgram {settings.DEEPGRAM_STT_MODEL} (streaming, multi, endpointing=500ms)")
            # NOTE: the plugin sends Deepgram KeepAlive frames itself and treats a
            # silence-timeout socket close as a *recoverable* STTError (it reconnects) —
            # there is no `keepalive` kwarg to pass. endpointing_ms=500 waits a touch
            # longer before declaring end-of-speech so the caller isn't cut off.
            return deepgram.STT(
                model=settings.DEEPGRAM_STT_MODEL or "nova-2-general",
                language="multi",          # caller may speak en/ar/fr/es
                interim_results=True,       # partials stream as the caller talks
                punctuate=True,
                smart_format=True,
                no_delay=True,             # emit finals promptly, don't buffer
                endpointing_ms=500,         # wait ~0.5s of silence before end-of-speech
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


# ── Phase 3b: Arabic (MSA) generation + TTS, gated on the selected language ──────────
# The base system prompt, guardrail, intent classification, entity extraction, and ALL
# database content stay ENGLISH (one source of truth). This single instruction is appended
# AFTER the guardrail's per-turn instruction ONLY on the Arabic branch, so the LLM renders
# just its FINAL SPOKEN reply in Modern Standard Arabic. It never alters facts or the prompt.
ARABIC_OUTPUT_INSTRUCTION = (
    "IMPORTANT — SPOKEN LANGUAGE: The caller selected Arabic. Produce your spoken reply ONLY "
    "in Modern Standard Arabic (الفصحى) — never a regional dialect. Translate the meaning of "
    "your reply into natural, correct MSA. Render proper nouns and menu/item/doctor names "
    "naturally within the Arabic sentence (do not force transliteration). Do NOT change any "
    "fact, number, price, name, date, or time — only the language of the spoken reply changes."
)


def _arabic_greeting(business_name: str | None) -> str:
    """Short MSA greeting, equivalent in meaning to the English one. The (English) business
    name is rendered naturally inside the Arabic sentence."""
    if business_name:
        return f"مرحباً بكم في {business_name}. أنا المساعد الآلي، كيف يمكنني مساعدتكم اليوم؟"
    return "مرحباً بكم. أنا المساعد الآلي، كيف يمكنني مساعدتكم اليوم؟"


def _build_cartesia_ar_tts():
    """Per-call Cartesia TTS for Arabic (MSA), or None when Arabic TTS isn't available — in
    which case the agent safely keeps the English Deepgram path (and English generation).

    sonic-2 does NOT support Arabic, so CARTESIA_AR_MODEL (default sonic-3.5) is used with
    language='ar'. Cartesia REQUIRES a voice id and we never guess one: if CARTESIA_AR_VOICE
    is unset (or no key/plugin), this returns None and Arabic callers fall back to English."""
    if not settings.CARTESIA_API_KEY:
        _log("Arabic TTS: no CARTESIA_API_KEY — Arabic callers fall back to the English path")
        return None
    if not settings.CARTESIA_AR_VOICE:
        _log("Arabic TTS: CARTESIA_AR_VOICE not set — NOT guessing a voice id; Arabic callers "
             "fall back to English until a confirmed MSA voice id is configured")
        return None
    try:
        from livekit.plugins import cartesia
        model = settings.CARTESIA_AR_MODEL or "sonic-3.5"
        _log(f"Arabic TTS: Cartesia {model} language=ar voice={settings.CARTESIA_AR_VOICE}")
        return cartesia.TTS(model=model, language="ar", voice=settings.CARTESIA_AR_VOICE,
                            api_key=settings.CARTESIA_API_KEY)
    except Exception as e:
        _log(f"Arabic TTS unavailable ({type(e).__name__}: {e}); Arabic callers fall back to English")
        return None


def _build_whisper_ar_stt():
    """Per-call OpenAI Whisper STT for the Arabic branch (Phase 3b fix). Deepgram
    language='multi' romanizes Arabic audio into nonsense English (so every turn is
    intent=unclear); Whisper transcribes Arabic strongly, so the Arabic branch uses
    whisper-1 with language='ar'. Whisper is non-streaming (chunked) — it is wrapped with
    the framework's VAD StreamAdapter at use time, which is the plugin's standard handling.

    Uses the already-configured OPENAI_API_KEY (the LLM provider) — no new credential. The
    OpenAI STT plugin is already imported here for the Whisper fallback in _build_stt, so no
    new dependency. Returns None on failure (the Arabic call then keeps Deepgram, logged)."""
    try:
        from livekit.plugins import openai
        _log("Arabic STT: OpenAI Whisper-1 (language=ar, VAD-chunked)")
        return openai.STT(model="whisper-1", language="ar", api_key=settings.OPENAI_API_KEY)
    except Exception as e:
        _log(f"Arabic STT unavailable ({type(e).__name__}: {e}); Arabic call keeps Deepgram multi")
        return None


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
    import httpx
    from livekit.agents import AgentSession
    from livekit.plugins import openai, silero

    # Cap the LLM call so a hung request can't leave the caller in silence — it surfaces
    # as an error the session recovers from instead of awaiting forever.
    llm_timeout = httpx.Timeout(20.0, connect=5.0)

    session_kwargs = dict(
        # Tight VAD windows -> fast endpointing without clipping the caller.
        vad=silero.VAD.load(min_silence_duration=0.3, min_speech_duration=0.1),
        stt=_build_stt(),
        # AgentSession streams LLM tokens straight into the TTS as they generate.
        llm=openai.LLM(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, timeout=llm_timeout),
        tts=_build_tts(behavior_config),
        allow_interruptions=True,        # barge-in: caller speech stops TTS immediately
        min_endpointing_delay=0.8,       # wait longer so the caller isn't cut off mid-sentence
        max_endpointing_delay=4.0,       # but never hang waiting forever
        preemptive_generation=True,      # LLM starts before the caller fully stops
    )
    td = _build_turn_detection()
    if td is not None:
        session_kwargs["turn_detection"] = td
    return AgentSession(**session_kwargs)


def _wire_session_logging(session) -> None:
    """Log every pipeline stage to the Railway stream so a stall is visible end-to-end:
    who's speaking, STT results, committed messages, per-stage latency (EOU / LLM TTFT /
    TTS TTFB via metrics), and errors. On a pipeline error, best-effort speak an apology
    so the caller is never left in silence. Event names verified against livekit-agents
    1.5.17 (user_state_changed / agent_state_changed / user_input_transcribed /
    conversation_item_added / metrics_collected / error)."""
    from livekit.agents import metrics as lk_metrics

    @session.on("user_state_changed")
    def _on_user_state(ev):
        st = getattr(ev, "new_state", None)
        if st == "speaking":
            logger.info("🎤 USER STARTED SPEAKING")
        elif st == "listening":
            logger.info("🛑 USER STOPPED SPEAKING")
        else:
            logger.info("user_state -> %s", st)

    @session.on("agent_state_changed")
    def _on_agent_state(ev):
        st = getattr(ev, "new_state", None)
        if st == "thinking":
            logger.info("🤔 AGENT THINKING (LLM)")
        elif st == "speaking":
            logger.info("🔊 AGENT STARTED SPEAKING (TTS)")
        elif st == "listening":
            logger.info("✅ AGENT STOPPED SPEAKING")
        else:
            logger.info("agent_state -> %s", st)

    @session.on("user_input_transcribed")
    def _on_transcript(ev):
        final = getattr(ev, "is_final", False)
        text = getattr(ev, "transcript", "")
        logger.info("📝 STT %s: %r", "FINAL" if final else "interim", text)

    @session.on("conversation_item_added")
    def _on_item(ev):
        item = getattr(ev, "item", None)
        role = getattr(item, "role", "?")
        text = getattr(item, "text_content", "")
        icon = "💬" if role == "assistant" else "🗣️"
        logger.info("%s %s: %r", icon, role, text)

    @session.on("metrics_collected")
    def _on_metrics(ev):
        m = getattr(ev, "metrics", None)
        if m is None:
            return
        # Full formatted line (all fields) for deep inspection...
        try:
            lk_metrics.log_metrics(m, logger=logger)
        except Exception:
            pass
        # ...plus a compact, greppable latency line for the stages that matter.
        t = getattr(m, "type", "")
        if t == "eou_metrics":
            logger.info("⏱️ EOU: end_of_utterance=%.0fms transcription=%.0fms guardrail(on_user_turn)=%.0fms",
                        _ms(getattr(m, "end_of_utterance_delay", 0)),
                        _ms(getattr(m, "transcription_delay", 0)),
                        _ms(getattr(m, "on_user_turn_completed_delay", 0)))
        elif t == "llm_metrics":
            logger.info("⏱️ LLM: ttft=%.0fms total=%.0fms tok/s=%.1f",
                        _ms(getattr(m, "ttft", 0)), _ms(getattr(m, "duration", 0)),
                        getattr(m, "tokens_per_second", 0) or 0)
        elif t == "tts_metrics":
            logger.info("⏱️ TTS: ttfb=%.0fms total=%.0fms audio=%.0fms",
                        _ms(getattr(m, "ttfb", 0)), _ms(getattr(m, "duration", 0)),
                        _ms(getattr(m, "audio_duration", 0)))
        elif t == "stt_metrics":
            logger.info("⏱️ STT: duration=%.0fms audio=%.0fms",
                        _ms(getattr(m, "duration", 0)), _ms(getattr(m, "audio_duration", 0)))

    _spoke_fallback = {"t": 0.0}

    @session.on("error")
    def _on_error(ev):
        err = getattr(ev, "error", ev)
        recoverable = getattr(err, "recoverable", False)
        logger.error("❌ SESSION ERROR (recoverable=%s): %s", recoverable, err)
        # Recoverable errors (e.g. Deepgram closing the socket after silence — it
        # reconnects) must NOT trigger a spoken prompt, or the agent says "could you
        # repeat that?" unprompted when the caller simply went quiet.
        if recoverable:
            return
        # Only on a genuine unrecoverable failure: best-effort audible recovery,
        # debounced so we don't spam on a burst of errors.
        now = time.monotonic()
        if now - _spoke_fallback["t"] < 8:
            return
        _spoke_fallback["t"] = now
        try:
            asyncio.create_task(session.say("I'm sorry, could you repeat that?",
                                            allow_interruptions=True))
        except Exception as e:
            logger.error("could not speak error fallback: %s", e)

    @session.on("close")
    def _on_close(ev):
        logger.info("🔚 session closed")


def _ms(v) -> float:
    """Seconds (float) -> milliseconds; tolerate None/non-numeric."""
    try:
        return float(v) * 1000.0
    except (TypeError, ValueError):
        return 0.0


def _make_agent_class():
    """Build the Agent subclass lazily so livekit-agents imports stay lazy."""
    from livekit.agents import Agent

    class ClinicAgent(Agent):
        def __init__(self, *, instructions, on_state=None, on_end=None, greeting=None,
                     seed_entities=None, pending_intent=None, tenant_id=None, niche=None,
                     language_prompt=None, languages=None, dtmf_event=None, dtmf_holder=None,
                     ar_tts=None, ar_greeting=None, ar_stt=None):
            super().__init__(instructions=instructions)
            # Outbound reminder calls seed the brain with the appointment context
            # (appointment_id, phone) and a pending confirm intent so a bare "yes"
            # confirms the right appointment and reschedule/cancel target it directly.
            # tenant_id scopes every data function to this caller's business; niche selects
            # which function set + intents are loaded (clinic -> appointments, restaurant ->
            # reservations/orders, real_estate/automotive/services -> lead capture).
            self._brain = GuardrailBrain(openai_api_key=settings.OPENAI_API_KEY,
                                         today=date.today().isoformat(),
                                         seed_entities=seed_entities,
                                         pending_intent=pending_intent,
                                         tenant_id=tenant_id, niche=niche)
            self._on_state = on_state
            self._on_end = on_end
            self._greeting = greeting or GREETING
            # Phase 3a language selection (multi-language inbound only). The prompt + a
            # shared DTMF event/holder are wired up in _serve; absent for single-language
            # tenants and outbound reminders, in which case selection is skipped entirely.
            self._language_prompt = language_prompt
            self._languages = languages or ["en"]
            self._dtmf_event = dtmf_event
            self._dtmf_holder = dtmf_holder if dtmf_holder is not None else {}
            self._call_language = None   # set by _select_language (Phase 3a)
            # Phase 3b: Arabic path is gated on BOTH the selected language == "ar" AND an
            # available Arabic TTS. self._arabic is the single decided flag (set in on_enter)
            # consumed by tts_node + on_user_turn_completed. None ar_tts -> English path.
            self._ar_tts = ar_tts
            self._ar_greeting = ar_greeting
            self._ar_stt = ar_stt   # Phase 3b fix: Whisper STT used on the Arabic branch only
            self._arabic = False

        async def on_enter(self):
            # Brief pause so the agent's audio track is fully published/subscribed
            # before we speak — otherwise the first word(s) get cut.
            try:
                await asyncio.sleep(0.3)
                # Phase 3a: offer the keypad language menu BEFORE the greeting (no-op for
                # single-language tenants / reminders). Stores + logs the chosen language.
                await self._select_language()
                # Phase 3b: decide the Arabic branch — gated on the selected language being
                # "ar" AND an available Arabic TTS. When false, EVERYTHING below is today's
                # English path byte-for-byte (Deepgram TTS, English greeting/generation).
                self._arabic = (self._call_language == "ar") and (self._ar_tts is not None)
                if self._call_language == "ar" and self._ar_tts is None:
                    _log("[AGENT] Arabic selected but no Arabic TTS configured "
                         "(CARTESIA_AR_VOICE unset) — using English Deepgram + English generation")
                _log(f"[AGENT] TTS for this call = "
                     f"{'cartesia (ar)' if self._arabic else 'deepgram (' + (self._call_language or 'en') + ')'}")
                _log(f"[AGENT] STT for this call = "
                     f"{'whisper (ar)' if (self._arabic and self._ar_stt is not None) else 'deepgram (multi)'}")
                # session.say() with a fixed string is more reliable/instant than
                # generate_reply() for a known greeting. For outbound reminders this is the
                # reminder script; for inbound it's the standard greeting (English, or MSA on
                # the Arabic branch). tts_node routes the audio to the right engine.
                greeting = self._ar_greeting if (self._arabic and self._ar_greeting) else self._greeting
                _log("greeting: speaking")
                await self.session.say(greeting, allow_interruptions=True)
                _log("greeting: done")
            except Exception as e:
                _log(f"greeting error: {type(e).__name__}: {e}")

        async def _select_language(self):
            """Phase 3a — brief bilingual prompt + keypad (DTMF) language capture, run BEFORE
            the greeting. Stores the chosen code on self._call_language and LOGS it. It NEVER
            branches behaviour on the value — the greeting / LLM / TTS below are byte-for-byte
            today's English flow (Arabic generation arrives in 3b).

            Multi-language tenants only; for a single-language tenant (no prompt) it just
            records the primary language and returns — no keypad step at all. A missed
            keypress (timeout) or an invalid digit defaults to the PRIMARY (first) language;
            the call is never blocked or dropped waiting for a key."""
            languages = self._languages or ["en"]
            primary = languages[0]
            if not self._language_prompt or len(languages) < 2:
                self._call_language = primary
                return
            try:
                _log("language prompt: speaking")
                await self.session.say(self._language_prompt, allow_interruptions=False)
            except Exception as e:
                _log(f"language prompt error: {type(e).__name__}: {e}")
            # Wait briefly for a keypress. The DTMF handler (registered on the room in
            # _serve) fills dtmf_holder['selected'] and sets dtmf_event. On timeout we
            # simply default — never hang.
            if self._dtmf_event is not None:
                try:
                    await asyncio.wait_for(self._dtmf_event.wait(), timeout=6.0)
                except asyncio.TimeoutError:
                    pass
            selected = (self._dtmf_holder or {}).get("selected")
            if selected:
                self._call_language = selected   # handler already logged the selection
            else:
                self._call_language = primary
                # A true no-input timeout (event never set) is logged here; an invalid
                # digit was already logged by the handler, so don't double-log it.
                if self._dtmf_event is None or not self._dtmf_event.is_set():
                    _log(f"[AGENT] no DTMF — defaulting to {primary}")

        async def stt_node(self, audio, model_settings):
            """Per-call STT routing (Phase 3b fix). Arabic branch -> OpenAI Whisper (strong
            Arabic, language=ar); every other call -> the framework default, i.e. the session's
            Deepgram language='multi' STT exactly as today. The English path is completely
            untouched (self._arabic is False), so Whisper is NEVER used on a non-Arabic call."""
            if self._arabic and self._ar_stt is not None:
                async for ev in self._arabic_stt_node(audio, model_settings):
                    yield ev
                return
            async for ev in Agent.default.stt_node(self, audio, model_settings):
                yield ev

        async def _arabic_stt_node(self, audio, model_settings):
            """Transcribe the audio stream with the per-call Whisper STT. Whisper is
            non-streaming, so it is wrapped in the framework's VAD StreamAdapter (the session's
            silero VAD) — the standard way to drive a chunked STT; we do not force streaming."""
            from livekit.agents import stt as stt_mod, utils
            vad = getattr(self.session, "vad", None) or self.vad
            wrapped = stt_mod.StreamAdapter(stt=self._ar_stt, vad=vad)
            conn_options = self.session.conn_options.stt_conn_options
            async with wrapped.stream(conn_options=conn_options) as stream:
                async def _forward():
                    async for frame in audio:
                        stream.push_frame(frame)
                    stream.end_input()
                forward_task = asyncio.create_task(_forward())
                try:
                    async for ev in stream:
                        yield ev
                finally:
                    await utils.aio.cancel_and_wait(forward_task)

        async def tts_node(self, text, model_settings):
            """Per-call TTS routing (Phase 3b). Arabic branch -> Cartesia (MSA); every other
            call -> the framework default, i.e. the session's Deepgram TTS exactly as today.
            The English path is completely untouched (self._arabic is False)."""
            if self._arabic and self._ar_tts is not None:
                async for frame in self._arabic_tts_node(text, model_settings):
                    yield frame
                return
            async for frame in Agent.default.tts_node(self, text, model_settings):
                yield frame

        async def _arabic_tts_node(self, text, model_settings):
            """Synthesize the text stream with the per-call Cartesia Arabic TTS. Mirrors the
            framework's default streaming loop, but bound to self._ar_tts (Cartesia streams
            natively, so no StreamAdapter is needed)."""
            from livekit.agents import utils
            conn_options = self.session.conn_options.tts_conn_options
            async with self._ar_tts.stream(conn_options=conn_options) as stream:
                async def _forward():
                    async for chunk in text:
                        stream.push_text(chunk)
                    stream.end_input()
                forward_task = asyncio.create_task(_forward())
                try:
                    async for ev in stream:
                        yield ev.frame
                finally:
                    await utils.aio.cancel_and_wait(forward_task)

        async def on_user_turn_completed(self, turn_ctx, new_message):
            """Guardrail: classify -> fetch real data -> inject a strict instruction
            BEFORE the LLM responds. The LLM may only state what we provide here.
            Wrapped so an STT/classify/DB failure recovers (ask to repeat) instead of
            leaving the caller in silence."""
            user_text = (new_message.text_content or "").strip()
            logger.info("📝 turn: user said %r", user_text)
            if not user_text:
                return
            try:
                last_assistant = self._last_assistant(turn_ctx)
                t0 = time.perf_counter()
                decision = await self._brain.decide(user_text, last_assistant)
                elapsed = (time.perf_counter() - t0) * 1000
                if self._on_state:
                    self._on_state(self._brain.snapshot())
                # Strict per-turn instruction with ONLY the real DB data (English — unchanged).
                turn_ctx.add_message(role="system", content=decision["instruction"])
                # Phase 3b: ONLY on the Arabic branch, append a final output-language directive
                # so the LLM renders its spoken reply (incl. the goodbye) in MSA. The guardrail
                # instruction above and all DB data stay English — only the spoken reply changes.
                if self._arabic:
                    turn_ctx.add_message(role="system", content=ARABIC_OUTPUT_INSTRUCTION)
                logger.info("🧠 guardrail decided intent=%s end=%s in %.0fms",
                            decision.get("intent"), decision.get("end"), elapsed)
                if decision.get("end") and self._on_end:
                    asyncio.create_task(self._on_end(decision["end"]))
            except Exception as e:
                logger.error("turn handling error: %s: %s; asking caller to repeat",
                             type(e).__name__, e)
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


async def _serve(room, behavior_config, call_id, started_at, *, is_worker,
                 call_context=None, tenant_id=None):
    """Build the session + guarded agent, start it on the (already-connected) room,
    and run until the call ends (caller hangs up, agent ends it, or max duration).

    `behavior_config` is the resolved TENANT config (greeting_message, system_prompt,
    voice_id, max_call_duration) for the business the dialed number belongs to.
    `tenant_id` scopes all of the agent's data lookups to that business.

    `call_context` is set for OUTBOUND reminder calls: it carries the appointment data
    so the agent opens with the reminder script (not the inbound greeting) and the
    guardrail targets the right appointment. None → a normal inbound call."""
    from livekit.agents import RoomInputOptions

    reminder = bool(call_context and call_context.get("purpose") == "reminder")
    # Reminder calls know their tenant from the appointment; prefer that.
    if reminder and call_context.get("tenant_id"):
        tenant_id = call_context["tenant_id"]

    # The tenant's niche selects which function set + intents the guardrail loads.
    niche = (behavior_config or {}).get("niche") or "clinic"

    # ── Phase 3a: language selection over SIP (DTMF) ──────────────────────────────
    # Multi-language tenants get a brief keypad prompt at call start; the digit is captured
    # natively via LiveKit's `sip_dtmf_received` event on the SIP leg (no Twilio webhook).
    # Single-language tenants and outbound reminders skip it entirely — no prompt, no keypad,
    # zero change to today's flow. The chosen language is only stored + logged in this phase.
    languages = _normalize_languages((behavior_config or {}).get("supported_languages"))
    multi_language = (not reminder) and len(languages) >= 2
    language_prompt = None
    dtmf_event = None
    dtmf_holder = {"selected": None}
    dtmf_handler = None
    # Phase 3b: build the per-call Arabic (MSA) Cartesia TTS only when this tenant actually
    # offers Arabic. None when Arabic isn't offered or isn't configured -> agent stays English.
    ar_tts = None
    ar_greeting = None
    ar_stt = None
    if multi_language and "ar" in languages:
        ar_tts = _build_cartesia_ar_tts()
        if ar_tts is not None:
            ar_greeting = _arabic_greeting((behavior_config or {}).get("business_name"))
            # Phase 3b fix: Arabic speech-IN uses Whisper (Deepgram multi romanizes Arabic).
            # Only built when the Arabic branch is actually active (Cartesia voice present).
            ar_stt = _build_whisper_ar_stt()
    if multi_language:
        primary = languages[0]
        language_prompt = _build_language_prompt((behavior_config or {}).get("business_name"),
                                                 languages)
        dtmf_event = asyncio.Event()

        def _on_dtmf(ev, _languages=languages, _primary=primary):
            """LiveKit rtc.SipDTMF handler: map the keypad digit to a language by position
            (1 -> languages[0], 2 -> languages[1], …). Valid digit -> store it; invalid digit
            -> treat as no-input (default to primary). Always resolves the wait so the call
            proceeds immediately on a keypress."""
            try:
                digit = (getattr(ev, "digit", "") or "").strip()
                if not digit:
                    code = getattr(ev, "code", None)
                    digit = str(code) if code is not None else ""
                idx = int(digit) - 1 if digit.isdigit() else -1
                if 0 <= idx < len(_languages):
                    dtmf_holder["selected"] = _languages[idx]
                    print(f"[AGENT] call language selected via DTMF = {_languages[idx]}",
                          flush=True)
                else:
                    dtmf_holder["selected"] = None
                    print(f"[AGENT] invalid DTMF digit {digit!r} — defaulting to {_primary}",
                          flush=True)
            except Exception as e:
                dtmf_holder["selected"] = None
                print(f"[AGENT] DTMF handler error: {type(e).__name__}: {e}", flush=True)
            finally:
                dtmf_event.set()

        try:
            room.on("sip_dtmf_received", _on_dtmf)
            dtmf_handler = _on_dtmf
            _log(f"language selection enabled (languages={languages}) — awaiting keypad DTMF")
        except Exception as e:
            # No DTMF capability -> don't prompt; the agent defaults to the primary language
            # and runs the normal flow. Never require a keypress to function.
            print(f"[AGENT] could not register DTMF handler: {type(e).__name__}: {e}; "
                  f"defaulting to {primary}", flush=True)
            language_prompt = None

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

    if reminder:
        instructions = REMINDER_SYSTEM_PROMPT
        greeting = build_reminder_greeting(call_context)
        # Seed the appointment we're calling about so confirm/reschedule/cancel act on it.
        seed_entities = {k: call_context[k] for k in ("appointment_id", "phone", "patient_name")
                         if call_context.get(k)}
        pending_intent = "confirm_appointment"
        _log(f"outbound reminder call for appointment {call_context.get('appointment_id')}")
    else:
        instructions = (behavior_config or {}).get("system_prompt") or DEFAULT_SYSTEM_PROMPT
        # Greet using THIS tenant's greeting_message (falls back to the generic constant).
        greeting = (behavior_config or {}).get("greeting_message") or GREETING
        seed_entities = None
        pending_intent = None
        # CALLER RECOGNITION (all niches): look the caller's number up within THIS tenant's
        # records. If they're known, greet them by name and seed their phone so the agent
        # never re-asks for it. Best-effort + strictly tenant-scoped — never blocks the call.
        try:
            recognized = await _recognize_caller(room, tenant_id, niche)
        except Exception as e:
            print(f"[agent] caller recognition failed: {type(e).__name__}: {e}")
            recognized = None
        if recognized and recognized.get("found"):
            name = recognized.get("name")
            phone = recognized.get("phone")
            name_key = "patient_name" if niche in ("clinic", "dental", "spa") else "customer_name"
            seed_entities = {k: v for k, v in {name_key: name, "phone": phone}.items() if v}
            if name:
                greeting = f"Hello {name.split()[0]}, " + greeting[0].lower() + greeting[1:]
            _log(f"recognized returning caller {name!r} ({phone})")

    agent = _make_agent_class()(instructions=instructions, on_state=on_state, on_end=on_end,
                                greeting=greeting, seed_entities=seed_entities,
                                pending_intent=pending_intent, tenant_id=tenant_id, niche=niche,
                                language_prompt=language_prompt, languages=languages,
                                dtmf_event=dtmf_event, dtmf_holder=dtmf_holder,
                                ar_tts=ar_tts, ar_greeting=ar_greeting, ar_stt=ar_stt)

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
    if dtmf_handler is not None:
        try:
            room.off("sip_dtmf_received", dtmf_handler)
        except Exception:
            pass
    if not is_worker:
        try:
            await room.disconnect()
        except Exception:
            pass
    await _close_call(call_id, state, end_reason["r"] or "completed", started_at)

    # Record the reminder result on the appointment. A human answered (the agent ran),
    # so the floor is "answered"; the guardrail upgrades it to confirmed/rescheduled/
    # cancelled when the patient acts. no-answer/voicemail are set earlier by Twilio AMD.
    if reminder:
        try:
            from app.services.reminder_service import finalize_reminder_outcome
            outcome = state.get("reminder_outcome") or "answered"
            await finalize_reminder_outcome(call_context.get("appointment_id"), call_id, outcome)
            _log(f"reminder outcome recorded: {outcome}")
        except Exception as e:
            print(f"[agent] reminder finalize error: {type(e).__name__}: {e}")


def _is_sip_participant(p) -> bool:
    """True for a real phone caller (SIP participant) vs. our own agent participant."""
    try:
        from livekit.protocol import models as m
        if getattr(p, "kind", None) == m.ParticipantInfo.Kind.SIP:
            return True
    except Exception:
        pass
    return "sip" in (getattr(p, "identity", "") or "").lower()


async def _wait_for_sip_participant(room, timeout: float = 10.0):
    """Wait until the real SIP caller has joined the room, then return that participant.

    The DIALED number lives on the SIP participant's attributes and is only readable once
    it has joined. Resolving the tenant before this point is the race that made every call
    fall back to the default tenant ('no remote participants yet' → 'COULD NOT READ' →
    'FALLBACK'). Polls remote_participants up to `timeout` seconds. Returns the SIP
    participant, or None if none appears in time."""
    print(f"[AGENT] waiting up to {timeout:.0f}s for the SIP participant to join "
          f"room {getattr(room, 'name', '?')!r}…", flush=True)
    waited_ms = 0
    interval = 0.25
    while True:
        try:
            for p in room.remote_participants.values():
                if _is_sip_participant(p):
                    if waited_ms:
                        print(f"[AGENT] SIP participant present after waiting {waited_ms}ms",
                              flush=True)
                    return p
        except Exception:
            pass
        if waited_ms >= int(timeout * 1000):
            return None
        await asyncio.sleep(interval)
        waited_ms += int(interval * 1000)


async def _load_config_for_tenant(tenant_id):
    """Load a tenant's agent config (greeting/system_prompt/voice/niche/…) by id. Used for
    OUTBOUND reminder calls whose tenant is known from the appointment (not the dialed
    number). Returns {} if the tenant can't be loaded."""
    if not tenant_id:
        return {}
    try:
        from app.db.database import AsyncSessionLocal
        from app.services.tenant_service import load_tenant_config
        from app.models.models import Tenant
        async with AsyncSessionLocal() as db:
            tenant = await db.get(Tenant, tenant_id)
            if not tenant:
                return {}
            return await load_tenant_config(db, tenant)
    except Exception as e:
        print(f"[AGENT] load config for tenant {tenant_id} failed: {type(e).__name__}: {e}",
              flush=True)
        return {}


async def _end_call_no_tenant(ctx, room_name: str):
    """No tenant owns the dialed number — end the call WITHOUT answering as any business.
    We deliberately do not speak a greeting (which business would we be?). Best-effort
    disconnect so the call ends cleanly instead of the agent answering as the wrong shop."""
    print(f"[AGENT] ❌ ending call in room {room_name} — no tenant for the dialed number "
          "(refusing to answer as the wrong business)", flush=True)
    try:
        await ctx.room.disconnect()
    except Exception as e:
        print(f"[AGENT] disconnect after no-tenant failed: {type(e).__name__}: {e}", flush=True)


# ── Entry point 1: dedicated worker (livekit-agents dispatches a job) ─────────
async def entrypoint(ctx):
    from livekit.agents import AutoSubscribe

    # Log the moment a job lands — BEFORE connecting — so the worker log shows every
    # accepted inbound SIP job even if connecting/resolution later hiccups. If you see no
    # "JOB RECEIVED" line on an inbound call, the problem is upstream of the agent (the SIP
    # trunk rejected the call / no room was created), not in this entrypoint.
    pre_room = getattr(getattr(ctx, "room", None), "name", None) or "?"
    print(f"[AGENT] ▶ JOB RECEIVED for room {pre_room}", flush=True)

    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    except Exception as e:
        print(f"[AGENT] ❌ connect failed for room {pre_room}: {type(e).__name__}: {e}",
              flush=True)
        raise
    room_name = ctx.room.name
    print(f"[AGENT] connected to room {room_name} as {AGENT_IDENTITY}", flush=True)

    # Double-join guard: if another agent participant is already in this room, bail
    # out so only one agent ever answers a call.
    others = [p for p in ctx.room.remote_participants.values()
              if (getattr(p, "identity", "") or "").startswith(AGENT_IDENTITY_PREFIX)]
    if others:
        print(f"[AGENT] agent already in {room_name} ({others[0].identity}); skipping join",
              flush=True)
        await ctx.room.disconnect()
        return

    # Wait for the real SIP caller to JOIN before reading its attributes. The dialed number
    # lives on the SIP participant's attributes and isn't present at connect time — resolving
    # the tenant before the participant joins is the race that forced every call onto the
    # default clinic ('no remote participants yet' → 'COULD NOT READ' → 'FALLBACK').
    sip_participant = await _wait_for_sip_participant(ctx.room, timeout=10.0)
    if sip_participant is not None:
        print(f"[AGENT] SIP participant joined room {room_name}: "
              f"identity={getattr(sip_participant, 'identity', '?')!r} "
              f"kind={getattr(sip_participant, 'kind', '?')}", flush=True)
    else:
        print(f"[AGENT] ⚠️ no SIP participant joined room {room_name} within 10s — "
              "the dialed number may be unreadable; resolution will reflect that", flush=True)

    # Is this room one of our OUTBOUND reminder calls? Those carry their tenant from the
    # appointment (the dialed number on an outbound call is the PATIENT's number, which
    # matches no tenant), so resolve that first and skip dialed-number routing for them.
    call_context = None
    try:
        from app.services.reminder_service import resolve_outbound_context_for_room
        call_context = await resolve_outbound_context_for_room(ctx.room)
    except Exception as e:
        print(f"[AGENT] outbound context resolve failed: {type(e).__name__}: {e}", flush=True)

    if call_context:
        tenant_id = call_context.get("tenant_id")
        behavior_config = await _load_config_for_tenant(tenant_id)
        call_id = call_context.get("call_id")
        print(f"[AGENT] room {room_name} is an outbound reminder for appointment "
              f"{call_context.get('appointment_id')} (tenant {tenant_id})", flush=True)
    else:
        # INBOUND: resolve the tenant DETERMINISTICALLY from the real dialed number now that
        # the SIP participant is present. No silent fallback — if no tenant owns the number,
        # end the call rather than answer as the wrong business.
        tenant_id, behavior_config = await _resolve_tenant(ctx.room)
        if not tenant_id:
            await _end_call_no_tenant(ctx, room_name)
            return
        call_id = await _create_call_record(tenant_id, behavior_config, room_name, None)

    await _serve(ctx.room, behavior_config, call_id, datetime.utcnow(), is_worker=True,
                 call_context=call_context, tenant_id=tenant_id)


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
        # Phone -> tenant routing: resolve the tenant from the dialed number; the passed-in
        # behavior_config (if any) overrides the resolved tenant config for manual use.
        tenant_id, resolved_config = await _resolve_tenant(room)
        behavior_config = behavior_config or resolved_config
        # Resolve outbound-reminder context (no-op for inbound calls).
        call_context = None
        try:
            from app.services.reminder_service import resolve_outbound_context_for_room
            call_context = await resolve_outbound_context_for_room(room)
            if call_context:
                call_id = call_context.get("call_id") or call_id
                tenant_id = call_context.get("tenant_id") or tenant_id
        except Exception as e:
            print(f"[agent] outbound context resolve failed: {type(e).__name__}: {e}")
        await _serve(room, behavior_config or {}, call_id, datetime.utcnow(),
                     is_worker=False, call_context=call_context, tenant_id=tenant_id)
    except Exception as e:
        print(f"[agent] error in room {room_name}: {type(e).__name__}: {e}")
    finally:
        _active_rooms.discard(room_name)


# ── Shared DB helpers ─────────────────────────────────────────────────────────

async def _resolve_tenant(room):
    """Phone -> tenant resolution for a joined `call-*` room. Returns (tenant_id, config)
    where config is the tenant's agent config (greeting, system_prompt, voice_id,
    max_call_duration). Reads the DIALED number off the SIP participant's attributes (the
    caller must have already joined — see entrypoint's _wait_for_sip_participant) and matches
    it to exactly one tenant. DETERMINISTIC: no silent default fallback (unless
    ALLOW_DEFAULT_TENANT_FALLBACK is set). Returns (None, {}) when no tenant can be resolved,
    which the caller treats as 'cannot route — end the call'. Never raises."""
    try:
        from app.db.database import AsyncSessionLocal
        from app.services.tenant_service import tenant_context_for_room, sip_called_number
        room_name = getattr(room, "name", "?")
        print(f"[AGENT] _resolve_tenant start for room {room_name!r}", flush=True)
        dialed = None
        try:
            dialed = sip_called_number(room)
        except Exception:
            dialed = None
        # tenant_context_for_room dumps every SIP attribute, logs the dialed number, and
        # emits the loud ⚠️ FALLBACK TO DEFAULT TENANT line when no tenant matches.
        async with AsyncSessionLocal() as db:
            resolved = await tenant_context_for_room(db, room)
        if resolved:
            tenant_id, config = resolved
            print(f"[AGENT] _resolve_tenant -> {config.get('business_name')} "
                  f"({config.get('niche')}) for dialed number {dialed or 'unknown'} "
                  f"[tenant_id={tenant_id}]", flush=True)
            return tenant_id, config
        print(f"[AGENT] no tenant resolved for dialed number {dialed or 'unknown'} — "
              "deterministic routing found no match; caller will NOT be answered", flush=True)
        return None, {}
    except Exception as e:
        # On error we do NOT guess a tenant — better to end the call than answer as the
        # wrong business. The caller (entrypoint) ends the call when this returns no tenant.
        print(f"[AGENT] tenant resolve error: {type(e).__name__}: {e}; cannot route", flush=True)
        return None, {}


async def _recognize_caller(room, tenant_id, niche):
    """Read the caller's number off the SIP join and look them up within THIS tenant's
    records (patients / reservations / orders / leads, by niche). Returns the recognition
    dict ({found, name, phone, ...}) or None. Strictly tenant-scoped; never raises into
    the call path."""
    try:
        from app.services.tenant_service import sip_caller_number
        from app.agents.common_functions import recognize_caller
        caller = sip_caller_number(room)
        if not caller:
            return None
        result = await recognize_caller(phone=caller, niche=niche, tenant_id=tenant_id)
        if result:
            result.setdefault("phone", caller)
        return result
    except Exception as e:
        print(f"[agent] _recognize_caller error: {type(e).__name__}: {e}")
        return None


async def _create_call_record(tenant_id, config, room_name, caller):
    try:
        from app.db.database import AsyncSessionLocal
        from app.models.models import Call, CallDirection, CallOutcome
        async with AsyncSessionLocal() as db:
            call = Call(
                tenant_id=tenant_id,
                agent_id=(config or {}).get("agent_id"),
                livekit_room=room_name,
                direction=CallDirection.inbound,
                caller_number=caller or "sip-caller",
                # The dialed (tenant) number — falls back to the configured default.
                called_number=(config or {}).get("twilio_phone_number") or settings.TWILIO_PHONE_NUMBER,
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
