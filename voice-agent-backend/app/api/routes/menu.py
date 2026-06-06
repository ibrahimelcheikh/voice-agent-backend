"""Menu API — the real menu data a restaurant tenant's voice agent reads from.

Exposes the menu over REST (dashboard / verification) plus a forgiving /quick helper to
seed menu items for a restaurant tenant from plain values (no IDs), so reservations/orders
can be tested via /docs without a phone — mirrors /appointments/quick.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List

from app.db.database import get_db
from app.models.models import MenuItem
from app.services.tenant_service import resolve_tenant_id_for_niche

router = APIRouter()

_RESTAURANT_NICHES = {"restaurant"}


class QuickMenuItem(BaseModel):
    """Seed one menu item from plain values. `price` is in DOLLARS (stored as cents)."""
    name: str
    price: float
    category: Optional[str] = None
    description: Optional[str] = None
    available: bool = True
    tenant_id: Optional[str] = None     # defaults to the first restaurant tenant


def _serialize(m: MenuItem) -> dict:
    return {"id": m.id, "name": m.name, "category": m.category,
            "price_cents": m.price, "price": f"${m.price / 100:.2f}",
            "description": m.description, "available": m.available}


@router.get("/")
async def list_menu(tenant_id: Optional[str] = None, available_only: bool = False,
                    db: AsyncSession = Depends(get_db)):
    tid = await resolve_tenant_id_for_niche(db, tenant_id, _RESTAURANT_NICHES)
    q = select(MenuItem)
    if tid:
        q = q.where(MenuItem.tenant_id == tid)
    if available_only:
        q = q.where(MenuItem.available == True)  # noqa: E712
    rows = (await db.execute(q.order_by(MenuItem.category, MenuItem.name))).scalars().all()
    return {"items": [_serialize(m) for m in rows], "tenant_id": tid}


@router.post("/quick")
async def quick_create_menu_item(data: QuickMenuItem, db: AsyncSession = Depends(get_db)):
    """Create a menu item for a restaurant tenant (test helper). Defaults to the first
    restaurant tenant when tenant_id is omitted."""
    tid = await resolve_tenant_id_for_niche(db, data.tenant_id, _RESTAURANT_NICHES)
    if not tid:
        raise HTTPException(404, "No restaurant tenant found — create one via POST /tenants")
    item = MenuItem(tenant_id=tid, name=data.name, category=data.category,
                    price=int(round(data.price * 100)), description=data.description,
                    available=data.available)
    db.add(item)
    await db.commit()
    return {"success": True, "data": _serialize(item)}


@router.post("/quick/bulk")
async def quick_bulk_menu(items: List[QuickMenuItem], db: AsyncSession = Depends(get_db)):
    """Seed several menu items at once (test helper)."""
    created = []
    for data in items:
        tid = await resolve_tenant_id_for_niche(db, data.tenant_id, _RESTAURANT_NICHES)
        if not tid:
            raise HTTPException(404, "No restaurant tenant found")
        item = MenuItem(tenant_id=tid, name=data.name, category=data.category,
                        price=int(round(data.price * 100)), description=data.description,
                        available=data.available)
        db.add(item)
        created.append(item)
    await db.commit()
    return {"success": True, "count": len(created),
            "data": [_serialize(m) for m in created]}
