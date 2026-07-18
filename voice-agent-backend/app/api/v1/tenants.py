"""/api/v1/tenants — merchants (operators see all, merchants see their own) and their
branches (reusing the Clinic model — one clinic = one branch)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Tenant, Clinic, Call, Appointment
from .deps import Principal, get_principal, require_operator, scope_tenant

router = APIRouter()


def serialize_merchant(t: Tenant, calls: int, bookings: int) -> dict:
    cfg = t.config or {}
    return {
        "id": t.id,
        "name": t.business_name,
        "city": cfg.get("city", ""),
        "type": cfg.get("type", ""),
        "plan": cfg.get("plan", "Starter"),
        "status": cfg.get("status", "live" if t.is_active else "paused"),
        "calls": calls,
        "bookings": bookings,
        "mrr": cfg.get("mrr", 0),
        "health": cfg.get("health", 0),
        "langs": t.supported_languages or ["en"],
        "default_language": t.default_language or "en",
    }


def serialize_branch(c: Clinic) -> dict:
    return {"id": c.id, "tenant_id": c.tenant_id, "name": c.name,
            "address": c.address, "phone": c.phone, "hours": c.hours or {}}


async def _counts(db: AsyncSession):
    calls = dict((r[0], r[1]) for r in (await db.execute(
        select(Call.tenant_id, func.count()).group_by(Call.tenant_id))).all())
    books = dict((r[0], r[1]) for r in (await db.execute(
        select(Appointment.tenant_id, func.count()).group_by(Appointment.tenant_id))).all())
    return calls, books


@router.get("")
async def list_tenants(principal: Principal = Depends(get_principal),
                       db: AsyncSession = Depends(get_db)):
    calls, books = await _counts(db)
    if principal.is_operator:
        rows = (await db.execute(select(Tenant).order_by(Tenant.created_at))).scalars().all()
    else:
        rows = (await db.execute(select(Tenant).where(Tenant.id == principal.tenant_id))).scalars().all()
    return {"items": [serialize_merchant(t, calls.get(t.id, 0), books.get(t.id, 0)) for t in rows]}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str, principal: Principal = Depends(get_principal),
                     db: AsyncSession = Depends(get_db)):
    tid = scope_tenant(principal, tenant_id)
    t = (await db.execute(select(Tenant).where(Tenant.id == tid))).scalars().first()
    if not t:
        raise HTTPException(404, "Tenant not found")
    calls, books = await _counts(db)
    return serialize_merchant(t, calls.get(t.id, 0), books.get(t.id, 0))


class TenantIn(BaseModel):
    business_name: str
    city: Optional[str] = None
    type: Optional[str] = None
    plan: Optional[str] = "Starter"
    twilio_phone_number: Optional[str] = None
    default_language: Optional[str] = "en"
    supported_languages: Optional[list] = None


@router.post("")
async def create_tenant(data: TenantIn, principal: Principal = Depends(require_operator),
                        db: AsyncSession = Depends(get_db)):
    t = Tenant(
        business_name=data.business_name,
        twilio_phone_number=data.twilio_phone_number,
        default_language=data.default_language or "en",
        supported_languages=data.supported_languages or [data.default_language or "en"],
        config={"city": data.city or "", "type": data.type or "", "plan": data.plan or "Starter",
                "status": "onboarding", "mrr": 0, "health": 0},
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return serialize_merchant(t, 0, 0)


# ── Branches (Clinic) ─────────────────────────────────────────────────────────

@router.get("/{tenant_id}/branches")
async def list_branches(tenant_id: str, principal: Principal = Depends(get_principal),
                        db: AsyncSession = Depends(get_db)):
    tid = scope_tenant(principal, tenant_id)
    rows = (await db.execute(
        select(Clinic).where(Clinic.tenant_id == tid).order_by(Clinic.created_at))).scalars().all()
    return {"items": [serialize_branch(c) for c in rows]}


class BranchIn(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    hours: Optional[dict] = None


@router.post("/{tenant_id}/branches")
async def create_branch(tenant_id: str, data: BranchIn,
                        principal: Principal = Depends(get_principal),
                        db: AsyncSession = Depends(get_db)):
    tid = scope_tenant(principal, tenant_id)
    if not tid:
        raise HTTPException(400, "tenant_id required")
    c = Clinic(tenant_id=tid, name=data.name, address=data.address, phone=data.phone,
               hours=data.hours or {})
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return serialize_branch(c)
