from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.models.models import Order, OrderType, OrderStatus
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class CreateOrder(BaseModel):
    customer_name: str
    customer_phone: str
    order_type: str = "pickup"
    items: List[dict] = []          # [{name, qty, price (cents)}]
    address: Optional[str] = None
    notes: Optional[str] = None
    created_via: str = "manual"
    agent_id: Optional[str] = None


class UpdateOrderStatus(BaseModel):
    status: str


def _enum(v):
    return v.value if hasattr(v, "value") else v


def _order_dict(o: Order) -> dict:
    return {"id": o.id, "agent_id": o.agent_id, "customer_name": o.customer_name,
            "customer_phone": o.customer_phone, "order_type": _enum(o.order_type),
            "items": o.items or [], "total_cents": o.total,
            "total_formatted": f"${(o.total or 0) / 100:.2f}",
            "status": _enum(o.status), "address": o.address, "notes": o.notes,
            "created_via": o.created_via, "created_at": str(o.created_at)}


@router.get("/")
async def list_orders(
    status: Optional[str] = None,
    order_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Order)
    if status:
        q = q.where(Order.status == status)
    if order_type:
        q = q.where(Order.order_type == order_type)
    q = q.order_by(desc(Order.created_at))
    rows = (await db.execute(q)).scalars().all()
    return {"success": True, "data": [_order_dict(o) for o in rows]}


@router.get("/active")
async def active_orders(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Order)
        .where(Order.status.in_([OrderStatus.received, OrderStatus.preparing, OrderStatus.ready]))
        .order_by(desc(Order.created_at))
    )).scalars().all()
    return {"success": True, "data": [_order_dict(o) for o in rows]}


@router.post("/")
async def create_order(data: CreateOrder, db: AsyncSession = Depends(get_db)):
    total = sum(int(i.get("price", 0)) * int(i.get("qty", 1)) for i in data.items)
    payload = data.model_dump()
    payload["order_type"] = OrderType(data.order_type) if data.order_type in OrderType._value2member_map_ else OrderType.pickup
    order = Order(**payload, total=total, status=OrderStatus.received)
    db.add(order)
    await db.commit()
    return {"success": True, "message": "Order created", "data": _order_dict(order)}


@router.get("/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalars().first()
    if not o:
        return {"success": False, "error": "Order not found"}
    return {"success": True, "data": _order_dict(o)}


@router.put("/{order_id}/status")
async def update_order_status(order_id: str, data: UpdateOrderStatus, db: AsyncSession = Depends(get_db)):
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalars().first()
    if not o:
        return {"success": False, "error": "Order not found"}
    if data.status not in OrderStatus._value2member_map_:
        return {"success": False, "error": f"Invalid status. Use one of {list(OrderStatus._value2member_map_)}"}
    o.status = OrderStatus(data.status)
    await db.commit()
    return {"success": True, "message": f"Order status updated to {data.status}", "data": _order_dict(o)}
