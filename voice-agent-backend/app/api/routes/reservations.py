from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.models.models import Reservation, ReservationStatus
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, timedelta

router = APIRouter()


class CreateReservation(BaseModel):
    customer_name: str
    customer_phone: str
    party_size: int = 2
    date: str
    time: str
    location: str = "Downtown"
    notes: Optional[str] = None
    created_via: str = "manual"
    agent_id: Optional[str] = None


class UpdateReservation(BaseModel):
    party_size: Optional[int] = None
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def _enum(v):
    return v.value if hasattr(v, "value") else v


def _res_dict(r: Reservation) -> dict:
    return {"id": r.id, "agent_id": r.agent_id, "customer_name": r.customer_name,
            "customer_phone": r.customer_phone, "party_size": r.party_size,
            "date": r.date, "time": r.time, "location": r.location,
            "status": _enum(r.status), "notes": r.notes, "created_via": r.created_via,
            "created_at": str(r.created_at)}


@router.get("/")
async def list_reservations(
    date: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Reservation)
    if date:
        q = q.where(Reservation.date == date)
    if status:
        q = q.where(Reservation.status == status)
    if location:
        q = q.where(Reservation.location == location)
    q = q.order_by(desc(Reservation.date), Reservation.time)
    rows = (await db.execute(q)).scalars().all()
    return {"success": True, "data": [_res_dict(r) for r in rows]}


@router.get("/today")
async def reservations_today(db: AsyncSession = Depends(get_db)):
    today = date.today().isoformat()
    rows = (await db.execute(
        select(Reservation).where(Reservation.date == today).order_by(Reservation.time)
    )).scalars().all()
    grouped: dict = {}
    for r in rows:
        grouped.setdefault(r.time, []).append(_res_dict(r))
    return {"success": True, "data": {"date": today, "count": len(rows), "by_time": grouped}}


@router.get("/upcoming")
async def reservations_upcoming(db: AsyncSession = Depends(get_db)):
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=7)).isoformat()
    rows = (await db.execute(
        select(Reservation)
        .where(Reservation.date >= today, Reservation.date <= end,
               Reservation.status != ReservationStatus.cancelled)
        .order_by(Reservation.date, Reservation.time)
    )).scalars().all()
    return {"success": True, "data": [_res_dict(r) for r in rows]}


@router.post("/")
async def create_reservation(data: CreateReservation, db: AsyncSession = Depends(get_db)):
    res = Reservation(**data.model_dump(), status=ReservationStatus.confirmed)
    db.add(res)
    await db.commit()
    return {"success": True, "message": "Reservation created", "data": _res_dict(res)}


@router.get("/{res_id}")
async def get_reservation(res_id: str, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(Reservation).where(Reservation.id == res_id))).scalars().first()
    if not r:
        return {"success": False, "error": "Reservation not found"}
    return {"success": True, "data": _res_dict(r)}


@router.put("/{res_id}")
async def update_reservation(res_id: str, data: UpdateReservation, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(Reservation).where(Reservation.id == res_id))).scalars().first()
    if not r:
        return {"success": False, "error": "Reservation not found"}
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(r, key, value)
    await db.commit()
    return {"success": True, "message": "Reservation updated", "data": _res_dict(r)}
