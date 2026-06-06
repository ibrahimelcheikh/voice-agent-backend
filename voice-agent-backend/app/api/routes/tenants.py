"""
Tenant management API — create and configure the businesses the platform serves.

These power the (future) admin dashboard. The routing-critical field is
`twilio_phone_number`: the dialed number that maps an inbound call to this tenant.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

from app.db.database import get_db
from app.models.models import Tenant, Niche

router = APIRouter()


class CreateTenant(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    business_name: str
    niche: Niche = Niche.clinic
    twilio_phone_number: Optional[str] = None
    default_language: str = "en"
    supported_languages: Optional[list[str]] = None
    timezone: str = "Asia/Beirut"
    greeting_message: Optional[str] = None
    knowledge_base: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None


class UpdateTenant(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    business_name: Optional[str] = None
    niche: Optional[Niche] = None
    twilio_phone_number: Optional[str] = None
    default_language: Optional[str] = None
    supported_languages: Optional[list[str]] = None
    timezone: Optional[str] = None
    greeting_message: Optional[str] = None
    knowledge_base: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class KnowledgeBase(BaseModel):
    knowledge_base: dict[str, Any]


def _serialize(t: Tenant) -> dict:
    return {
        "id": t.id,
        "business_name": t.business_name,
        "niche": t.niche.value if t.niche else None,
        "twilio_phone_number": t.twilio_phone_number,
        "default_language": t.default_language,
        "supported_languages": t.supported_languages or [],
        "timezone": t.timezone,
        "greeting_message": t.greeting_message,
        "knowledge_base": t.knowledge_base or {},
        "config": t.config or {},
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


async def _number_in_use(db: AsyncSession, number: str, exclude_id: str | None = None) -> bool:
    if not number:
        return False
    q = select(Tenant).where(Tenant.twilio_phone_number == number)
    if exclude_id:
        q = q.where(Tenant.id != exclude_id)
    return (await db.execute(q)).scalars().first() is not None


@router.post("/")
async def create_tenant(data: CreateTenant, db: AsyncSession = Depends(get_db)):
    if data.twilio_phone_number and await _number_in_use(db, data.twilio_phone_number):
        raise HTTPException(409, "A tenant with this Twilio number already exists")
    tenant = Tenant(
        business_name=data.business_name,
        niche=data.niche,
        twilio_phone_number=data.twilio_phone_number,
        default_language=data.default_language,
        supported_languages=data.supported_languages or [data.default_language],
        timezone=data.timezone,
        greeting_message=data.greeting_message,
        knowledge_base=data.knowledge_base or {},
        config=data.config or {},
    )
    db.add(tenant)
    await db.commit()
    return {"success": True, "data": _serialize(tenant)}


@router.get("/")
async def list_tenants(page: int = 1, page_size: int = 50,
                       db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Tenant))).scalar() or 0
    rows = (await db.execute(
        select(Tenant).order_by(Tenant.created_at)
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [_serialize(t) for t in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(404, "Tenant not found")
    return {"data": _serialize(t)}


@router.patch("/{tenant_id}")
async def update_tenant(tenant_id: str, data: UpdateTenant,
                        db: AsyncSession = Depends(get_db)):
    t = await db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(404, "Tenant not found")
    updates = data.model_dump(exclude_unset=True)
    if "twilio_phone_number" in updates and updates["twilio_phone_number"]:
        if await _number_in_use(db, updates["twilio_phone_number"], exclude_id=tenant_id):
            raise HTTPException(409, "A tenant with this Twilio number already exists")
    for field, value in updates.items():
        setattr(t, field, value)
    await db.commit()
    return {"success": True, "data": _serialize(t)}


@router.put("/{tenant_id}/knowledge-base")
async def set_knowledge_base(tenant_id: str, data: KnowledgeBase,
                             db: AsyncSession = Depends(get_db)):
    """Replace a tenant's knowledge base (FAQ source the agent may state from:
    hours, services, pricing, locations, policies)."""
    t = await db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(404, "Tenant not found")
    t.knowledge_base = data.knowledge_base
    await db.commit()
    return {"success": True, "data": _serialize(t)}
