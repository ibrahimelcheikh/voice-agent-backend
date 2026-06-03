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
    "You are Aria, the warm and efficient AI receptionist for the Golden Fork restaurant "
    "chain (locations: Downtown, Midtown, Uptown, Airport). You book tables, take orders, "
    "answer questions from the knowledge base, check reservations/orders, and transfer to a "
    "human when a customer is upset or the request is out of scope. Always use your tools to "
    "take real actions. Keep replies short and natural, like a phone call. When you have what "
    "you need, confirm and close politely."
)

SCENARIOS = {
    "reservation": [
        "Hi, I'd like to book a table for 4 this Saturday at 7pm.",
        "Downtown please. The name is John Smith, phone 415-555-0142.",
        "Great, thank you!",
    ],
    "order": [
        "Hi, I'd like to place a delivery order.",
        "Two burgers and one caesar salad. Name is Maria Santos, phone 415-555-0188.",
        "Deliver to 22 Oak Street. Thanks!",
    ],
    "faq": [
        "What are your hours?",
        "Is parking available?",
        "Do you have vegetarian options?",
    ],
    "complaint": [
        "My last delivery arrived completely cold and I'm really upset.",
        "No, I don't want a coupon, I want to speak to a manager right now.",
    ],
    "cancel": [
        "I need to cancel my reservation. My phone is 415-555-0142.",
        "Yes please cancel it. Thanks.",
    ],
}


class SimulateCall(BaseModel):
    scenario: str = "reservation"


@router.post("/simulate-call")
async def simulate_call(data: SimulateCall, db: AsyncSession = Depends(get_db)):
    scenario = data.scenario.lower()
    if scenario not in SCENARIOS:
        return {"success": False,
                "error": f"Unknown scenario. Choose one of {list(SCENARIOS)}"}

    customer_turns = SCENARIOS[scenario]
    transcript_lines, escalated, tools_used = await _run_conversation(customer_turns, db)

    agent = (await db.execute(
        select(Agent).where(Agent.type == "inbound")
    )).scalars().first()

    transcript = "\n".join(transcript_lines)
    outcome = CallOutcome.escalated if escalated else CallOutcome.resolved
    score = 72.0 if escalated else 91.0
    started = datetime.utcnow()

    call = Call(
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


async def _run_conversation(customer_turns, db):
    """Drive the LLM through the scripted customer turns; returns
    (transcript_lines, escalated, tools_used)."""
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
                        result_text, payload = await execute_tool(tc.function.name, args, db)
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
                transcript.append(f"Aria: {reply}")
                messages.append({"role": "assistant", "content": reply})
                break
        return transcript, escalated, tools_used
    except Exception as e:
        # Deterministic fallback so the demo always returns something useful.
        print(f"[demo] LLM simulation unavailable ({type(e).__name__}: {e}); using canned transcript")
        return _canned(customer_turns), ("complaint" in str(customer_turns).lower()), tools_used


def _canned(customer_turns):
    lines = []
    replies = [
        "Thank you for calling Golden Fork, this is Aria. How can I help you today?",
        "Of course! Let me take care of that for you.",
        "All set — is there anything else I can help with?",
        "Wonderful, have a great day!",
    ]
    for i, turn in enumerate(customer_turns):
        lines.append(f"Aria: {replies[min(i, len(replies) - 1)]}")
        lines.append(f"Customer: {turn}")
    lines.append("Aria: Thank you, goodbye!")
    return lines
