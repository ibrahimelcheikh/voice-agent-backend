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


class GuardrailBrain:
    """Framework-agnostic guardrail logic. One instance per call."""

    def __init__(self, *, openai_api_key: str, today: str, model: str = "gpt-4o-mini",
                 max_unclear: int = 3):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self._model = model
        self._today = today
        # Human-readable today (with weekday) so the classifier can compute "next Monday".
        try:
            self._today_human = date.fromisoformat(today).strftime("%A, %B %d, %Y")
        except (ValueError, TypeError):
            self._today_human = today
        self._max_unclear = max_unclear

        self.entities: dict = {}
        self.language = "en"
        self._language_locked = False
        self._unclear_streak = 0

    def snapshot(self) -> dict:
        return {"language": self.language, "entities": dict(self.entities)}

    async def decide(self, user_text: str, last_assistant: str = "") -> dict:
        """Classify -> fetch real data -> build a strict LLM instruction.

        Returns {instruction, intent, data, end (reason|None), transfer (bool)}.
        Never raises — on error it returns a safe "connect to staff" instruction.
        """
        t0 = time.perf_counter()
        try:
            intent, extracted, language = await self._classify(user_text)
        except Exception as e:
            logger.error("❌ classify error after %.0fms: %s: %s",
                         (time.perf_counter() - t0) * 1000, type(e).__name__, e)
            # Don't transfer on a transient classify failure — ask the caller to repeat.
            return {"instruction": self._wrap(
                last_assistant,
                {"instruction_text": "There was a brief delay. Apologise in one short sentence "
                                     "and ask the caller to please repeat that."}),
                "intent": "unclear", "data": {}, "end": None, "transfer": False}
        logger.info("🧭 intent=%s lang=%s entities=%s in %.0fms",
                    intent, language, extracted, (time.perf_counter() - t0) * 1000)

        if not self._language_locked and language in LANGUAGES:
            self.language = language
            self._language_locked = True

        for k in _ENTITY_KEYS:
            if extracted.get(k):
                self.entities[k] = extracted[k]

        # Deterministic relative-date resolution — so we never ask the caller for a
        # calendar date even if the classifier left it relative/blank.
        resolved = _resolve_relative_date(user_text, self._today)
        if resolved:
            field = "new_date" if intent == "reschedule_appointment" else "date"
            if not _is_iso_date(self.entities.get(field)):
                self.entities[field] = resolved
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

        self._unclear_streak = 0

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

        payload = {"intent": intent, "data": data}
        if intent == "book_appointment" and not data.get("success"):
            payload["task"] = ("The booking is not complete. Politely ask only for the missing "
                               "detail(s); do not confirm a booking.")
        return {"instruction": self._wrap(last_assistant, payload),
                "intent": intent, "data": data, "end": None, "transfer": False}

    async def _classify(self, user_text: str):
        sys = (
            f"You route a medical-clinic phone call. Today is {self._today_human} "
            f"({self._today}). Classify the caller's latest message into exactly one intent "
            "and extract entities. ALWAYS compute relative dates yourself from today's date — "
            "'tomorrow', 'this Friday', 'next Monday at 3pm', 'next week' — into absolute "
            "YYYY-MM-DD and 24h HH:MM. NEVER leave a date relative and never expect the caller "
            "to give a calendar date. Detect the spoken language (en/ar/fr/es). "
            "If the message is ambiguous or you cannot tell what they want, use intent 'unclear'."
        )
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": user_text}],
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
            f"Reply in {lang_name}, in 1-2 short, warm, professional sentences. Do not greet again."
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
