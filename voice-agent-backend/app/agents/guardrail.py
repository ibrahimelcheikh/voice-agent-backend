"""
IntentGuardrailProcessor — the anti-hallucination wrapper.

This is the core safety mechanism. The LLM is NEVER allowed to freely generate
clinic information. Instead, for every caller utterance this processor:

  1. Intercepts the transcribed user text (from the user context aggregator).
  2. Classifies intent + entities with an OpenAI function call.
  3. Executes the matching clinic_functions.* function -> REAL data from the DB.
  4. Builds a STRICT, tightly-scoped instruction containing ONLY that data.
  5. Hands that instruction to the LLM, which becomes a natural-language
     formatter of real data — not a knowledge source.

It also handles: language detection (EN/AR/FR/ES), no-repetition, remembering
entities already provided, clarifying questions on unclear intent, and signalling
intelligent call ending.

Placed in the pipeline between the user context aggregator and the LLM:

    ... -> user_aggregator -> IntentGuardrailProcessor -> LLM -> ...
"""
import json

from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, TextFrame, LLMMessagesFrame  # noqa: F401 (spec import surface)
from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext, OpenAILLMContextFrame,
)

from app.agents.clinic_functions import CLINIC_FUNCTIONS

LANGUAGES = {"en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish"}

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

# Entities that should persist across turns so we never re-ask for them.
_ENTITY_KEYS = ["patient_name", "phone", "doctor", "date", "time", "new_date",
                "new_time", "reason", "appointment_id", "insurance_provider"]

# Which accumulated entities each clinic function call needs.
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


class IntentGuardrailProcessor(FrameProcessor):
    def __init__(self, *, openai_api_key: str, today: str, model: str = "gpt-4o-mini",
                 max_unclear: int = 3, on_end_call=None, on_state=None, **kwargs):
        super().__init__(**kwargs)
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self._model = model
        self._today = today
        self._max_unclear = max_unclear
        self._on_end_call = on_end_call        # async (reason) -> None
        self._on_state = on_state              # (dict) -> None  (language/entities to call record)

        self.entities: dict = {}
        self.language = "en"
        self._language_locked = False
        self._unclear_streak = 0
        self._ended = False

    # ── frame plumbing ────────────────────────────────────────────────────────

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Only intercept the user's aggregated context heading toward the LLM.
        if isinstance(frame, OpenAILLMContextFrame) and direction == FrameDirection.DOWNSTREAM:
            await self._handle_user_turn(frame)
            return

        await self.push_frame(frame, direction)

    # ── the guardrail ─────────────────────────────────────────────────────────

    async def _handle_user_turn(self, frame: OpenAILLMContextFrame):
        if self._ended:
            return
        messages = frame.context.get_messages()
        user_text = self._last_user_text(messages)
        last_assistant = self._last_assistant_text(messages)

        if not user_text:
            # Nothing to classify — let the original context flow so the LLM can prompt.
            await self.push_frame(frame, FrameDirection.DOWNSTREAM)
            return

        try:
            intent, extracted, language = await self._classify(user_text)
        except Exception as e:  # never crash the call on a classifier hiccup
            print(f"[guardrail] classify error: {type(e).__name__}: {e}")
            await self._emit_instruction(
                "I'm having a little trouble — let me connect you with our staff who can help.",
                user_text, last_assistant, force_text=True)
            return

        # Lock the caller's language on the first confident detection.
        if not self._language_locked and language in LANGUAGES:
            self.language = language
            self._language_locked = True
            self._notify_state()

        # Persist any new entities so we don't ask again.
        for k in _ENTITY_KEYS:
            v = extracted.get(k)
            if v:
                self.entities[k] = v

        # End-call / human handoff intents short-circuit the LLM.
        if intent == "end_call":
            await self._end("caller_said_goodbye")
            return
        if intent == "speak_to_human":
            await self._emit_instruction(
                None, user_text, last_assistant,
                data={"action": "transfer", "message": "Connecting to a staff member."},
                intent="speak_to_human")
            return

        # Unclear -> ask a clarifying question instead of guessing.
        if intent == "unclear":
            self._unclear_streak += 1
            if self._unclear_streak >= self._max_unclear:
                await self._emit_instruction(
                    None, user_text, last_assistant,
                    data={"action": "transfer",
                          "message": "I'm having trouble understanding. Let me connect you to our staff."},
                    intent="speak_to_human", then_end="too_many_unclear")
                return
            await self._emit_instruction(
                None, user_text, last_assistant,
                data={"action": "clarify"}, intent="unclear")
            return

        self._unclear_streak = 0

        # Execute the matching clinic function -> REAL data only.
        func = CLINIC_FUNCTIONS.get(intent)
        data = {}
        if func:
            kwargs = {k: self.entities.get(k) for k in _FUNCTION_ARGS.get(intent, [])}
            try:
                data = await func(**kwargs)
            except Exception as e:
                print(f"[guardrail] function {intent} error: {type(e).__name__}: {e}")
                data = {}

        await self._emit_instruction(None, user_text, last_assistant,
                                     data=data, intent=intent)

    # ── classification ────────────────────────────────────────────────────────

    async def _classify(self, user_text: str):
        sys = (
            f"You route a medical-clinic phone call. Today is {self._today}. "
            "Classify the caller's latest message into exactly one intent and extract entities. "
            "Resolve relative dates/times (e.g. 'tomorrow', 'next Monday at 3pm') into absolute "
            "YYYY-MM-DD and 24h HH:MM. Detect the spoken language (en/ar/fr/es). "
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
        )
        call = resp.choices[0].message.tool_calls[0]
        args = json.loads(call.function.arguments or "{}")
        intent = args.get("intent", "unclear")
        language = args.get("language", "en")
        extracted = {k: args[k] for k in _ENTITY_KEYS if args.get(k)}
        return intent, extracted, language

    # ── strict instruction -> LLM ─────────────────────────────────────────────

    async def _emit_instruction(self, fixed_text, user_text, last_assistant, *,
                                data=None, intent=None, force_text=False, then_end=None):
        """Build a tight system instruction from REAL data and push a fresh,
        minimal context to the LLM. The LLM may only phrase what's here."""
        lang_name = LANGUAGES.get(self.language, "English")
        guard = (
            "You are the AI receptionist for a medical clinic. You may ONLY use the "
            "information provided below. NEVER invent appointment times, prices, doctor "
            "names, policies, or insurance details. If the data is empty or a request "
            "failed, apologise briefly and offer to connect them to staff. "
            f"Reply in {lang_name}, in 1-2 short, warm, professional sentences. "
            "Do not greet again."
        )
        if last_assistant:
            guard += (f" Your previous reply was: \"{last_assistant}\". Do NOT repeat it; "
                      "if the information is unchanged, confirm it in different words.")
        if self.entities:
            known = ", ".join(f"{k}={v}" for k, v in self.entities.items())
            guard += f" Details already collected (never ask for these again): {known}."

        if force_text and fixed_text:
            payload = {"instruction_text": fixed_text}
        elif intent == "unclear":
            payload = {"situation": "The caller's request was unclear.",
                       "task": "Ask one short, friendly clarifying question to find out how you can help."}
        elif data is not None:
            payload = {"intent": intent, "data": data}
            if intent == "book_appointment" and not data.get("success"):
                payload["task"] = (
                    "The booking is not complete. Politely ask only for the missing detail(s); "
                    "do not confirm a booking.")
        else:
            payload = {"data": {}}

        guard += "\n\nDATA (the only thing you may state):\n" + json.dumps(payload, ensure_ascii=False)

        context = OpenAILLMContext(messages=[
            {"role": "system", "content": guard},
            {"role": "user", "content": user_text},
        ])
        await self.push_frame(OpenAILLMContextFrame(context=context), FrameDirection.DOWNSTREAM)

        if then_end:
            await self._end(then_end)

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _end(self, reason: str):
        if self._ended:
            return
        self._ended = True
        self._notify_state()
        if self._on_end_call:
            try:
                await self._on_end_call(reason)
            except Exception as e:
                print(f"[guardrail] on_end_call error: {type(e).__name__}: {e}")

    def _notify_state(self):
        if self._on_state:
            try:
                self._on_state({"language": self.language, "entities": dict(self.entities)})
            except Exception:
                pass

    @staticmethod
    def _last_user_text(messages) -> str:
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content")
                if isinstance(c, str):
                    return c.strip()
                if isinstance(c, list):  # multimodal — pull text parts
                    return " ".join(p.get("text", "") for p in c if isinstance(p, dict)).strip()
        return ""

    @staticmethod
    def _last_assistant_text(messages) -> str:
        for m in reversed(messages):
            if m.get("role") == "assistant" and isinstance(m.get("content"), str):
                return m["content"].strip()
        return ""
