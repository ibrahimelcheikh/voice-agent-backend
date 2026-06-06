"""
Demo call simulator — run a full AI conversation for a scenario without a phone.

Drives Aria (the Golden Fork receptionist) through a scripted customer using
OpenAI function-calling. Tool calls hit the real database, so a simulated
"reservation" scenario actually creates a reservation row. The full transcript
is saved as a Call record so it shows up in analytics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Call, Agent, CallDirection, CallOutcome
from app.core.config import settings
from app.agents.tools import TOOL_SCHEMAS, execute_tool
from pydantic import BaseModel
from datetime import datetime
import json

router = APIRouter()

ARIA_PROMPT = (
    "You are the AI receptionist for Prime Health Clinic. You may ONLY state information "
    "returned by your tools (clinic functions). NEVER invent appointment times, prices, doctor "
    "names, or policies. Always use your tools to fetch real data, then phrase it naturally. "
    "Collect the patient's name and phone before booking. Keep replies short and natural, like a "
    "phone call. If a tool returns no data, offer to connect to staff. Confirm and close politely."
)

SCENARIOS = {
    "book": [
        "Hi, I'd like to book an appointment with the dentist this Friday at 10am.",
        "My name is Omar Hassan, phone 415-555-0142.",
        "Great, thank you!",
    ],
    "hours": [
        "What are your opening hours?",
        "Where are you located?",
        "Thanks, that's all.",
    ],
    "services": [
        "What services do you offer and how much is a dental cleaning?",
        "And do you accept Bupa insurance?",
        "Perfect, thank you.",
    ],
    "reschedule": [
        "I need to move my appointment to next Tuesday at 3pm. My phone is 415-555-0188.",
        "Yes please, thank you.",
    ],
    "emergency": [
        "I think I'm having chest pains right now.",
        "Please connect me to someone.",
    ],
}


class SimulateCall(BaseModel):
    scenario: str = "book"


@router.post("/simulate-call")
async def simulate_call(data: SimulateCall, db: AsyncSession = Depends(get_db)):
    scenario = data.scenario.lower()
    if scenario not in SCENARIOS:
        return {"success": False,
                "error": f"Unknown scenario. Choose one of {list(SCENARIOS)}"}

    # Run the simulator against a real tenant so the tool calls hit tenant-scoped data
    # (defaults to the original clinic).
    from app.services.tenant_service import resolve_tenant_id
    tenant_id = await resolve_tenant_id(db, None)

    customer_turns = SCENARIOS[scenario]
    transcript_lines, escalated, tools_used = await _run_conversation(
        customer_turns, db, tenant_id)

    aq = select(Agent).where(Agent.type == "inbound")
    if tenant_id:
        aq = aq.where(Agent.tenant_id == tenant_id)
    agent = (await db.execute(aq)).scalars().first()

    transcript = "\n".join(transcript_lines)
    outcome = CallOutcome.escalated if escalated else CallOutcome.resolved
    score = 72.0 if escalated else 91.0
    started = datetime.utcnow()

    call = Call(
        tenant_id=tenant_id,
        agent_id=agent.id if agent else None,
        direction=CallDirection.inbound,
        caller_number="+14155550142",
        called_number=settings.TWILIO_PHONE_NUMBER,
        duration_seconds=len(transcript_lines) * 12,
        outcome=outcome,
        ai_score=score,
        transcript=transcript,
        extracted_data={"scenario": scenario, "tools_used": tools_used},
        rule_violations=[],
        sentiment_data={"overall": "negative" if escalated else "positive",
                        "timeline": [0.2, 0.4, -0.6, -0.4, -0.5] if escalated else [0.3, 0.5, 0.7, 0.8, 0.9]},
        ai_analysis={"score": score,
                     "summary": f"Simulated {scenario} call ({'escalated' if escalated else 'resolved'}).",
                     "recommendations": ["Demo simulation"]},
        started_at=started,
        ended_at=started,
    )
    db.add(call)
    await db.commit()

    return {"success": True, "data": {
        "call_id": call.id,
        "scenario": scenario,
        "outcome": outcome.value,
        "escalated": escalated,
        "tools_used": tools_used,
        "transcript": transcript,
        "transcript_lines": transcript_lines,
    }}


async def _run_conversation(customer_turns, db, tenant_id=None):
    """Drive the LLM through the scripted customer turns; returns
    (transcript_lines, escalated, tools_used). Tool calls are tenant-scoped."""
    transcript, tools_used, escalated = [], [], False
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        messages = [{"role": "system", "content": ARIA_PROMPT}]

        for turn in customer_turns:
            transcript.append(f"Customer: {turn}")
            messages.append({"role": "user", "content": turn})

            # Resolve any tool calls until Aria produces a spoken reply.
            for _ in range(6):
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini", messages=messages,
                    tools=TOOL_SCHEMAS, tool_choice="auto", max_tokens=300,
                )
                msg = resp.choices[0].message
                if msg.tool_calls:
                    messages.append({
                        "role": "assistant", "content": msg.content or "",
                        "tool_calls": [
                            {"id": tc.id, "type": "function",
                             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                            for tc in msg.tool_calls
                        ],
                    })
                    for tc in msg.tool_calls:
                        try:
                            args = json.loads(tc.function.arguments or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        result_text, payload = await execute_tool(tc.function.name, args, db,
                                                                  tenant_id=tenant_id)
                        tools_used.append(tc.function.name)
                        if payload.get("escalated"):
                            escalated = True
                        messages.append({
                            "role": "tool", "tool_call_id": tc.id,
                            "content": json.dumps({"result": result_text, **payload}),
                        })
                    continue
                # Spoken reply
                reply = msg.content or "..."
                transcript.append(f"Assistant: {reply}")
                messages.append({"role": "assistant", "content": reply})
                break
        return transcript, escalated, tools_used
    except Exception as e:
        # Deterministic fallback so the demo always returns something useful.
        print(f"[demo] LLM simulation unavailable ({type(e).__name__}: {e}); using canned transcript")
        return _canned(customer_turns), ("emergency" in str(customer_turns).lower()
                                         or "chest pain" in str(customer_turns).lower()), tools_used


def _canned(customer_turns):
    lines = []
    replies = [
        "Thank you for calling Prime Health Clinic. This is the AI assistant, how may I help you?",
        "Of course! Let me check that for you.",
        "All set — is there anything else I can help with?",
        "Thank you for calling, have a great day!",
    ]
    for i, turn in enumerate(customer_turns):
        lines.append(f"Assistant: {replies[min(i, len(replies) - 1)]}")
        lines.append(f"Customer: {turn}")
    lines.append("Assistant: Thank you, goodbye!")
    return lines
