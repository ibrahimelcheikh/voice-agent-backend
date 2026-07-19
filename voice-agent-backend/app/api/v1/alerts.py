"""/api/v1/alerts — operator-only system/health alerts for the PrimeOps console."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import OpsAlert
from .deps import Principal, require_operator
from ._util import rel_time

router = APIRouter()


def serialize(a: OpsAlert) -> dict:
    return {"id": a.id, "sev": a.severity, "title": a.title, "merchant": a.merchant_name or "",
            "time": rel_time(a.created_at), "body": a.body or "", "status": a.status}


@router.get("")
async def list_alerts(severity: Optional[str] = None,
                      principal: Principal = Depends(require_operator),
                      db: AsyncSession = Depends(get_db)):
    q = select(OpsAlert).where(OpsAlert.status == "active")
    if severity and severity != "all":
        q = q.where(OpsAlert.severity == severity)
    rows = (await db.execute(q.order_by(desc(OpsAlert.created_at)))).scalars().all()
    return {"items": [serialize(a) for a in rows]}


class AlertIn(BaseModel):
    severity: str = "info"
    title: str
    merchant_name: Optional[str] = None
    tenant_id: Optional[str] = None
    body: Optional[str] = None


@router.post("")
async def create_alert(data: AlertIn, principal: Principal = Depends(require_operator),
                       db: AsyncSession = Depends(get_db)):
    a = OpsAlert(severity=data.severity, title=data.title, merchant_name=data.merchant_name,
                 tenant_id=data.tenant_id, body=data.body)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return serialize(a)


@router.patch("/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str, principal: Principal = Depends(require_operator),
                        db: AsyncSession = Depends(get_db)):
    a = (await db.execute(select(OpsAlert).where(OpsAlert.id == alert_id))).scalars().first()
    if not a:
        raise HTTPException(404, "Alert not found")
    a.status = "dismissed"
    await db.commit()
    return serialize(a)
