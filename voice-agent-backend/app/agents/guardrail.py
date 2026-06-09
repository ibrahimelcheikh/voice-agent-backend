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

from app.agents.niches import get_niche_spec

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

# Which intents/entities/functions are in play is NICHE-SPECIFIC and now lives in
# app/agents/niches.py (NicheSpec). The GuardrailBrain loads the spec for the tenant's
# niche, so a restaurant agent never offers "book_appointment" and a clinic agent never
# offers "take_order". The deterministic helpers below (affirmation / closing / relative
# date) are niche-agnostic and shared by every niche.

# Per-intent guidance when a primary "create" action fired but isn't complete yet (a
# required detail is missing, or — for orders — the caller named something off-menu). The
# clinic's book_appointment text is kept verbatim so existing behavior is unchanged.
_INCOMPLETE_TASK = {
    "book_appointment": ("The booking is not complete. Politely ask only for the missing "
                         "detail(s); do not confirm a booking."),
    "create_reservation": ("The reservation is not complete. Politely ask only for the "
                           "missing detail(s); do not confirm it yet."),
    "take_order": ("The order is not complete, or includes something not on the menu. "
                   "Politely tell the caller what is unavailable (offer a real menu "
                   "alternative) or ask for the missing detail(s); NEVER invent a dish or "
                   "price; do not confirm the order yet."),
    "capture_lead": ("Some details are still missing. Politely ask only for the missing "
                     "detail(s) before confirming."),
}


def _full_menu_task(data: dict) -> str:
    """Build the per-turn task for a full-menu readback so the agent reads a few real items
    (name + price) in ONE concise reply and offers the rest — never trailing off after one
    item. Uses the actual items returned by menu_lookup (already tenant-scoped + available)."""
    items = [i for i in (data.get("items") or []) if isinstance(i, dict) and i.get("name")]
    head = items[:3]
    sample = ", ".join(f"{i['name']} {i.get('price', '')}".strip() for i in head)
    remaining = max(0, len(items) - len(head))
    rest = (f", then offer the remaining {remaining} (e.g. \"want to hear the rest?\")"
            if remaining else "")
    return (
        "The caller asked what's on the menu. Read the menu out loud in ONE short, natural "
        "spoken sentence: name the first 2-3 items WITH their prices"
        f"{rest}. "
        f"Say it like: \"We have {sample} — want to hear the rest?\". "
        "Use ONLY the real item names and prices from the data below; do NOT invent items; "
        "do NOT trail off after a single item. This one reply may use up to ~25 words to fit "
        "the 2-3 items and prices."
    )

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


# Closing / farewell phrases. When the caller signals they're finished, the call must END
# — even right after a booking or confirmation, where the dialogue context would otherwise
# tempt the classifier to (mis)tag a closer as confirm_appointment.
_STRONG_CLOSERS = (
    "that's it", "thats it", "that is it", "that's all", "thats all", "that is all",
    "that'll be all", "thatll be all", "that will be all", "no thanks", "no thank you",
    "no that's all", "no thats all", "nothing else", "i'm done", "im done", "i am done",
    "we're done", "were done", "all done", "goodbye", "good bye", "bye bye",
    "have a good day", "have a great day", "take care",
)
# A real farewell/thanks word — needed for the "pure sign-off" check below.
_FAREWELL_CORE = {"thank", "thanks", "thankyou", "thx", "ty", "bye", "goodbye", "cheers",
                  "done"}
# Filler that may pad a sign-off ("okay, thank you so much!") without changing that it's
# a closer. Deliberately excludes words like "correct"/"right" that mark an acknowledgement.
_CLOSING_FILLER = {"ok", "okay", "alright", "alrighty", "great", "perfect", "cool",
                   "awesome", "good", "you", "so", "much", "very", "really", "appreciate",
                   "it", "yes", "yeah", "yep", "no", "nope", "and", "that's", "thats",
                   "all", "now", "a", "lot"}


def _is_closing(text: str) -> bool:
    """True if the caller is signing off (that's it / that's all / no thanks / thank you /
    goodbye / I'm done). Deterministic so a closer is never mis-tagged as confirm_appointment
    in a post-booking context. NOTE: 'yes that's correct' is NOT closing — it's an
    acknowledgement (handled separately)."""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s']", " ", t)      # strip punctuation
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return False
    for phrase in _STRONG_CLOSERS:
        if phrase in t:
            return True
    # Pure sign-off: every word is filler/thanks/farewell AND at least one is a real
    # farewell word ("thank you", "thanks!", "okay bye"). 'ok great' has no farewell word,
    # so it is treated as a plain acknowledgement, not an end-of-call.
    tokens = t.split()
    has_farewell = any(tok in _FAREWELL_CORE for tok in tokens)
    only_filler = all(tok in _FAREWELL_CORE or tok in _CLOSING_FILLER for tok in tokens)
    return has_farewell and only_filler


class GuardrailBrain:
    """Framework-agnostic guardrail logic. One instance per call."""

    def __init__(self, *, openai_api_key: str, today: str, model: str = "gpt-4o-mini",
                 max_unclear: int = 5, seed_entities: dict | None = None,
                 pending_intent: str | None = None, tenant_id: str | None = None,
                 niche: str | None = None, normalize_items_to_english: bool = False):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self._model = model
        self._today = today
        # Phase 3b fix: when the caller speaks a non-English language (the Arabic agent sets
        # this True), the classifier must output order item names as the EXACT English menu
        # names so the pure-English menu matcher (restaurant_functions.take_order) matches them.
        # English calls leave this False -> the classifier prompt is byte-for-byte unchanged.
        # _menu_names is the tenant's real menu, loaded once on demand and cached for the call.
        self._normalize_items = normalize_items_to_english
        self._menu_names: list | None = None
        # Tenant whose data this call operates on. Passed into every data function so
        # the agent can only ever read/write THIS business's data — no cross-tenant leak.
        self._tenant_id = tenant_id
        # The tenant's niche decides which function set + intents are in play (clinic ->
        # appointments, restaurant -> reservations/orders, real_estate/automotive/services
        # -> lead capture). Defaults to the clinic spec when unknown.
        self._niche = niche
        self._spec = get_niche_spec(niche)
        # Human-readable today (with weekday) so the classifier can compute "next Monday".
        try:
            self._today_human = date.fromisoformat(today).strftime("%A, %B %d, %Y")
        except (ValueError, TypeError):
            self._today_human = today
        # Lenient by default: only hand off to staff after many genuinely-unintelligible
        # turns. The streak resets on ANY real intent / new entity / confirmation, so a
        # caller who is actually being helped never hits this.
        self._max_unclear = max_unclear

        # Outbound reminder calls seed the entities (appointment_id, phone) and a pending
        # intent (confirm_appointment) up front: the agent already knows which appointment
        # this is, so confirm/reschedule/cancel target it directly and a bare "yes"
        # confirms it without re-collecting any details.
        self.entities: dict = dict(seed_entities or {})
        self.language = "en"
        self._language_locked = False
        self._unclear_streak = 0
        # Last actionable intent awaiting confirmation / a missing detail. A follow-up
        # "yes" or a bare detail (phone, time) resolves back to this instead of looking
        # like an out-of-context, unclear utterance.
        self._pending_intent: str | None = pending_intent
        # True once an appointment has been booked/confirmed (or rescheduled/cancelled)
        # this call. Guards against the re-confirmation loop: a follow-up affirmation after
        # a settled booking is a simple acknowledgement, NOT a request to re-run
        # confirm_appointment and re-read the details. Reminder calls start False (the
        # appointment is still unconfirmed and the caller is about to confirm it once).
        self._settled = False
        # For outbound reminders: the result to record on the appointment. Defaults to
        # "answered" (a human picked up) and upgrades to confirmed/rescheduled/cancelled
        # as the patient acts.
        self.reminder_outcome: str | None = None

    def snapshot(self) -> dict:
        return {"language": self.language, "entities": dict(self.entities),
                "reminder_outcome": self.reminder_outcome}

    async def decide(self, user_text: str, last_assistant: str = "") -> dict:
        """Classify -> fetch real data -> build a strict LLM instruction.

        Returns {instruction, intent, data, end (reason|None), transfer (bool)}.
        Never raises — on error it returns a safe "connect to staff" instruction.
        """
        t0 = time.perf_counter()
        try:
            intent, extracted, language = await self._classify(
                user_text, last_assistant, self._pending_intent, self.entities,
                settled=self._settled)
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
        closing = _is_closing(user_text)
        # Fix 2 — closing/farewell phrases ALWAYS end the call, with priority over any
        # pending action. Right after a booking the dialogue context otherwise tempts the
        # classifier to tag "okay that's it, thank you" as confirm_appointment; this stops
        # that and lets the agent give the goodbye and hang up.
        if closing:
            if intent != "end_call":
                logger.info("👋 closing phrase %r -> end_call (was %s)", user_text, intent)
            intent = "end_call"
        # Fix 1 & 3 — never re-confirm/re-read an appointment that's already settled this
        # call. Once we've booked and read the appointment back, a follow-up affirmation
        # ("yes", "that's correct", "great") is a simple acknowledgement, not a request to
        # run confirm_appointment again. (Reminder calls start unsettled, so the caller's
        # first confirmation of an existing booking still runs once.)
        elif self._settled and (intent == "confirm_appointment"
                                or (affirmative and intent in ("unclear", "end_call"))):
            logger.info("👍 acknowledgement of already-settled appointment %r (was %s)",
                        user_text, intent)
            intent = "_acknowledge"
        # Backstop for the classifier: a plain confirmation while an action is pending
        # COMPLETES that action — it is never "unclear" or "end_call" noise. The
        # accumulated entities are carried forward so the function fires with everything
        # collected across the whole conversation.
        elif affirmative and self._pending_intent and intent in ("unclear", "end_call"):
            logger.info("✅ affirmative %r resolved to pending intent %s",
                        user_text, self._pending_intent)
            intent = self._pending_intent

        # end_call may ONLY fire on a CLEAR, deterministic closing phrase (_is_closing). The
        # classifier sometimes mis-tags vague/incomplete fragments — "you can do", "okay",
        # "I suppose", "go ahead", "yeah" — as end_call and hangs up mid-conversation. If it
        # returned end_call but the utterance is NOT a clear closer (and wasn't resolved to a
        # pending action above), do NOT end the call — treat it as continuation ('unclear')
        # and ask one short clarifying question instead of saying goodbye.
        if intent == "end_call" and not closing:
            logger.info("🚫 classifier said end_call on non-closing fragment %r — "
                        "NOT hanging up; treating as continuation", user_text)
            intent = "unclear"

        logger.info("🧭 intent=%s lang=%s entities=%s pending=%s settled=%s in %.0fms",
                    intent, language, extracted, self._pending_intent, self._settled,
                    (time.perf_counter() - t0) * 1000)

        if not self._language_locked and language in LANGUAGES:
            self.language = language
            self._language_locked = True

        # Merge (never overwrite-and-forget) entities across turns. `contributed` tracks
        # whether this turn added/changed any detail — a turn that moves the booking
        # forward must reset the unclear streak even if the intent looked thin. List
        # entities (e.g. a restaurant order's `items`) are REPLACED with the latest
        # non-empty extraction: the classifier is told to always return the full running
        # list, so the newest one is authoritative.
        contributed = False
        for k in self._spec.entity_keys:
            val = extracted.get(k)
            if not val:
                continue
            if k in self._spec.list_entities:
                if self.entities.get(k) != val:
                    self.entities[k] = val
                    contributed = True
            elif self.entities.get(k) != val:
                self.entities[k] = val
                contributed = True

        # Deterministic relative-date resolution — so we never ask the caller for a
        # calendar date even if the classifier left it relative/blank.
        resolved = _resolve_relative_date(user_text, self._today)
        if resolved:
            field = "new_date" if intent in self._spec.reschedule_intents else "date"
            if not _is_iso_date(self.entities.get(field)):
                self.entities[field] = resolved
                contributed = True
                logger.info("📅 resolved relative date -> %s (field=%s)", resolved, field)

        if intent == "_acknowledge":
            # Already-settled appointment + a bare acknowledgement: respond briefly and
            # DO NOT call any function or re-read the appointment (Fix 1 & 3).
            self._unclear_streak = 0
            noun = self._spec.settled_noun
            return {"instruction": self._wrap(last_assistant,
                    {"situation": f"The {noun} is already booked and confirmed; the caller "
                                  "is simply acknowledging — not asking for anything new.",
                     "task": "Give a brief acknowledgement such as \"You're all set — anything "
                             f"else?\". Do NOT repeat or re-read the {noun} details, and do "
                             "not state any new information."}),
                    "intent": "acknowledge", "data": {}, "end": None, "transfer": False}

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
        if intent in self._spec.actionable:
            self._pending_intent = intent

        func = self._spec.functions.get(intent)
        data = {}
        if func:
            kwargs = {k: self.entities.get(k) for k in self._spec.function_args.get(intent, [])}
            # Scope every data function to this call's tenant (anti-cross-tenant guard).
            kwargs["tenant_id"] = self._tenant_id
            # [AR-DIAG] On the Arabic path, log the order item names AS PASSED to take_order
            # (post-normalization) so we can confirm they are now English menu names, not Arabic.
            if intent == "take_order" and self._normalize_items:
                _names = [it.get("name") for it in (kwargs.get("items") or [])
                          if isinstance(it, dict)]
                logger.info("[AR-DIAG] take_order items (normalized) = %s", _names)
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
        # can't accidentally repeat it (e.g. re-book the same appointment), and record
        # the reminder outcome (confirmed / rescheduled / cancelled).
        if intent in self._spec.actionable and isinstance(data, dict) and data.get("success"):
            self._pending_intent = None
            # Mark settled so a follow-up affirmation acknowledges rather than re-running
            # the action + re-reading it back (the re-confirmation loop).
            self._settled = True
            if intent in self._spec.intent_outcome:
                self.reminder_outcome = self._spec.intent_outcome[intent]

        payload = {"intent": intent, "data": data}
        if (isinstance(data, dict) and not data.get("success") and intent == "take_order"
                and data.get("reason") in ("awaiting_items", "no_items")):
            # The caller wants to order but named no items yet (intro phrase, or intro + items
            # split across turns). Ask what they'd like — NEVER claim the menu/order is empty.
            payload["task"] = (
                "The caller wants to place an order but has NOT named any items yet. Warmly ask "
                "what they would like to order, e.g. \"Sure! What would you like?\". The full menu "
                "IS available — NEVER say the menu is empty, the order is empty, or that you can't "
                "process the order, and do NOT claim anything is unavailable.")
        elif isinstance(data, dict) and not data.get("success") and intent in _INCOMPLETE_TASK:
            payload["task"] = _INCOMPLETE_TASK[intent]
        # Full-menu readback: when menu_lookup returns the whole menu, give the LLM an
        # explicit, concrete task (the real item names + prices) so it reads 2-3 in ONE
        # concise sentence and offers the rest — instead of trailing off after one item.
        elif isinstance(data, dict) and data.get("is_full_menu") and data.get("found"):
            payload["task"] = _full_menu_task(data)
        return {"instruction": self._wrap(last_assistant, payload),
                "intent": intent, "data": data, "end": None, "transfer": False}

    async def _menu_item_names(self) -> list:
        """The tenant's real, available menu item names (English) — loaded ONCE per call from
        the niche's menu_lookup and cached. Used to normalize Arabic-spoken items to the exact
        English menu names. Returns [] (and caches it) when the niche has no menu / on error, so
        we never re-query every turn."""
        if self._menu_names is not None:
            return self._menu_names
        self._menu_names = []   # cache up-front so a failure isn't retried each turn
        fn = self._spec.functions.get("menu_lookup")
        if not fn:
            return self._menu_names
        try:
            data = await fn(tenant_id=self._tenant_id)   # no query -> full available menu
            self._menu_names = [i["name"] for i in (data.get("items") or [])
                                if isinstance(i, dict) and i.get("name")]
            logger.info("📋 loaded %d menu names for item normalization", len(self._menu_names))
        except Exception as e:
            logger.error("menu-name load failed: %s: %s", type(e).__name__, e)
        return self._menu_names

    async def _classify(self, user_text: str, last_assistant: str = "",
                        pending_intent: str | None = None, entities: dict | None = None,
                        settled: bool = False):
        sys = (
            f"You route {self._spec.classifier_subject}. Today is {self._today_human} "
            f"({self._today}). Classify the caller's latest message into exactly one intent "
            "and extract entities. ALWAYS compute relative dates yourself from today's date — "
            "'tomorrow', 'this Friday', 'next Monday at 3pm', 'next week' — into absolute "
            "YYYY-MM-DD and 24h HH:MM. NEVER leave a date relative and never expect the caller "
            "to give a calendar date. Detect the spoken language (en/ar/fr/es). "
            "Only classify 'end_call' for a CLEAR closing phrase — 'goodbye', 'bye', "
            "'that's all', 'that's it thank you', \"I'm done\", 'nothing else', 'no thanks "
            "bye' — even right after completing a request; a sign-off is NEVER a confirmation. "
            "Do NOT classify vague or incomplete fragments as 'end_call': 'you can do', 'you "
            "can do it', 'okay', 'I suppose', 'go ahead', 'yeah', 'sure', 'hmm', 'right' are "
            "NOT goodbyes. When the message is ambiguous or incomplete, do NOT end the call — "
            "classify it as 'unclear' (or the action already in progress) so the conversation "
            "continues. Use intent 'faq' for "
            f"general questions ({self._spec.faq_examples}). "
            "If the message is ambiguous or you cannot tell what they want, use intent 'unclear'."
        )
        # Niche-specific routing guidance (e.g. restaurant: menu/food/price questions are
        # menu_lookup, not faq). Empty for niches that need no extra steer.
        if self._spec.routing_hint:
            sys += "\n\n" + self._spec.routing_hint

        # Phase 3b fix — Arabic order item NORMALIZATION (Arabic agent only; English is untouched).
        # The DB/menu/matcher are English-only by design. A caller speaking Arabic says حمص/فلافل,
        # which would reach the English matcher as Arabic and fail. So, given the tenant's REAL
        # menu, tell the classifier to emit each order item's `name` as the EXACT English menu
        # name. The LLM also folds spelling variants of the same spoken word (فليفل/فلافل) onto the
        # same menu item. Quantities are unaffected. Only added when normalization is on AND the
        # niche has a menu with items to order.
        if self._normalize_items and "items" in self._spec.list_entities:
            menu_names = await self._menu_item_names()
            if menu_names:
                sys += (
                    "\n\nORDER ITEM NORMALIZATION (CRITICAL): This restaurant's EXACT menu items "
                    "are:\n  " + "; ".join(menu_names) + "\n"
                    "When you extract the `items` array, set each item's `name` to the EXACT "
                    "English menu name from the list above that the caller is referring to — even "
                    "when the caller speaks ARABIC (or another language) or uses a spelling "
                    "variant. Map by meaning: e.g. حمص -> the matching English item, فلافل or its "
                    "variant spelling فليفل -> the matching English item, شاورما دجاج -> the "
                    "chicken shawarma item, عصير ليمون -> the lemonade item. Two spellings of the "
                    "same spoken word MUST map to the SAME menu item. Output every item `name` in "
                    "English exactly as written in the list. Keep quantities as the caller said "
                    "them. Only if a named item is genuinely NOT on the list, keep the caller's "
                    "original words so it can be reported as unavailable."
                )

        # Give the classifier short-term memory of the dialogue so short replies — "yes",
        # "correct", a bare phone number or time — are interpreted against what the agent
        # just asked and the action already in progress, instead of looking unclear.
        ctx = []
        if last_assistant:
            ctx.append(f'The assistant just said: "{last_assistant}"')
        if settled:
            ctx.append(f"The {self._spec.settled_noun} has ALREADY been completed and "
                       "confirmed this call (the assistant has already read it back once).")
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
                "- If the caller signals they are finished (that's it / that's all / no "
                "thanks / thank you / goodbye / I'm done), classify as 'end_call' — even "
                "right after completing a request. A sign-off is never a confirmation.\n"
                + (f"- The {self._spec.settled_noun} is ALREADY confirmed. A bare "
                   "acknowledgement (yes / that's correct / great / okay / perfect) is NOT a "
                   "request to do it again — classify it as 'unclear' (a simple "
                   "acknowledgement) unless the caller clearly asks for something new.\n"
                   if settled else
                   "- If the assistant just asked the caller to confirm an action and the "
                   "caller responds affirmatively (yes / yeah / correct / that's right / "
                   "go ahead / sure / please do), classify the intent as the pending action "
                   f"({pending_intent or 'the action in progress'}) — NOT 'unclear' — and "
                   "carry the already-collected entities forward.\n")
                + "- If the caller gives a bare detail (a phone number, a name, a time, an "
                "item) that fills a missing field for the pending action, classify it as "
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
            tools=self._spec.router_tool(),
            tool_choice={"type": "function", "function": {"name": "route_intent"}},
            temperature=0,
            max_tokens=400,
            timeout=_CLASSIFY_TIMEOUT,
        )
        call = resp.choices[0].message.tool_calls[0]
        args = json.loads(call.function.arguments or "{}")
        intent = args.get("intent", "unclear")
        language = args.get("language", "en")
        extracted = {k: args[k] for k in self._spec.entity_keys if args.get(k)}
        return intent, extracted, language

    def _wrap(self, last_assistant: str, payload: dict) -> str:
        """Build the strict per-turn system instruction around a data payload."""
        lang_name = LANGUAGES.get(self.language, "English")
        guard = (
            f"You are {self._spec.assistant_role}. You may ONLY use the information provided "
            "below. NEVER invent any facts — times, prices, names, menu items, dishes, "
            "services, policies, availability, or insurance details. If the data is empty or a "
            "request failed, apologise briefly and offer to connect them to staff. When a date "
            "is already known, confirm it back to the caller (e.g. 'Monday, June 9') — NEVER "
            "ask the caller to provide a calendar date; relative dates like 'next Monday' are "
            "already resolved for you. You are on a PHONE call: reply in ONE short sentence, "
            "MAXIMUM 15 words, like a real receptionist. Never list more than 2-3 items — give "
            "only the top few then ask if they want more. "
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
                         on_end_call=None, on_state=None, tenant_id=None, niche=None, **kw):
                super().__init__(**kw)
                self._brain = GuardrailBrain(openai_api_key=openai_api_key, today=today,
                                             model=model, tenant_id=tenant_id, niche=niche)
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
