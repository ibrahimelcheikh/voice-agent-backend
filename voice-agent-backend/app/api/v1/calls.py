"""/api/v1/calls — conversations list + transcript detail, from the existing Call rows
the live agent already persists. Read-only."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Call
from .deps import Principal, get_principal, require_tenant, scope_tenant

router = APIRouter()


def _dur(seconds: Optional[int]) -> str:
    if not seconds:
        return "—"
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _time(dt) -> str:
    try:
        return dt.strftime("%-I:%M %p")
    except Exception:
        return ""


def _sentiment(c: Call) -> str:
    sd = c.sentiment_data or {}
    if isinstance(sd, dict) and sd.get("label"):
        return str(sd["label"]).capitalize()
    if c.outcome and c.outcome.value == "escalated":
        return "Concerned"
    return "Positive"


def serialize(c: Call, full: bool = False) -> dict:
    urgent = bool(c.outcome and c.outcome.value == "escalated")
    tag = "booked" if c.appointment_id else "call"
    out = {
        "id": c.id,
        "name": c.caller_number or "Unknown",
        "phone": c.caller_number or "",
        "time": _time(c.started_at),
        "tag": tag,
        "lang": c.language or "en",
        "sentiment": _sentiment(c),
        "dur": _dur(c.duration_seconds),
        "urgent": urgent,
        "summary": (c.transcript or "")[:400] if not full else (c.transcript or ""),
    }
    if full:
        out["transcript"] = c.transcript or ""
        out["ai_analysis"] = c.ai_analysis or {}
        out["extracted_data"] = c.extracted_data or {}
    return out


@router.get("")
async def list_calls(page: int = 1, page_size: int = 30,
                     tenant_id: str = Depends(require_tenant),
                     db: AsyncSession = Depends(get_db)):
    base = select(Call).where(Call.tenant_id == tenant_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (await db.execute(
        base.order_by(desc(Call.started_at)).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [serialize(c) for c in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@router.get("/{call_id}")
async def get_call(call_id: str, principal: Principal = Depends(get_principal),
                   db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(Call).where(Call.id == call_id))).scalars().first()
    if not c:
        raise HTTPException(404, "Call not found")
    scope_tenant(principal, c.tenant_id)
    return serialize(c, full=True)
