"""
Niche function sets — the tenant's niche decides which functions the agent loads and
which intents the classifier may choose from.

A restaurant agent must never try to "book a doctor", and a clinic agent must never try
to "take an order". This module is the single place that maps a tenant's `niche` to:

  * the function registry the guardrail runs (intent -> coroutine, real DB data),
  * the exact set of intents the classifier is allowed to emit,
  * the entity fields the classifier extracts,
  * which intents are "actionable" (can sit pending awaiting confirmation),
  * the role/voice framing for the classifier + the strict reply wrapper.

The anti-hallucination contract is unchanged: classifier -> real DB function -> grounded
LLM reply, never invent data. This module just swaps WHICH real functions are in play.

Niche groups:
  clinic, dental, spa             -> appointments + provider availability + services + FAQ
  restaurant                      -> reservations + menu-aware orders + menu lookup + FAQ
  real_estate, automotive, services -> lead capture + FAQ
ALL niches                        -> FAQ (tenant knowledge base) + caller recognition
"""
from dataclasses import dataclass, field

from app.agents.clinic_functions import CLINIC_FUNCTIONS
from app.agents.restaurant_functions import RESTAURANT_FUNCTIONS
from app.agents.lead_functions import LEAD_FUNCTIONS
from app.agents.common_functions import faq_lookup

# Intents handled by the guardrail itself (no DB function) — appended to every niche so the
# agent can always hand off, end the call, or ask for clarification.
_UNIVERSAL_INTENTS = ["faq", "speak_to_human", "end_call", "unclear"]

# Shared entity property schemas (OpenAI function-call parameters).
_P = {
    "patient_name": {"type": "string"},
    "customer_name": {"type": "string", "description": "The caller's name."},
    "phone": {"type": "string", "description": "Digits only if given."},
    "doctor": {"type": "string", "description": "Doctor name or specialty mentioned."},
    "service": {"type": "string", "description": "The treatment/service the caller wants to "
                "book (e.g. Botox, HydraFacial, Laser Hair Removal)."},
    "date": {"type": "string", "description": "Resolved date, YYYY-MM-DD."},
    "time": {"type": "string", "description": "Resolved time, 24h HH:MM."},
    "new_date": {"type": "string", "description": "Reschedule target date, YYYY-MM-DD."},
    "new_time": {"type": "string", "description": "Reschedule target time, HH:MM."},
    "reason": {"type": "string", "description": "Reason for the visit."},
    "appointment_id": {"type": "string"},
    "insurance_provider": {"type": "string"},
    "party_size": {"type": "integer", "description": "Number of diners."},
    "notes": {"type": "string", "description": "Special requests / notes."},
    "reservation_id": {"type": "string"},
    "order_id": {"type": "string"},
    "pickup_time": {"type": "string", "description": "Requested pickup time, 24h HH:MM, or 'ASAP'."},
    "menu_query": {"type": "string", "description": "Menu item or category the caller is asking about."},
    "items": {
        "type": "array",
        "description": "The COMPLETE list of items the caller has ordered so far. Always "
                       "include every item ordered this call, merging any newly added ones.",
        "items": {"type": "object", "properties": {
            "name": {"type": "string", "description": "The menu item name as the caller said it."},
            "quantity": {"type": "integer", "description": "How many. Default 1."},
        }, "required": ["name"]},
    },
    "lead_type": {"type": "string",
                  "description": "What the caller wants: property type (real estate), vehicle "
                                 "interest (automotive), or service needed (services)."},
    "budget": {"type": "string", "description": "Budget the caller mentioned, free-form."},
    "requirements": {"type": "string", "description": "Extra detail / requirements / notes."},
    "query": {"type": "string", "description": "The general question being asked (for FAQ)."},
}


@dataclass
class NicheSpec:
    """Everything the guardrail needs to run one niche. See module docstring."""
    key: str                              # canonical group: clinic | restaurant | lead
    functions: dict                       # intent -> coroutine
    domain_intents: list                  # niche intents (universal ones appended)
    entity_props: dict                    # JSON-schema props the classifier extracts
    function_args: dict                   # intent -> [entity keys passed to the function]
    actionable: set                       # intents that can sit pending awaiting confirmation
    reschedule_intents: set               # intents whose relative date fills `new_date`
    list_entities: set                    # entity keys whose value is a list (e.g. items)
    classifier_subject: str               # "a medical-clinic phone call"
    assistant_role: str                   # "the AI receptionist for a medical clinic"
    settled_noun: str                     # "appointment" — used in the settled-context rules
    intent_outcome: dict = field(default_factory=dict)   # success intent -> recorded outcome
    # What counts as a generic FAQ question for THIS niche. Kept niche-specific so a
    # restaurant doesn't route food/menu/price questions into the knowledge-base FAQ.
    faq_examples: str = "hours, location, policies, pricing, products"
    # Extra niche-specific routing guidance appended to the classifier system prompt — e.g.
    # for a restaurant, "what's on the menu / how much is X" must be menu_lookup, not faq.
    routing_hint: str = ""

    @property
    def intents(self) -> list:
        # Universal intents always available; de-duplicate while preserving order.
        seen, out = set(), []
        for i in self.domain_intents + _UNIVERSAL_INTENTS:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out

    @property
    def entity_keys(self) -> list:
        return list(self.entity_props)

    def router_tool(self) -> list:
        """The single function the classifier is forced to call for this niche."""
        props = {"intent": {"type": "string", "enum": self.intents},
                 "language": {"type": "string", "enum": ["en", "ar", "fr", "es"],
                              "description": "Language the caller is speaking."}}
        props.update(self.entity_props)
        return [{"type": "function", "function": {
            "name": "route_intent",
            "description": f"Classify the caller's latest message into one intent for "
                           f"{self.classifier_subject} and extract any entities.",
            "parameters": {"type": "object", "properties": props,
                           "required": ["intent", "language"]},
        }}]


# Add FAQ to every niche's function set + args (the knowledge-base engine, all niches).
def _with_faq(functions: dict, function_args: dict):
    functions = dict(functions)
    functions["faq"] = faq_lookup
    function_args = dict(function_args)
    function_args["faq"] = ["query"]
    return functions, function_args


# ── Clinic / dental / spa — appointments (UNCHANGED behavior) ─────────────────
_CLINIC_FUNCS, _CLINIC_ARGS = _with_faq(
    CLINIC_FUNCTIONS,
    {
        "book_appointment": ["patient_name", "phone", "doctor", "service", "date", "time", "reason"],
        "cancel_appointment": ["phone", "appointment_id"],
        "reschedule_appointment": ["phone", "new_date", "new_time", "appointment_id"],
        "confirm_appointment": ["phone", "appointment_id"],
        "check_appointment": ["phone"],
        "clinic_hours": [],
        "clinic_location": [],
        "services_offered": [],
        "doctor_availability": ["doctor", "date"],
        "insurance_question": ["insurance_provider"],
    },
)

CLINIC_SPEC = NicheSpec(
    key="clinic",
    functions=_CLINIC_FUNCS,
    domain_intents=[
        "book_appointment", "cancel_appointment", "reschedule_appointment",
        "confirm_appointment", "check_appointment", "clinic_hours", "clinic_location",
        "services_offered", "doctor_availability", "insurance_question",
    ],
    entity_props={k: _P[k] for k in (
        "patient_name", "phone", "doctor", "service", "date", "time", "new_date", "new_time",
        "reason", "appointment_id", "insurance_provider", "query")},
    function_args=_CLINIC_ARGS,
    actionable={"book_appointment", "cancel_appointment", "reschedule_appointment",
                "confirm_appointment"},
    reschedule_intents={"reschedule_appointment"},
    list_entities=set(),
    classifier_subject="a medical-clinic phone call",
    assistant_role="the AI receptionist for a medical clinic",
    settled_noun="appointment",
    intent_outcome={
        "confirm_appointment": "confirmed",
        "reschedule_appointment": "rescheduled",
        "cancel_appointment": "cancelled",
    },
)


# ── Restaurant — reservations + menu-aware orders ─────────────────────────────
_RESTAURANT_FUNCS, _RESTAURANT_ARGS = _with_faq(
    RESTAURANT_FUNCTIONS,
    {
        "create_reservation": ["customer_name", "phone", "party_size", "date", "time", "notes"],
        "modify_reservation": ["phone", "reservation_id", "new_date", "new_time", "party_size"],
        "cancel_reservation": ["phone", "reservation_id"],
        "check_reservation": ["phone"],
        "menu_lookup": ["menu_query"],
        "take_order": ["items", "customer_name", "phone", "pickup_time"],
        "check_order": ["phone", "order_id"],
    },
)

RESTAURANT_SPEC = NicheSpec(
    key="restaurant",
    functions=_RESTAURANT_FUNCS,
    domain_intents=[
        "create_reservation", "modify_reservation", "cancel_reservation",
        "check_reservation", "menu_lookup", "take_order", "check_order",
    ],
    entity_props={k: _P[k] for k in (
        "customer_name", "phone", "party_size", "date", "time", "new_date", "new_time",
        "notes", "reservation_id", "items", "pickup_time", "order_id", "menu_query",
        "query")},
    function_args=_RESTAURANT_ARGS,
    actionable={"create_reservation", "modify_reservation", "cancel_reservation",
                "take_order"},
    reschedule_intents={"modify_reservation"},
    list_entities={"items"},
    classifier_subject="a restaurant phone call (reservations and pickup orders)",
    assistant_role="the AI host for a restaurant",
    settled_noun="reservation or order",
    # For a restaurant, food/menu questions are NOT FAQ — they read the real menu.
    faq_examples="opening hours, location, parking, or general policies (NOT food, menu, "
                 "dishes, or prices — those are menu_lookup)",
    routing_hint=(
        "This is a RESTAURANT. Any question about the FOOD or MENU — what's on the menu, "
        "what they have / serve / offer to eat, what dishes or items are available, "
        "naming the items, what's good / popular / the best seller, main dishes, or the "
        "PRICE of a food item (e.g. \"what do you have\", \"what's on your menu\", "
        "\"name the items\", \"how much is the shawarma\") — MUST be classified as intent "
        "'menu_lookup', NEVER 'faq'. Put the caller's words in the menu_query entity. "
        "Use 'take_order' only when the caller is actually placing an order. Reserve 'faq' "
        "for non-food questions like opening hours, location, parking, or policies."
    ),
)


# ── Real estate / automotive / services — lead capture ────────────────────────
_LEAD_FUNCS, _LEAD_ARGS = _with_faq(
    LEAD_FUNCTIONS,
    {
        "capture_lead": ["customer_name", "phone", "lead_type", "budget", "requirements"],
        "check_lead": ["phone"],
    },
)

LEAD_SPEC = NicheSpec(
    key="lead",
    functions=_LEAD_FUNCS,
    domain_intents=["capture_lead", "check_lead"],
    entity_props={k: _P[k] for k in (
        "customer_name", "phone", "lead_type", "budget", "requirements", "query")},
    function_args=_LEAD_ARGS,
    actionable={"capture_lead"},
    reschedule_intents=set(),
    list_entities=set(),
    classifier_subject="an inbound enquiry call where the goal is to capture the caller's "
                       "details as a lead",
    assistant_role="the AI assistant capturing enquiries for the business",
    settled_noun="enquiry",
)


_NICHE_TO_SPEC = {
    "clinic": CLINIC_SPEC,
    "dental": CLINIC_SPEC,
    "spa": CLINIC_SPEC,
    "restaurant": RESTAURANT_SPEC,
    "real_estate": LEAD_SPEC,
    "automotive": LEAD_SPEC,
    "services": LEAD_SPEC,
}


def get_niche_spec(niche: str | None) -> NicheSpec:
    """Resolve a tenant's niche to its function-set spec. Unknown/None falls back to the
    clinic spec (the original behavior), so any misconfiguration degrades safely."""
    return _NICHE_TO_SPEC.get((niche or "").lower(), CLINIC_SPEC)
