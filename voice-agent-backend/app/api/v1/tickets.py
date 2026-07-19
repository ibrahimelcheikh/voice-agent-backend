"""/api/v1/tickets — operator-only support tickets for the PrimeOps console."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import OpsTicket
from .deps import Principal, require_operator
from ._util import rel_time

router = APIRouter()


def serialize(t: OpsTicket) -> dict:
    return {"id": t.code or t.id, "subject": t.subject, "merchant": t.merchant_name or "",
            "status": t.status, "pri": t.priority, "agent": t.assignee or "—",
            "time": rel_time(t.created_at)}


@router.get("")
async def list_tickets(status: Optional[str] = None,
                       principal: Principal = Depends(require_operator),
                       db: AsyncSession = Depends(get_db)):
    q = select(OpsTicket)
    if status and status != "all":
        q = q.where(OpsTicket.status == status)
    rows = (await db.execute(q.order_by(desc(OpsTicket.created_at)))).scalars().all()
    return {"items": [serialize(t) for t in rows]}


class TicketIn(BaseModel):
    subject: str
    merchant_name: Optional[str] = None
    tenant_id: Optional[str] = None
    status: str = "open"
    priority: str = "medium"
    assignee: Optional[str] = None


@router.post("")
async def create_ticket(data: TicketIn, principal: Principal = Depends(require_operator),
                        db: AsyncSession = Depends(get_db)):
    t = OpsTicket(subject=data.subject, merchant_name=data.merchant_name, tenant_id=data.tenant_id,
                  status=data.status, priority=data.priority, assignee=data.assignee)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return serialize(t)


@router.patch("/{ticket_id}")
async def update_ticket(ticket_id: str, data: TicketIn,
                        principal: Principal = Depends(require_operator),
                        db: AsyncSession = Depends(get_db)):
    t = (await db.execute(
        select(OpsTicket).where((OpsTicket.id == ticket_id) | (OpsTicket.code == ticket_id))
    )).scalars().first()
    if not t:
        raise HTTPException(404, "Ticket not found")
    t.subject = data.subject
    t.status = data.status
    t.priority = data.priority
    t.assignee = data.assignee
    await db.commit()
    return serialize(t)
