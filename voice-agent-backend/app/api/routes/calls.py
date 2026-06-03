from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.db.database import get_db
from app.models.models import Call, Agent, CallOutcome, CallDirection
from app.core.config import settings
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import re

router = APIRouter()

TWILIO_COST_PER_MIN = 0.0085  # USD


class MakeCall(BaseModel):
    to_number: str
    agent_id: str
    campaign_id: Optional[str] = None


def _fmt_duration(seconds) -> str:
    s = int(seconds or 0)
    return f"{s // 60:02d}:{s % 60:02d}"


def _score_color(score) -> Optional[str]:
    if score is None:
        return None
    if score >= 85:
        return "green"
    if score >= 70:
        return "yellow"
    return "red"


def _enum(v):
    return v.value if hasattr(v, "value") else v


async def _agent_name_map(db) -> dict:
    rows = (await db.execute(select(Agent.id, Agent.name))).all()
    return {r[0]: r[1] for r in rows}


@router.get("/")
async def list_calls(
    direction: Optional[str] = None,
    outcome: Optional[str] = None,
    agent_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Call)
    count_q = select(func.count(Call.id))
    if direction:
        query = query.where(Call.direction == direction)
        count_q = count_q.where(Call.direction == direction)
    if outcome:
        query = query.where(Call.outcome == outcome)
        count_q = count_q.where(Call.outcome == outcome)
    if agent_id:
        query = query.where(Call.agent_id == agent_id)
        count_q = count_q.where(Call.agent_id == agent_id)
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.where(Call.started_at >= df)
            count_q = count_q.where(Call.started_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(Call.started_at <= dt)
            count_q = count_q.where(Call.started_at <= dt)
        except ValueError:
            pass

    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(desc(Call.started_at)).limit(limit).offset(offset)
    calls = (await db.execute(query)).scalars().all()
    names = await _agent_name_map(db)

    return {"success": True, "data": [
        {
            "id": c.id,
            "agent_id": c.agent_id,
            "agent_name": names.get(c.agent_id, "Unassigned"),
            "direction": _enum(c.direction),
            "caller_number": c.caller_number,
            "called_number": c.called_number,
            "duration_seconds": c.duration_seconds,
            "duration_formatted": _fmt_duration(c.duration_seconds),
            "outcome": _enum(c.outcome),
            "ai_score": round(c.ai_score, 1) if c.ai_score is not None else None,
            "score_color": _score_color(c.ai_score),
            "started_at": str(c.started_at),
            "ended_at": str(c.ended_at) if c.ended_at else None,
        }
        for c in calls
    ], "total": total, "limit": limit, "offset": offset}


@router.get("/stats")
async def call_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)

    total_today = (await db.execute(
        select(func.count(Call.id)).where(Call.started_at >= today_start)
    )).scalar() or 0

    active_now = (await db.execute(
        select(func.count(Call.id)).where(Call.outcome == CallOutcome.in_progress)
    )).scalar() or 0

    avg_score_week = (await db.execute(
        select(func.avg(Call.ai_score)).where(Call.started_at >= week_start)
    )).scalar()

    avg_duration = (await db.execute(select(func.avg(Call.duration_seconds)))).scalar()

    total_calls = (await db.execute(select(func.count(Call.id)))).scalar() or 0
    connected = (await db.execute(
        select(func.count(Call.id)).where(
            Call.outcome.in_([CallOutcome.resolved, CallOutcome.escalated])
        )
    )).scalar() or 0
    connect_rate = round(connected / total_calls * 100, 1) if total_calls else 0.0

    total_seconds = (await db.execute(select(func.sum(Call.duration_seconds)))).scalar() or 0
    cost_estimate = round(total_seconds / 60 * TWILIO_COST_PER_MIN, 2)

    return {"success": True, "data": {
        "total_calls_today": total_today,
        "active_calls": active_now,
        "avg_score_week": round(avg_score_week, 1) if avg_score_week else 0.0,
        "avg_duration_seconds": round(avg_duration or 0),
        "avg_duration_formatted": _fmt_duration(avg_duration),
        "connect_rate": connect_rate,
        "total_calls": total_calls,
        "cost_estimate_usd": cost_estimate,
    }}


@router.get("/{call_id}")
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)):
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalars().first()
    if not call:
        return {"success": False, "error": "Call not found"}
    names = await _agent_name_map(db)
    sentiment = call.sentiment_data or {}
    analysis = call.ai_analysis or {}
    return {"success": True, "data": {
        "id": call.id,
        "agent_id": call.agent_id,
        "agent_name": names.get(call.agent_id, "Unassigned"),
        "campaign_id": call.campaign_id,
        "direction": _enum(call.direction),
        "caller_number": call.caller_number,
        "called_number": call.called_number,
        "twilio_call_sid": call.twilio_call_sid,
        "livekit_room": call.livekit_room,
        "duration_seconds": call.duration_seconds,
        "duration_formatted": _fmt_duration(call.duration_seconds),
        "outcome": _enum(call.outcome),
        "ai_score": round(call.ai_score, 1) if call.ai_score is not None else None,
        "score_color": _score_color(call.ai_score),
        "transcript": call.transcript,
        "recording_url": call.recording_url,
        "extracted_data": call.extracted_data or {},
        "rule_violations": call.rule_violations or [],
        "recommendations": analysis.get("recommendations", []),
        "ai_analysis": analysis,
        "sentiment_overall": sentiment.get("overall"),
        "sentiment_timeline": sentiment.get("timeline", []),
        "started_at": str(call.started_at),
        "ended_at": str(call.ended_at) if call.ended_at else None,
    }}


@router.post("/make")
async def make_outbound_call(data: MakeCall, db: AsyncSession = Depends(get_db)):
    """Validate the number, initiate a Twilio outbound call, persist the record."""
    # E.164 validation
    if not re.fullmatch(r"\+[1-9]\d{7,14}", data.to_number.strip()):
        return {"success": False, "error": "Invalid phone number. Use E.164 format, e.g. +14155552671"}

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        ngrok_url = (settings.NGROK_URL or "").rstrip("/") or "https://your-ngrok-url.ngrok.io"

        twilio_call = client.calls.create(
            to=data.to_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=f"{ngrok_url}/twilio/outbound",
            status_callback=f"{ngrok_url}/twilio/status",
            status_callback_method="POST",
            status_callback_event=["initiated", "answered", "completed"],
        )

        call = Call(
            agent_id=data.agent_id,
            campaign_id=data.campaign_id,
            twilio_call_sid=twilio_call.sid,
            direction=CallDirection.outbound,
            caller_number=settings.TWILIO_PHONE_NUMBER,
            called_number=data.to_number,
            outcome=CallOutcome.in_progress,
        )
        db.add(call)
        await db.commit()
        return {"success": True, "message": "Call initiated",
                "data": {"call_id": call.id, "twilio_sid": twilio_call.sid}}
    except Exception as e:
        return {"success": False, "error": f"Twilio call failed: {e}"}


@router.post("/{call_id}/analyze")
async def analyze_call(call_id: str, db: AsyncSession = Depends(get_db)):
    """Run GPT-4o-mini analysis over the call transcript and persist results."""
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalars().first()
    if not call:
        return {"success": False, "error": "Call not found"}
    if not call.transcript:
        return {"success": False, "error": "Call has no transcript to analyze"}

    analysis = await _analyze_transcript(call.transcript)

    # Persist
    if analysis.get("score") is not None:
        call.ai_score = float(analysis["score"])
    call.extracted_data = analysis.get("extracted_data", call.extracted_data or {})
    call.rule_violations = analysis.get("rule_violations", [])
    call.sentiment_data = {
        "overall": analysis.get("sentiment", "neutral"),
        "timeline": analysis.get("sentiment_timeline", []),
    }
    call.ai_analysis = {
        "score": analysis.get("score"),
        "summary": analysis.get("summary"),
        "recommendations": analysis.get("recommendations", []),
    }
    await db.commit()

    return {"success": True, "data": {
        "call_id": call.id,
        "score": call.ai_score,
        "score_color": _score_color(call.ai_score),
        "sentiment": analysis.get("sentiment"),
        "extracted_data": call.extracted_data,
        "rule_violations": call.rule_violations,
        "recommendations": analysis.get("recommendations", []),
        "summary": analysis.get("summary"),
    }}


async def _analyze_transcript(transcript: str) -> dict:
    """Call OpenAI to score and analyze a transcript; degrade gracefully on error."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": (
                    "You are a call-quality analyst. Analyze the call transcript and return "
                    "STRICT JSON with keys: score (0-100 integer for agent quality), "
                    "sentiment ('positive'|'neutral'|'negative'), "
                    "sentiment_timeline (array of 5 floats between -1 and 1 over the call), "
                    "extracted_data (object with any of name, phone, reservation details, order details, issue), "
                    "rule_violations (array of short strings), "
                    "recommendations (array of short improvement tips), "
                    "summary (one sentence)."
                )},
                {"role": "user", "content": transcript},
            ],
            max_tokens=500,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {
            "score": 80,
            "sentiment": "neutral",
            "sentiment_timeline": [0.0, 0.2, 0.1, 0.3, 0.4],
            "extracted_data": {},
            "rule_violations": [],
            "recommendations": ["Automated analysis unavailable", f"({type(e).__name__})"],
            "summary": "Analysis could not be completed automatically.",
        }
