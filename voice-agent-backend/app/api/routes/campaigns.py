from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db, AsyncSessionLocal
from app.models.models import Campaign, Call, CampaignStatus, CallDirection, CallOutcome
from app.core.config import settings
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import asyncio

router = APIRouter()


class CreateCampaign(BaseModel):
    name: str
    agent_id: str
    contacts: List[dict] = []
    script: Optional[str] = None
    calls_per_hour: int = 10
    retry_attempts: int = 2
    scheduled_start: Optional[str] = None


def _campaign_dict(c: Campaign) -> dict:
    return {
        "id": c.id, "name": c.name, "agent_id": c.agent_id, "status": _enum(c.status),
        "total_contacts": c.total_contacts, "called_count": c.called_count,
        "connected_count": c.connected_count, "voicemail_count": c.voicemail_count,
        "failed_count": c.failed_count, "calls_per_hour": c.calls_per_hour,
        "connect_rate": round(c.connected_count / c.called_count * 100, 1) if c.called_count else 0.0,
        "created_at": str(c.created_at),
    }


def _enum(v):
    return v.value if hasattr(v, "value") else v


@router.get("/")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    campaigns = (await db.execute(select(Campaign))).scalars().all()
    return {"success": True, "data": [_campaign_dict(c) for c in campaigns]}


@router.post("/")
async def create_campaign(data: CreateCampaign, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(
        name=data.name, agent_id=data.agent_id,
        contacts=data.contacts, script=data.script,
        total_contacts=len(data.contacts),
        calls_per_hour=data.calls_per_hour, retry_attempts=data.retry_attempts,
        scheduled_start=datetime.fromisoformat(data.scheduled_start) if data.scheduled_start else None,
    )
    db.add(campaign)
    await db.commit()
    return {"success": True, "message": "Campaign created", "data": {"id": campaign.id}}


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalars().first()
    if not c:
        return {"success": False, "error": "Campaign not found"}
    return {"success": True, "data": {**_campaign_dict(c), "contacts": c.contacts or [], "script": c.script}}


@router.put("/{campaign_id}/status")
async def update_campaign_status(campaign_id: str, status: str, db: AsyncSession = Depends(get_db)):
    campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalars().first()
    if not campaign:
        return {"success": False, "error": "Campaign not found"}
    campaign.status = status
    await db.commit()
    return {"success": True, "message": f"Campaign {status}"}


@router.post("/{campaign_id}/launch")
async def launch_campaign(campaign_id: str, background_tasks: BackgroundTasks,
                          db: AsyncSession = Depends(get_db)):
    """Activate a campaign and dial its contacts in the background, rate-limited."""
    campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalars().first()
    if not campaign:
        return {"success": False, "error": "Campaign not found"}
    if campaign.status == CampaignStatus.active:
        return {"success": False, "error": "Campaign already active"}

    campaign.status = CampaignStatus.active
    await db.commit()

    background_tasks.add_task(_run_campaign, campaign.id)
    return {"success": True, "message": "Campaign launched",
            "data": {"id": campaign.id, "total_contacts": campaign.total_contacts}}


@router.get("/{campaign_id}/progress")
async def campaign_progress(campaign_id: str, db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalars().first()
    if not c:
        return {"success": False, "error": "Campaign not found"}

    completion = round(c.called_count / c.total_contacts * 100, 1) if c.total_contacts else 0.0
    remaining = max(c.total_contacts - c.called_count, 0)
    per_hour = max(c.calls_per_hour, 1)
    eta_minutes = round(remaining / per_hour * 60, 1)

    return {"success": True, "data": {
        "status": _enum(c.status),
        "total": c.total_contacts,
        "called": c.called_count,
        "connected": c.connected_count,
        "voicemail": c.voicemail_count,
        "failed": c.failed_count,
        "remaining": remaining,
        "completion_percent": completion,
        "estimated_minutes_remaining": eta_minutes,
    }}


async def _run_campaign(campaign_id: str):
    """Background dialer: loops contacts respecting calls_per_hour."""
    async with AsyncSessionLocal() as db:
        campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalars().first()
        if not campaign:
            return
        contacts = list(campaign.contacts or [])
        per_hour = max(campaign.calls_per_hour or 10, 1)
        delay = 3600.0 / per_hour  # seconds between calls

        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        except Exception:
            client = None

        ngrok_url = (settings.NGROK_URL or "").rstrip("/")

        for contact in contacts:
            # Stop if the campaign was paused/cancelled mid-run.
            campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalars().first()
            if not campaign or campaign.status != CampaignStatus.active:
                break

            phone = contact.get("phone")
            sid, outcome = None, CallOutcome.in_progress
            if client and phone and ngrok_url:
                try:
                    tw = client.calls.create(
                        to=phone, from_=settings.TWILIO_PHONE_NUMBER,
                        url=f"{ngrok_url}/twilio/outbound",
                        status_callback=f"{ngrok_url}/twilio/status",
                        status_callback_method="POST",
                    )
                    sid = tw.sid
                    campaign.connected_count += 1
                except Exception as e:
                    print(f"[campaign {campaign_id}] dial failed for {phone}: {e}")
                    campaign.failed_count += 1
                    outcome = CallOutcome.abandoned
            else:
                # No live Twilio/ngrok — record the attempt so progress advances in demo mode.
                campaign.failed_count += 1
                outcome = CallOutcome.no_answer

            db.add(Call(
                agent_id=campaign.agent_id, campaign_id=campaign.id,
                twilio_call_sid=sid, direction=CallDirection.outbound,
                caller_number=settings.TWILIO_PHONE_NUMBER, called_number=phone,
                outcome=outcome,
            ))
            campaign.called_count += 1
            await db.commit()

            await asyncio.sleep(delay)

        # Mark complete if we finished the list while still active.
        campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalars().first()
        if campaign and campaign.status == CampaignStatus.active:
            campaign.status = CampaignStatus.completed
            await db.commit()
        print(f"[campaign {campaign_id}] finished")
