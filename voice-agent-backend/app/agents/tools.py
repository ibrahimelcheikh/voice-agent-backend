"""
Clinic tool adapter — used by the demo simulator (/demo/simulate-call).

The live phone agent does NOT use these; it uses the IntentGuardrailProcessor
(app/agents/guardrail.py) which calls app.agents.clinic_functions directly. This
module just exposes the same clinic functions as OpenAI function-calling schemas
so the text-only demo can drive a scripted conversation against the real database.
"""
import json

from app.agents.clinic_functions import CLINIC_FUNCTIONS

# OpenAI function-calling schemas for the demo simulator.
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "book_appointment",
        "description": "Book a clinic appointment for a patient.",
        "parameters": {"type": "object", "properties": {
            "patient_name": {"type": "string"}, "phone": {"type": "string"},
            "doctor": {"type": "string", "description": "Doctor name or specialty"},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "time": {"type": "string", "description": "24h HH:MM"},
            "reason": {"type": "string"}},
            "required": ["patient_name", "phone", "date", "time"]}}},
    {"type": "function", "function": {
        "name": "cancel_appointment",
        "description": "Cancel a patient's appointment by phone number.",
        "parameters": {"type": "object", "properties": {
            "phone": {"type": "string"}, "appointment_id": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "reschedule_appointment",
        "description": "Move a patient's appointment to a new date/time.",
        "parameters": {"type": "object", "properties": {
            "phone": {"type": "string"}, "new_date": {"type": "string"},
            "new_time": {"type": "string"}}, "required": ["phone", "new_date", "new_time"]}}},
    {"type": "function", "function": {
        "name": "check_appointment",
        "description": "Look up a patient's upcoming appointment by phone number.",
        "parameters": {"type": "object", "properties": {"phone": {"type": "string"}},
                       "required": ["phone"]}}},
    {"type": "function", "function": {
        "name": "clinic_hours", "description": "Get the clinic's opening hours.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "clinic_location", "description": "Get the clinic's address and phone.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "services_offered", "description": "List the clinic's services and prices.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "doctor_availability",
        "description": "Check which days/hours a doctor is available.",
        "parameters": {"type": "object", "properties": {
            "doctor": {"type": "string"}, "date": {"type": "string"}},
            "required": ["doctor"]}}},
    {"type": "function", "function": {
        "name": "insurance_question",
        "description": "Check whether an insurance provider is accepted.",
        "parameters": {"type": "object", "properties": {
            "insurance_provider": {"type": "string"}}}}},
]

# Map demo function names to the kwargs each clinic function accepts.
_ARGS = {
    "book_appointment": ["patient_name", "phone", "doctor", "date", "time", "reason"],
    "cancel_appointment": ["phone", "appointment_id"],
    "reschedule_appointment": ["phone", "new_date", "new_time"],
    "check_appointment": ["phone"],
    "clinic_hours": [], "clinic_location": [], "services_offered": [],
    "doctor_availability": ["doctor", "date"],
    "insurance_question": ["insurance_provider"],
}


async def execute_tool(name: str, args: dict, db=None, tenant_id=None):
    """Run a clinic function by name. Returns (summary_text, data_payload).

    `db` is accepted for interface compatibility but unused — each clinic
    function opens its own session. `tenant_id` scopes every function to one business.
    """
    func = CLINIC_FUNCTIONS.get(name)
    if not func:
        return f"Unknown tool: {name}", {"error": "unknown_tool"}
    kwargs = {k: (args or {}).get(k) for k in _ARGS.get(name, [])}
    kwargs["tenant_id"] = tenant_id
    try:
        data = await func(**kwargs)
    except Exception as e:
        return "Sorry, I couldn't complete that — let me connect you to staff.", {"error": str(e)}
    return json.dumps(data, ensure_ascii=False), data
