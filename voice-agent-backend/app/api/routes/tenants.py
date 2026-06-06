"""
Tenant management API — create and configure the businesses the platform serves.

These power the (future) admin dashboard. The routing-critical field is
`twilio_phone_number`: the dialed number that maps an inbound call to this tenant.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

from app.db.database import get_db
from app.models.models import Tenant, Niche

router = APIRouter()


def _log(msg: str) -> None:
    """Print to stdout so the line is always visible in the Railway log stream (the
    codebase relies on print() for production diagnostics, not the logging module)."""
    print(f"[tenants] {msg}", flush=True)


class CreateTenant(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    business_name: str
    niche: Niche = Niche.clinic
    twilio_phone_number: Optional[str] = None
    default_language: str = "en"
    supported_languages: Optional[list[str]] = None
    timezone: str = "Asia/Beirut"
    greeting_message: Optional[str] = None
    knowledge_base: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None


class UpdateTenant(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    business_name: Optional[str] = None
    niche: Optional[Niche] = None
    twilio_phone_number: Optional[str] = None
    default_language: Optional[str] = None
    supported_languages: Optional[list[str]] = None
    timezone: Optional[str] = None
    greeting_message: Optional[str] = None
    knowledge_base: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class KnowledgeBase(BaseModel):
    knowledge_base: dict[str, Any]


def _serialize(t: Tenant) -> dict:
    return {
        "id": t.id,
        "business_name": t.business_name,
        "niche": t.niche.value if t.niche else None,
        "twilio_phone_number": t.twilio_phone_number,
        "default_language": t.default_language,
        "supported_languages": t.supported_languages or [],
        "timezone": t.timezone,
        "greeting_message": t.greeting_message,
        "knowledge_base": t.knowledge_base or {},
        "config": t.config or {},
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


async def _number_in_use(db: AsyncSession, number: str, exclude_id: str | None = None) -> bool:
    if not number:
        return False
    q = select(Tenant).where(Tenant.twilio_phone_number == number)
    if exclude_id:
        q = q.where(Tenant.id != exclude_id)
    return (await db.execute(q)).scalars().first() is not None


@router.post("/")
async def create_tenant(data: CreateTenant, db: AsyncSession = Depends(get_db)):
    if data.twilio_phone_number and await _number_in_use(db, data.twilio_phone_number):
        raise HTTPException(409, "A tenant with this Twilio number already exists")
    tenant = Tenant(
        business_name=data.business_name,
        niche=data.niche,
        twilio_phone_number=data.twilio_phone_number,
        default_language=data.default_language,
        supported_languages=data.supported_languages or [data.default_language],
        timezone=data.timezone,
        greeting_message=data.greeting_message,
        knowledge_base=data.knowledge_base or {},
        config=data.config or {},
    )
    db.add(tenant)
    await db.commit()
    return {"success": True, "data": _serialize(tenant)}


@router.get("/")
async def list_tenants(page: int = 1, page_size: int = 50,
                       db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Tenant))).scalar() or 0
    rows = (await db.execute(
        select(Tenant).order_by(Tenant.created_at)
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [_serialize(t) for t in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(404, "Tenant not found")
    return {"data": _serialize(t)}


# Every tenant column a PATCH may change. The request is validated into UpdateTenant, so
# only these names can ever reach the model; listing them here also guards against an
# unexpected key being setattr'd onto the ORM object.
_UPDATABLE_FIELDS = {
    "business_name", "niche", "twilio_phone_number", "default_language",
    "supported_languages", "timezone", "greeting_message", "knowledge_base",
    "config", "is_active",
}


@router.patch("/{tenant_id}")
async def update_tenant(tenant_id: str, data: UpdateTenant, request: Request,
                        db: AsyncSession = Depends(get_db)):
    """Partial update: apply ONLY the fields present in the request body, leave the rest
    unchanged, commit, then return the tenant re-read from the database.

    `exclude_unset=True` is what makes this a true PATCH — a field the caller omitted is
    absent from the dump and so is never touched, while a field they DID send (even to a
    new value like a different twilio_phone_number) is applied and committed.

    Heavily instrumented (see the [tenants] log lines) because a 200-with-no-change almost
    always means the body never arrived as parsed JSON (wrong Content-Type, an empty body,
    or a proxy stripping it) — which the logs make obvious."""
    # Raw body for diagnostics. Starlette caches the body, so reading it here is safe even
    # though FastAPI already parsed it into `data`.
    try:
        raw_bytes = await request.body()
        raw_text = raw_bytes.decode("utf-8") if raw_bytes else ""
    except Exception as e:  # pragma: no cover - diagnostics must never break the request
        raw_text = f"<unreadable: {type(e).__name__}>"
    content_type = request.headers.get("content-type")
    _log(f"PATCH /{tenant_id} content-type={content_type!r} raw_body={raw_text!r}")

    t = await db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(404, "Tenant not found")

    # The fields the caller actually sent (not omitted, not just schema defaults).
    parsed = data.model_dump(exclude_unset=True)
    _log(f"PATCH /{tenant_id} parsed model (exclude_unset)={parsed}")
    updates = {k: v for k, v in parsed.items() if k in _UPDATABLE_FIELDS}

    # DEFENSIVE FALLBACK: if the validated model carried no recognised fields but the client
    # DID send a JSON object, apply the recognised keys straight from the raw body. This
    # guarantees a PATCH with a real body can never be a silent no-op, whatever the body
    # parsing did. (Validation already ran, so any value present here is well-formed.)
    if not updates and raw_text:
        try:
            body_obj = json.loads(raw_text)
            if isinstance(body_obj, dict):
                updates = {k: v for k, v in body_obj.items() if k in _UPDATABLE_FIELDS}
                if updates:
                    _log(f"PATCH /{tenant_id} model had no fields; applied {sorted(updates)} "
                         "from RAW body instead")
        except (ValueError, TypeError) as e:
            _log(f"PATCH /{tenant_id} raw body is not a JSON object ({type(e).__name__})")

    _log(f"PATCH /{tenant_id} applying fields: {sorted(updates)}")

    # Reject a duplicate routing number up front (twilio_phone_number is UNIQUE).
    if updates.get("twilio_phone_number"):
        if await _number_in_use(db, updates["twilio_phone_number"], exclude_id=tenant_id):
            raise HTTPException(409, "A tenant with this Twilio number already exists")

    for field, value in updates.items():
        setattr(t, field, value)

    # Persist BEFORE returning. add() makes the intent explicit (t is already tracked);
    # commit flushes the UPDATE; refresh re-reads the row so the response reflects exactly
    # what is now in the database, not just the in-memory object.
    db.add(t)
    await db.commit()
    await db.refresh(t)
    _log(f"PATCH /{tenant_id} COMMITTED -> twilio_phone_number={t.twilio_phone_number!r} "
         f"business_name={t.business_name!r} niche={t.niche.value if t.niche else None} "
         f"is_active={t.is_active}")
    return {"success": True, "updated_fields": sorted(updates.keys()),
            "data": _serialize(t)}


@router.put("/{tenant_id}/knowledge-base")
async def set_knowledge_base(tenant_id: str, data: KnowledgeBase,
                             db: AsyncSession = Depends(get_db)):
    """Replace a tenant's knowledge base (FAQ source the agent may state from:
    hours, services, pricing, locations, policies)."""
    t = await db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(404, "Tenant not found")
    t.knowledge_base = data.knowledge_base
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"success": True, "data": _serialize(t)}
