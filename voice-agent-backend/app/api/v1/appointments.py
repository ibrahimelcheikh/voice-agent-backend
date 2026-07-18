"""/api/v1/appointments — upcoming/booked appointments for a tenant, from the existing
Appointment rows the agent books."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Appointment, Patient, Service
from .deps import require_tenant

router = APIRouter()

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _day(date_str: str) -> str:
    try:
        from datetime import date
        y, m, d = (int(x) for x in date_str.split("-"))
        return _DAYS[date(y, m, d).weekday()]
    except Exception:
        return ""


@router.get("")
async def list_appointments(tenant_id: str = Depends(require_tenant),
                            db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Appointment, Patient.name, Service.name)
        .outerjoin(Patient, Appointment.patient_id == Patient.id)
        .outerjoin(Service, Appointment.service_id == Service.id)
        .where(Appointment.tenant_id == tenant_id)
        .order_by(desc(Appointment.date))
    )).all()
    items = []
    for appt, patient_name, service_name in rows:
        via_map = {"voice": "AI · Voice", "whatsapp": "AI · WhatsApp", "manual": "Manual"}
        items.append({
            "id": appt.id,
            "name": patient_name or "Unknown",
            "svc": service_name or (appt.reason or ""),
            "day": _day(appt.date),
            "date": (appt.date or "").split("-")[-1],
            "time": appt.time,
            "status": appt.status.value if appt.status else "booked",
            "via": via_map.get(appt.created_via, "AI · Voice"),
        })
    return {"items": items}
