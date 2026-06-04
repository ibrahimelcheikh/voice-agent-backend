from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.models.models import WhatsAppConversation, WhatsAppMessage, Agent, BehaviorConfig
from app.core.config import settings
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

DEFAULT_WA_AGENT = "agt-002"
FALLBACK_SYSTEM_PROMPT = (
    "You are the WhatsApp assistant for Prime Health Clinic. Help patients with appointments, "
    "clinic hours, services, doctors, and insurance questions. Only share information you are "
    "sure of; if unsure, offer to connect them to staff. Be concise, warm, and professional. "
    "Keep replies under 80 words."
)


class SendMessage(BaseModel):
    contact_number: str
    message: str
    agent_id: str = DEFAULT_WA_AGENT


def _conv_dict(c: WhatsAppConversation) -> dict:
    return {"id": c.id, "agent_id": c.agent_id, "contact_number": c.contact_number,
            "contact_name": c.contact_name, "status": c.status,
            "message_count": c.message_count, "last_message": c.last_message,
            "last_message_at": str(c.last_message_at) if c.last_message_at else None}


@router.get("/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    convs = (await db.execute(
        select(WhatsAppConversation).order_by(desc(WhatsAppConversation.last_message_at))
    )).scalars().all()
    return {"success": True, "data": [_conv_dict(c) for c in convs]}


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, db: AsyncSession = Depends(get_db)):
    messages = (await db.execute(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == conv_id)
        .order_by(WhatsAppMessage.sent_at)
    )).scalars().all()
    return {"success": True, "data": [
        {"id": m.id, "role": m.role, "content": m.content, "sent_at": str(m.sent_at)}
        for m in messages
    ]}


async def _system_prompt_for(agent_id: str, db: AsyncSession) -> str:
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalars().first()
    if agent and agent.behavior_config_id:
        cfg = (await db.execute(
            select(BehaviorConfig).where(BehaviorConfig.id == agent.behavior_config_id)
        )).scalars().first()
        if cfg and cfg.system_prompt:
            return cfg.system_prompt
    return FALLBACK_SYSTEM_PROMPT


@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio WhatsApp webhook — incoming customer messages."""
    form_data = await request.form()
    from_number = form_data.get("From", "").replace("whatsapp:", "")
    message_body = form_data.get("Body", "")
    profile_name = form_data.get("ProfileName")

    conv = (await db.execute(
        select(WhatsAppConversation).where(WhatsAppConversation.contact_number == from_number)
    )).scalars().first()
    if not conv:
        conv = WhatsAppConversation(
            agent_id=DEFAULT_WA_AGENT, contact_number=from_number,
            contact_name=profile_name, status="active", message_count=0,
        )
        db.add(conv)
        await db.flush()

    if conv.status == "handed_off":
        # A human owns this thread now — record but don't auto-reply.
        db.add(WhatsAppMessage(conversation_id=conv.id, role="customer", content=message_body))
        conv.message_count += 1
        conv.last_message = message_body
        conv.last_message_at = datetime.utcnow()
        await db.commit()
        return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                        media_type="application/xml")

    db.add(WhatsAppMessage(conversation_id=conv.id, role="customer", content=message_body))

    history = (await db.execute(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == conv.id)
        .order_by(desc(WhatsAppMessage.sent_at))
        .limit(10)
    )).scalars().all()
    history = list(reversed(history))

    system_prompt = await _system_prompt_for(conv.agent_id, db)
    ai_response = await _generate_ai_response(system_prompt, history, message_body)

    db.add(WhatsAppMessage(conversation_id=conv.id, role="agent", content=ai_response))
    conv.message_count += 2
    conv.last_message = ai_response
    conv.last_message_at = datetime.utcnow()
    await db.commit()

    _send_whatsapp(from_number, ai_response)

    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{ai_response}</Message></Response>'
    return Response(content=twiml, media_type="application/xml")


@router.post("/send")
async def send_message(data: SendMessage, db: AsyncSession = Depends(get_db)):
    """Send a proactive WhatsApp message and record it in the conversation."""
    conv = (await db.execute(
        select(WhatsAppConversation).where(WhatsAppConversation.contact_number == data.contact_number)
    )).scalars().first()
    if not conv:
        conv = WhatsAppConversation(
            agent_id=data.agent_id, contact_number=data.contact_number,
            status="active", message_count=0,
        )
        db.add(conv)
        await db.flush()

    db.add(WhatsAppMessage(conversation_id=conv.id, role="agent", content=data.message))
    conv.message_count += 1
    conv.last_message = data.message
    conv.last_message_at = datetime.utcnow()
    await db.commit()

    sent = _send_whatsapp(data.contact_number, data.message)
    return {"success": True, "message": "Message sent" if sent else "Saved (Twilio send failed)",
            "data": {"conversation_id": conv.id}}


@router.put("/conversations/{conv_id}/handoff")
async def handoff(conv_id: str, db: AsyncSession = Depends(get_db)):
    """Hand the conversation off to a human team member."""
    conv = (await db.execute(
        select(WhatsAppConversation).where(WhatsAppConversation.id == conv_id)
    )).scalars().first()
    if not conv:
        return {"success": False, "error": "Conversation not found"}

    conv.status = "handed_off"
    handoff_msg = "You're being connected to a team member. They'll be with you shortly."
    db.add(WhatsAppMessage(conversation_id=conv.id, role="agent", content=handoff_msg))
    conv.message_count += 1
    conv.last_message = handoff_msg
    conv.last_message_at = datetime.utcnow()
    await db.commit()

    _send_whatsapp(conv.contact_number, handoff_msg)
    print(f"[whatsapp] NOTIFY HUMAN: conversation {conv.id} ({conv.contact_number}) needs attention")
    return {"success": True, "message": "Conversation handed off to a human",
            "data": {"conversation_id": conv.id, "status": conv.status}}


async def _generate_ai_response(system_prompt: str, history, latest: str) -> str:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({
                "role": "assistant" if m.role == "agent" else "user",
                "content": m.content,
            })
        if not history or history[-1].content != latest:
            messages.append({"role": "user", "content": latest})
        resp = await client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "Thank you for your message! A team member will get back to you shortly."


def _send_whatsapp(to_number: str, body: str) -> bool:
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            to=f"whatsapp:{to_number}",
            from_=f"whatsapp:{settings.TWILIO_PHONE_NUMBER}",
            body=body,
        )
        return True
    except Exception as e:
        print(f"[whatsapp] Twilio send error: {e}")
        return False
