"""
Anti-hallucination guardrail.

Two layers live here:

  * GuardrailBrain — pure, framework-agnostic logic. For every caller utterance it
    classifies intent + entities + language (OpenAI function call), runs the matching
    clinic_functions.* against the DB to get REAL data, and builds a STRICT, tightly
    scoped instruction the LLM may use as its ONLY source of truth. The live phone
    agent (clinic_agent.ClinicAgent.on_user_turn_completed) uses this directly — no
    Pipecat needed, which is why it works inside the native livekit-agents AgentSession.

  * IntentGuardrailProcessor — a thin Pipecat FrameProcessor wrapper around the brain,
    kept for the Pipecat pipeline variant and the spec's FILE 2 surface.

The LLM is forbidden from inventing appointment times, prices, doctor names, policies,
or insurance details — it is only a natural-language formatter of the brain's data.
"""
import json
import logging
import re
import time
from datetime import date, timedelta

from app.agents.clinic_functions import CLINIC_FUNCTIONS

logger = logging.getLogger("clinic-agent.guardrail")

LANGUAGES = {"en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish"}

# Classifier OpenAI call timeout (s). Without this a hung classify call leaves the
# agent silent mid-call (on_user_turn_completed awaits it forever).
_CLASSIFY_TIMEOUT = 8.0

_WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_iso_date(v) -> bool:
    if not isinstance(v, str) or not _ISO_RE.match(v):
        return False
    try:
        date.fromisoformat(v)
        return True
    except ValueError:
        return False


def _resolve_relative_date(text: str, today_iso: str) -> str | None:
    """Deterministically convert a relative date phrase in `text` to an ISO date, so the
    agent never has to ask the caller for a calendar date. Handles today/tonight,
    tomorrow, day after tomorrow, '(this|next) <weekday>', a bare <weekday>, and
    'next week'. Returns YYYY-MM-DD or None if no relative phrase is found."""
    try:
        today = date.fromisoformat(today_iso)
    except (ValueError, TypeError):
        return None
    t = text.lower()
    if "day after tomorrow" in t:
        return (today + timedelta(days=2)).isoformat()
    if "tomorrow" in t:
        return (today + timedelta(days=1)).isoformat()
    if "today" in t or "tonight" in t:
        return today.isoformat()
    for name, wd in _WEEKDAYS.items():
        if re.search(rf"\b{name}\b", t):
            base = (wd - today.weekday()) % 7
            days = base or 7  # next future occurrence — a named weekday never means today
            if "next" in t and base != 0:
                days += 7      # "next <weekday>" = the one a full week on
            return (today + timedelta(days=days)).isoformat()
    if "next week" in t:
        return (today + timedelta(days=7)).isoformat()
    return None

INTENTS = [
    "book_appointment", "cancel_appointment", "reschedule_appointment",
    "check_appointment", "clinic_hours", "clinic_location", "services_offered",
    "doctor_availability", "insurance_question", "speak_to_human", "end_call",
    "unclear",
]

# Single function the classifier is forced to call.
_ROUTER_TOOL = [{
    "type": "function",
    "function": {
        "name": "route_intent",
        "description": "Classify the caller's latest message into one clinic intent and extract any entities.",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": INTENTS},
                "language": {"type": "string", "enum": list(LANGUAGES),
                             "description": "Language the caller is speaking."},
                "patient_name": {"type": "string"},
                "phone": {"type": "string", "description": "Digits only if given."},
                "doctor": {"type": "string", "description": "Doctor name or specialty mentioned."},
                "date": {"type": "string", "description": "Resolved appointment date, YYYY-MM-DD."},
                "time": {"type": "string", "description": "Resolved time, 24h HH:MM."},
                "new_date": {"type": "string", "description": "Reschedule target date, YYYY-MM-DD."},
                "new_time": {"type": "string", "description": "Reschedule target time, HH:MM."},
                "reason": {"type": "string", "description": "Reason for the visit."},
                "appointment_id": {"type": "string"},
                "insurance_provider": {"type": "string"},
            },
            "required": ["intent", "language"],
        },
    },
}]

_ENTITY_KEYS = ["patient_name", "phone", "doctor", "date", "time", "new_date",
                "new_time", "reason", "appointment_id", "insurance_provider"]

_FUNCTION_ARGS = {
    "book_appointment": ["patient_name", "phone", "doctor", "date", "time", "reason"],
    "cancel_appointment": ["phone", "appointment_id"],
    "reschedule_appointment": ["phone", "new_date", "new_time", "appointment_id"],
    "check_appointment": ["phone"],
    "clinic_hours": [],
    "clinic_location": [],
    "services_offered": [],
    "doctor_availability": ["doctor", "date"],
    "insurance_question": ["insurance_provider"],
}

# Intents that DO something and can sit "pending" awaiting confirmation / a missing
# detail. A bare "yes" right after the agent asked to confirm one of these resolves
# back to it (see GuardrailBrain._pending_intent).
_ACTIONABLE = {"book_appointment", "cancel_appointment", "reschedule_appointment"}

# Short affirmations that confirm a pending action. These must NEVER be treated as
# "unclear" — a caller saying "yes" to "shall I book it?" is completing the booking.
_AFFIRMATIVE_WORDS = {
    "yes", "yeah", "yep", "yup", "yes please", "sure", "okay", "ok", "correct",
    "right", "that's right", "thats right", "that is right", "that's correct",
    "thats correct", "that is correct", "go ahead", "go for it", "please do",
    "please", "do it", "confirm", "confirmed", "sounds good", "perfect",
    "absolutely", "of course", "definitely", "exactly", "affirmative",
}
_AFFIRMATIVE_PREFIX = re.compile(
    r"^(yes|yeah|yep|yup|sure|ok|okay|correct|right|confirm|confirmed)\b", re.I)


def _is_affirmative(text: str) -> bool:
    """True if the caller's utterance is a plain confirmation ('yes', 'that's right',
    'go ahead', 'yes, that's correct') — i.e. agreement, not a new request."""
    t = text.lower().strip().strip(".!?,")
    if not t:
        return False
    if t in _AFFIRMATIVE_WORDS:
        return True
    return bool(_AFFIRMATIVE_PREFIX.match(t))


class GuardrailBrain:
    """Framework-agnostic guardrail logic. One instance per call."""

    def __init__(self, *, openai_api_key: str, today: str, model: str = "gpt-4o-mini",
                 max_unclear: int = 5):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self._model = model
        self._today = today
        # Human-readable today (with weekday) so the classifier can compute "next Monday".
        try:
            self._today_human = date.fromisoformat(today).strftime("%A, %B %d, %Y")
        except (ValueError, TypeError):
            self._today_human = today
        # Lenient by default: only hand off to staff after many genuinely-unintelligible
        # turns. The streak resets on ANY real intent / new entity / confirmation, so a
        # caller who is actually being helped never hits this.
        self._max_unclear = max_unclear

        self.entities: dict = {}
        self.language = "en"
        self._language_locked = False
        self._unclear_streak = 0
        # Last actionable intent awaiting confirmation / a missing detail. A follow-up
        # "yes" or a bare detail (phone, time) resolves back to this instead of looking
        # like an out-of-context, unclear utterance.
        self._pending_intent: str | None = None

    def snapshot(self) -> dict:
        return {"language": self.language, "entities": dict(self.entities)}

    async def decide(self, user_text: str, last_assistant: str = "") -> dict:
        """Classify -> fetch real data -> build a strict LLM instruction.

        Returns {instruction, intent, data, end (reason|None), transfer (bool)}.
        Never raises — on error it returns a safe "connect to staff" instruction.
        """
        t0 = time.perf_counter()
        try:
            intent, extracted, language = await self._classify(
                user_text, last_assistant, self._pending_intent, self.entities)
        except Exception as e:
            logger.error("❌ classify error after %.0fms: %s: %s",
                         (time.perf_counter() - t0) * 1000, type(e).__name__, e)
            # Don't transfer on a transient classify failure — ask the caller to repeat.
            return {"instruction": self._wrap(
                last_assistant,
                {"instruction_text": "There was a brief delay. Apologise in one short sentence "
                                     "and ask the caller to please repeat that."}),
                "intent": "unclear", "data": {}, "end": None, "transfer": False}

        affirmative = _is_affirmative(user_text)
        # Backstop for the classifier: a plain confirmation while an action is pending
        # COMPLETES that action — it is never "unclear" or "end_call" noise. The
        # accumulated entities are carried forward so the function fires with everything
        # collected across the whole conversation.
        if affirmative and self._pending_intent and intent in ("unclear", "end_call"):
            logger.info("✅ affirmative %r resolved to pending intent %s",
                        user_text, self._pending_intent)
            intent = self._pending_intent

        logger.info("🧭 intent=%s lang=%s entities=%s pending=%s in %.0fms",
                    intent, language, extracted, self._pending_intent,
                    (time.perf_counter() - t0) * 1000)

        if not self._language_locked and language in LANGUAGES:
            self.language = language
            self._language_locked = True

        # Merge (never overwrite-and-forget) entities across turns. `contributed` tracks
        # whether this turn added/changed any detail — a turn that moves the booking
        # forward must reset the unclear streak even if the intent looked thin.
        contributed = False
        for k in _ENTITY_KEYS:
            if extracted.get(k) and self.entities.get(k) != extracted[k]:
                self.entities[k] = extracted[k]
                contributed = True

        # Deterministic relative-date resolution — so we never ask the caller for a
        # calendar date even if the classifier left it relative/blank.
        resolved = _resolve_relative_date(user_text, self._today)
        if resolved:
            field = "new_date" if intent == "reschedule_appointment" else "date"
            if not _is_iso_date(self.entities.get(field)):
                self.entities[field] = resolved
                contributed = True
                logger.info("📅 resolved relative date -> %s (field=%s)", resolved, field)

        if intent == "end_call":
            return {"instruction": self._wrap(last_assistant,
                    {"situation": "The caller is ending the call.",
                     "task": "Give a brief, warm goodbye. Do not ask anything else."}),
                    "intent": intent, "data": {}, "end": "caller_said_goodbye", "transfer": False}

        if intent == "speak_to_human":
            return {"instruction": self._wrap(last_assistant,
                    {"action": "transfer",
                     "task": "Tell the caller you're connecting them to a staff member now."}),
                    "intent": intent, "data": {}, "end": None, "transfer": True}

        if intent == "unclear":
            # An affirmation or any turn that contributed a detail is NEVER counted as
            # unclear — the caller is engaged and moving forward, not stuck. Only a turn
            # that is genuinely unintelligible advances the streak toward a handoff.
            if affirmative or contributed:
                self._unclear_streak = 0
            else:
                self._unclear_streak += 1
            if self._unclear_streak >= self._max_unclear:
                return {"instruction": self._wrap(last_assistant,
                        {"action": "transfer",
                         "task": "Say you're having trouble understanding and will connect them to staff."}),
                        "intent": intent, "data": {}, "end": "too_many_unclear", "transfer": True}
            return {"instruction": self._wrap(last_assistant,
                    {"situation": "The caller's request was unclear.",
                     "task": "Ask one short, friendly clarifying question to find out how you can help."}),
                    "intent": intent, "data": {}, "end": None, "transfer": False}

        # A real intent (or a turn that contributed an entity) means the call is making
        # progress — reset the unclear streak so an earlier hiccup never triggers a handoff.
        self._unclear_streak = 0
        # Remember an actionable intent so a follow-up "yes" / bare detail resolves to it.
        if intent in _ACTIONABLE:
            self._pending_intent = intent

        func = CLINIC_FUNCTIONS.get(intent)
        data = {}
        if func:
            kwargs = {k: self.entities.get(k) for k in _FUNCTION_ARGS.get(intent, [])}
            tf = time.perf_counter()
            try:
                data = await func(**kwargs)
                logger.info("🔧 fn %s args=%s -> %s in %.0fms", intent, kwargs,
                            (list(data)[:6] if isinstance(data, dict) else type(data).__name__),
                            (time.perf_counter() - tf) * 1000)
            except Exception as e:
                logger.error("❌ function %s error after %.0fms: %s: %s", intent,
                             (time.perf_counter() - tf) * 1000, type(e).__name__, e)
                data = {}

        # Once an actionable request succeeds, clear the pending flag so a later "yes"
        # can't accidentally repeat it (e.g. re-book the same appointment).
        if intent in _ACTIONABLE and isinstance(data, dict) and data.get("success"):
            self._pending_intent = None

        payload = {"intent": intent, "data": data}
        if intent == "book_appointment" and not data.get("success"):
            payload["task"] = ("The booking is not complete. Politely ask only for the missing "
                               "detail(s); do not confirm a booking.")
        return {"instruction": self._wrap(last_assistant, payload),
                "intent": intent, "data": data, "end": None, "transfer": False}

    async def _classify(self, user_text: str, last_assistant: str = "",
                        pending_intent: str | None = None, entities: dict | None = None):
        sys = (
            f"You route a medical-clinic phone call. Today is {self._today_human} "
            f"({self._today}). Classify the caller's latest message into exactly one intent "
            "and extract entities. ALWAYS compute relative dates yourself from today's date — "
            "'tomorrow', 'this Friday', 'next Monday at 3pm', 'next week' — into absolute "
            "YYYY-MM-DD and 24h HH:MM. NEVER leave a date relative and never expect the caller "
            "to give a calendar date. Detect the spoken language (en/ar/fr/es). "
            "If the message is ambiguous or you cannot tell what they want, use intent 'unclear'."
        )

        # Give the classifier short-term memory of the dialogue so short replies — "yes",
        # "correct", a bare phone number or time — are interpreted against what the agent
        # just asked and the action already in progress, instead of looking unclear.
        ctx = []
        if last_assistant:
            ctx.append(f'The assistant just said: "{last_assistant}"')
        if pending_intent:
            ctx.append(f"An action is already in progress and awaiting completion: "
                       f"{pending_intent}.")
        if entities:
            known = ", ".join(f"{k}={v}" for k, v in entities.items())
            ctx.append(f"Details already collected this call: {known}.")
        if ctx:
            sys += (
                "\n\nCONVERSATION CONTEXT (use it to interpret short replies):\n"
                + "\n".join(ctx)
                + "\n\nRULES FOR SHORT REPLIES:\n"
                "- If the assistant just asked the caller to confirm an action and the "
                "caller responds affirmatively (yes / yeah / correct / that's right / "
                "go ahead / sure / please do), classify the intent as the pending action "
                f"({pending_intent or 'the action in progress'}) — NOT 'unclear' — and "
                "carry the already-collected entities forward.\n"
                "- If the caller gives a bare detail (a phone number, a name, a time, a "
                "doctor) that fills a missing field for the pending action, classify it as "
                "that pending action and extract the new entity.\n"
                "- Only use 'unclear' when the caller's message truly cannot be tied to "
                "any intent or to the action in progress."
            )

        messages = [{"role": "system", "content": sys}]
        if last_assistant:
            messages.append({"role": "assistant", "content": last_assistant})
        messages.append({"role": "user", "content": user_text})
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=_ROUTER_TOOL,
            tool_choice={"type": "function", "function": {"name": "route_intent"}},
            temperature=0,
            max_tokens=300,
            timeout=_CLASSIFY_TIMEOUT,
        )
        call = resp.choices[0].message.tool_calls[0]
        args = json.loads(call.function.arguments or "{}")
        intent = args.get("intent", "unclear")
        language = args.get("language", "en")
        extracted = {k: args[k] for k in _ENTITY_KEYS if args.get(k)}
        return intent, extracted, language

    def _wrap(self, last_assistant: str, payload: dict) -> str:
        """Build the strict per-turn system instruction around a data payload."""
        lang_name = LANGUAGES.get(self.language, "English")
        guard = (
            "You are the AI receptionist for a medical clinic. You may ONLY use the information "
            "provided below. NEVER invent appointment times, prices, doctor names, policies, or "
            "insurance details. If the data is empty or a request failed, apologise briefly and "
            "offer to connect them to staff. When a date is already known, confirm it back to the "
            "caller (e.g. 'Monday, June 9') — NEVER ask the caller to provide a calendar date; "
            "relative dates like 'next Monday' are already resolved for you. "
            "You are on a PHONE call: reply in ONE short sentence, MAXIMUM 15 words, like a real "
            "receptionist. Never list more than 2 items — when listing services or insurers, give "
            "only the top 2-3 then ask if they want more. "
            f"Reply in {lang_name}. Do not greet again."
        )
        if last_assistant:
            guard += (f" Your previous reply was: \"{last_assistant}\". Do NOT repeat it; if the "
                      "information is unchanged, confirm it in different words.")
        if self.entities:
            known = ", ".join(f"{k}={v}" for k, v in self.entities.items())
            guard += f" Details already collected (never ask for these again): {known}."
        return guard + "\n\nDATA (the only thing you may state):\n" + json.dumps(payload, ensure_ascii=False)


# ── Pipecat wrapper (kept for the Pipecat pipeline variant / spec FILE 2) ─────

class IntentGuardrailProcessor:
    """Pipecat FrameProcessor that runs the GuardrailBrain. Imported lazily so that
    the native livekit-agents path never needs Pipecat installed."""

    def __new__(cls, *args, **kwargs):
        from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
        from pipecat.frames.frames import Frame  # noqa: F401
        from pipecat.processors.aggregators.openai_llm_context import (
            OpenAILLMContext, OpenAILLMContextFrame,
        )

        class _Impl(FrameProcessor):
            def __init__(self, *, openai_api_key, today, model="gpt-4o-mini",
                         on_end_call=None, on_state=None, **kw):
                super().__init__(**kw)
                self._brain = GuardrailBrain(openai_api_key=openai_api_key, today=today, model=model)
                self._on_end_call = on_end_call
                self._on_state = on_state
                self._ended = False

            async def process_frame(self, frame, direction):
                await super().process_frame(frame, direction)
                if isinstance(frame, OpenAILLMContextFrame) and direction == FrameDirection.DOWNSTREAM:
                    await self._handle(frame)
                    return
                await self.push_frame(frame, direction)

            async def _handle(self, frame):
                if self._ended:
                    return
                msgs = frame.context.get_messages()
                user_text = _last(msgs, "user")
                last_assistant = _last(msgs, "assistant")
                if not user_text:
                    await self.push_frame(frame, FrameDirection.DOWNSTREAM)
                    return
                decision = await self._brain.decide(user_text, last_assistant)
                if self._on_state:
                    self._on_state(self._brain.snapshot())
                ctx = OpenAILLMContext(messages=[
                    {"role": "system", "content": decision["instruction"]},
                    {"role": "user", "content": user_text},
                ])
                await self.push_frame(OpenAILLMContextFrame(context=ctx), FrameDirection.DOWNSTREAM)
                if decision.get("end") and self._on_end_call:
                    self._ended = True
                    await self._on_end_call(decision["end"])

        def _last(messages, role):
            for m in reversed(messages):
                if m.get("role") == role:
                    c = m.get("content")
                    if isinstance(c, str):
                        return c.strip()
                    if isinstance(c, list):
                        return " ".join(p.get("text", "") for p in c if isinstance(p, dict)).strip()
            return ""

        return _Impl(*args, **kwargs)
