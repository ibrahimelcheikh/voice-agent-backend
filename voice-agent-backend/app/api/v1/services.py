"""/api/v1/services — treatments the merchant app shows and the agent quotes.
The voice agent reads name/price/duration; the rich merchant fields (about/prep/after/
pricing tiers, EN+AR) live in Service.details and never affect the agent."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Service
from .deps import Principal, get_principal, require_tenant, scope_tenant

router = APIRouter()


def serialize(s: Service) -> dict:
    d = s.details or {}
    return {
        "id": s.id,
        "name": s.name,
        "en": s.name,
        "ar": d.get("ar", s.name),
        "cat": s.category or d.get("cat", ""),
        "price": d.get("price", s.price),
        "dur": s.duration_minutes,
        "description": s.description,
        "about": d.get("about", {}),
        "tiers": d.get("tiers", []),
        "prep": d.get("prep", {}),
        "after": d.get("after", {}),
    }


@router.get("")
async def list_services(tenant_id: str = Depends(require_tenant),
                        db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Service).where(Service.tenant_id == tenant_id).order_by(Service.created_at)
    )).scalars().all()
    return {"items": [serialize(s) for s in rows]}


class ServiceIn(BaseModel):
    name: str
    price: Optional[int] = 0
    duration_minutes: Optional[int] = 30
    category: Optional[str] = None
    description: Optional[str] = None
    details: Optional[dict] = None


@router.post("")
async def create_service(data: ServiceIn, tenant_id: str = Depends(require_tenant),
                         db: AsyncSession = Depends(get_db)):
    s = Service(tenant_id=tenant_id, name=data.name, price=data.price or 0,
                duration_minutes=data.duration_minutes or 30, category=data.category,
                description=data.description, details=data.details or {})
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return serialize(s)


@router.patch("/{service_id}")
async def update_service(service_id: str, data: ServiceIn,
                         principal: Principal = Depends(get_principal),
                         db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(Service).where(Service.id == service_id))).scalars().first()
    if not s:
        raise HTTPException(404, "Service not found")
    scope_tenant(principal, s.tenant_id)  # 403 if merchant of another tenant
    s.name = data.name
    s.price = data.price or 0
    s.duration_minutes = data.duration_minutes or 30
    s.category = data.category
    s.description = data.description
    if data.details is not None:
        s.details = data.details
    await db.commit()
    await db.refresh(s)
    return serialize(s)


@router.delete("/{service_id}")
async def delete_service(service_id: str, principal: Principal = Depends(get_principal),
                         db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(Service).where(Service.id == service_id))).scalars().first()
    if not s:
        raise HTTPException(404, "Service not found")
    scope_tenant(principal, s.tenant_id)
    await db.delete(s)
    await db.commit()
    return {"deleted": True, "id": service_id}
