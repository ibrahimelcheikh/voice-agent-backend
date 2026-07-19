"""/api/v1/settings — the merchant Settings screen. Writes land in the exact tables the
live voice agent reads, so console edits change real agent behavior:
  * open greeting   -> Tenant.greeting_message
  * closed greeting -> Tenant.closed_greeting
  * hours           -> Clinic.hours (agent reads via get_clinic_hours)
  * holidays        -> Holiday rows (surfaced in load_tenant_config)
  * temp closure    -> Tenant.config['temporary_closure']
  * voice           -> inbound Agent.voice_id (+ speed/ambience in Tenant.config['voice'])
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Tenant, Clinic, Holiday, Agent, AgentType
from .deps import require_tenant

router = APIRouter()


async def _primary_clinic(db: AsyncSession, tenant_id: str) -> Optional[Clinic]:
    return (await db.execute(
        select(Clinic).where(Clinic.tenant_id == tenant_id).order_by(Clinic.created_at)
    )).scalars().first()


async def _tenant(db: AsyncSession, tenant_id: str) -> Tenant:
    t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not t:
        raise HTTPException(404, "Tenant not found")
    return t


def _holiday(h: Holiday) -> dict:
    return {"id": h.id, "name": h.name, "date": h.date, "closed": h.closed, "hours": h.hours}


@router.get("")
async def get_settings(tenant_id: str = Depends(require_tenant), db: AsyncSession = Depends(get_db)):
    t = await _tenant(db, tenant_id)
    clinic = await _primary_clinic(db, tenant_id)
    holidays = (await db.execute(select(Holiday).where(Holiday.tenant_id == tenant_id))).scalars().all()
    agent = (await db.execute(
        select(Agent).where(Agent.tenant_id == tenant_id, Agent.type == AgentType.inbound)
    )).scalars().first()
    cfg = t.config or {}
    return {
        "open_greeting": t.greeting_message,
        "closed_greeting": t.closed_greeting,
        "hours": (clinic.hours if clinic else {}) or {},
        "holidays": [_holiday(h) for h in holidays],
        "temporary_closure": cfg.get("temporary_closure"),
        "voice": {
            "voice_id": (agent.voice_id if agent else None),
            **(cfg.get("voice") or {}),
        },
    }


class Greetings(BaseModel):
    open_greeting: Optional[str] = None
    closed_greeting: Optional[str] = None


@router.put("/greetings")
async def put_greetings(data: Greetings, tenant_id: str = Depends(require_tenant),
                        db: AsyncSession = Depends(get_db)):
    t = await _tenant(db, tenant_id)
    if data.open_greeting is not None:
        t.greeting_message = data.open_greeting
    if data.closed_greeting is not None:
        t.closed_greeting = data.closed_greeting
    await db.commit()
    return {"open_greeting": t.greeting_message, "closed_greeting": t.closed_greeting}


class HoursIn(BaseModel):
    hours: dict


@router.put("/hours")
async def put_hours(data: HoursIn, tenant_id: str = Depends(require_tenant),
                    db: AsyncSession = Depends(get_db)):
    clinic = await _primary_clinic(db, tenant_id)
    if not clinic:
        clinic = Clinic(tenant_id=tenant_id, name="Main branch", hours=data.hours)
        db.add(clinic)
    else:
        clinic.hours = data.hours
        flag_modified(clinic, "hours")
    await db.commit()
    return {"hours": clinic.hours}


class HolidayIn(BaseModel):
    name: str
    date: Optional[str] = None
    closed: bool = True
    hours: Optional[str] = None


@router.get("/holidays")
async def list_holidays(tenant_id: str = Depends(require_tenant), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Holiday).where(Holiday.tenant_id == tenant_id))).scalars().all()
    return {"items": [_holiday(h) for h in rows]}


@router.post("/holidays")
async def add_holiday(data: HolidayIn, tenant_id: str = Depends(require_tenant),
                      db: AsyncSession = Depends(get_db)):
    h = Holiday(tenant_id=tenant_id, name=data.name, date=data.date, closed=data.closed,
                hours=None if data.closed else data.hours)
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return _holiday(h)


@router.delete("/holidays/{holiday_id}")
async def remove_holiday(holiday_id: str, tenant_id: str = Depends(require_tenant),
                         db: AsyncSession = Depends(get_db)):
    h = (await db.execute(select(Holiday).where(
        Holiday.id == holiday_id, Holiday.tenant_id == tenant_id))).scalars().first()
    if not h:
        raise HTTPException(404, "Holiday not found")
    await db.delete(h)
    await db.commit()
    return {"deleted": True, "id": holiday_id}


class TempClosure(BaseModel):
    active: bool = False
    until: Optional[str] = None
    note: Optional[str] = None


@router.put("/temporary-closure")
async def put_temp_closure(data: TempClosure, tenant_id: str = Depends(require_tenant),
                           db: AsyncSession = Depends(get_db)):
    t = await _tenant(db, tenant_id)
    cfg = dict(t.config or {})
    cfg["temporary_closure"] = data.model_dump()
    t.config = cfg
    flag_modified(t, "config")
    await db.commit()
    return {"temporary_closure": cfg["temporary_closure"]}


class VoiceIn(BaseModel):
    voice_id: Optional[str] = None
    speed: Optional[int] = None
    ambient: Optional[bool] = None
    ambient_level: Optional[int] = None


@router.put("/voice")
async def put_voice(data: VoiceIn, tenant_id: str = Depends(require_tenant),
                    db: AsyncSession = Depends(get_db)):
    t = await _tenant(db, tenant_id)
    if data.voice_id:
        agent = (await db.execute(
            select(Agent).where(Agent.tenant_id == tenant_id, Agent.type == AgentType.inbound)
        )).scalars().first()
        if agent:
            agent.voice_id = data.voice_id
    cfg = dict(t.config or {})
    voice_cfg = dict(cfg.get("voice") or {})
    for k in ("speed", "ambient", "ambient_level"):
        v = getattr(data, k)
        if v is not None:
            voice_cfg[k] = v
    cfg["voice"] = voice_cfg
    t.config = cfg
    flag_modified(t, "config")
    await db.commit()
    return {"voice": {"voice_id": data.voice_id, **voice_cfg}}
