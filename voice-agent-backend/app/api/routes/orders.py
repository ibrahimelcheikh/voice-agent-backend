"""Orders API — back-office view of the pickup orders the agent takes, plus a /quick helper
to create one from plain values for testing (mirrors /appointments/quick).

The /quick helper runs the SAME take_order function the voice agent uses, so it enforces
the same guardrail: every item is validated against the tenant's real, available menu —
an unknown dish is rejected (422), never invented or priced.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional, List

from app.db.database import get_db
from app.models.models import Order, OrderItem
from app.services.tenant_service import resolve_tenant_id_for_niche
from app.agents.restaurant_functions import take_order

router = APIRouter()

_RESTAURANT_NICHES = {"restaurant"}


class QuickOrderItem(BaseModel):
    name: str               # menu item name (matched against the tenant's real menu)
    quantity: int = 1


class QuickOrder(BaseModel):
    customer_name: str
    phone: str
    items: List[QuickOrderItem]
    pickup_time: Optional[str] = None
    tenant_id: Optional[str] = None     # defaults to the first restaurant tenant


async def _serialize(db: AsyncSession, o: Order) -> dict:
    lines = (await db.execute(
        select(OrderItem).where(OrderItem.order_id == o.id)
    )).scalars().all()
    return {"id": o.id, "customer_name": o.customer_name, "phone": o.phone,
            "pickup_time": o.pickup_time, "status": o.status.value,
            "total_cents": o.total, "total": f"${o.total / 100:.2f}",
            "items": [{"name": li.name, "quantity": li.quantity,
                       "line_total": f"${li.line_total / 100:.2f}"} for li in lines]}


@router.get("/")
async def list_orders(page: int = 1, page_size: int = 20, status: Optional[str] = None,
                      tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id_for_niche(db, tenant_id, _RESTAURANT_NICHES)
    q = select(Order)
    if tid:
        q = q.where(Order.tenant_id == tid)
    if status:
        q = q.where(Order.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    rows = (await db.execute(
        q.order_by(desc(Order.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [await _serialize(db, o) for o in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size,
            "tenant_id": tid}


@router.post("/quick")
async def quick_create_order(data: QuickOrder, db: AsyncSession = Depends(get_db)):
    """Create a pickup order from plain values (test helper). Items are validated against
    the tenant's real menu — an item that doesn't exist / isn't available is rejected."""
    tid = await resolve_tenant_id_for_niche(db, data.tenant_id, _RESTAURANT_NICHES)
    if not tid:
        raise HTTPException(404, "No restaurant tenant found — create one via POST /tenants")
    result = await take_order(
        items=[{"name": i.name, "quantity": i.quantity} for i in data.items],
        customer_name=data.customer_name, phone=data.phone,
        pickup_time=data.pickup_time, tenant_id=tid)
    if not result.get("success"):
        # e.g. items_not_on_menu — surface the guardrail's reason + what matched.
        raise HTTPException(422, result)
    return {"success": True, "data": result, "tenant_id": tid}
