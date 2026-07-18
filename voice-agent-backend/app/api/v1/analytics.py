"""/api/v1/analytics — aggregates computed from the existing Call/Appointment rows.
Merchants get their own tenant's numbers; operators get fleet-wide numbers."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Call, Appointment, Tenant
from .deps import Principal, get_principal, require_operator, require_tenant

router = APIRouter()


async def _daily_volume(db: AsyncSession, tenant_id: str | None, days: int = 28) -> list[int]:
    q = select(func.date(Call.started_at), func.count()).group_by(func.date(Call.started_at))
    if tenant_id:
        q = q.where(Call.tenant_id == tenant_id)
    rows = (await db.execute(q)).all()
    by_date = {str(r[0]): r[1] for r in rows if r[0] is not None}
    # Return the most-recent `days` buckets in chronological order (0-filled).
    keys = sorted(by_date.keys())[-days:]
    return [by_date[k] for k in keys] or [0]


@router.get("/overview")
async def overview(tenant_id: str = Depends(require_tenant), db: AsyncSession = Depends(get_db)):
    calls = (await db.execute(
        select(func.count()).where(Call.tenant_id == tenant_id))).scalar() or 0
    bookings = (await db.execute(
        select(func.count()).where(Appointment.tenant_id == tenant_id))).scalar() or 0
    # booking channel split
    chan = dict((r[0] or "voice", r[1]) for r in (await db.execute(
        select(Appointment.created_via, func.count())
        .where(Appointment.tenant_id == tenant_id)
        .group_by(Appointment.created_via))).all())
    return {
        "calls": calls,
        "bookings": bookings,
        "conversion": round(100 * bookings / calls) if calls else 0,
        "call_volume": await _daily_volume(db, tenant_id),
        "booking_channel": chan,
    }


@router.get("/fleet")
async def fleet(principal: Principal = Depends(require_operator), db: AsyncSession = Depends(get_db)):
    total_calls = (await db.execute(select(func.count()).select_from(Call))).scalar() or 0
    total_bookings = (await db.execute(select(func.count()).select_from(Appointment))).scalar() or 0
    # calls by merchant (join tenant name)
    rows = (await db.execute(
        select(Tenant.business_name, func.count(Call.id))
        .outerjoin(Call, Call.tenant_id == Tenant.id)
        .group_by(Tenant.business_name)
        .order_by(desc(func.count(Call.id)))
    )).all()
    calls_by_merchant = [{"name": r[0], "calls": r[1]} for r in rows if r[1]]
    chan = dict((r[0] or "voice", r[1]) for r in (await db.execute(
        select(Appointment.created_via, func.count()).group_by(Appointment.created_via))).all())
    return {
        "total_calls": total_calls,
        "total_bookings": total_bookings,
        "conversion": round(100 * total_bookings / total_calls) if total_calls else 0,
        "calls_by_merchant": calls_by_merchant,
        "booking_channel": chan,
        "call_volume": await _daily_volume(db, None),
    }
