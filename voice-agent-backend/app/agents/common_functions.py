"""
Cross-niche data functions every tenant's agent shares: FAQ from the tenant's knowledge
base, and caller recognition by phone.

Both are strictly tenant-scoped and strictly grounded:

  * faq_lookup answers ONLY from the tenant's knowledge_base (set in tenant config). If the
    answer isn't there it says so / offers a human handoff — it never invents a fact.
  * recognize_caller looks the caller's phone up within THIS tenant's customer records only
    (patients for clinics, reservations/orders for restaurants, leads for the rest), so the
    agent can greet a returning caller by name without ever crossing tenant boundaries.
"""
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.core.tenant_scope import scope_query as _scope, require_tenant_id
from app.models.models import (
    Tenant, Patient, Appointment, AppointmentStatus,
    Reservation, ReservationStatus, Order, Lead,
)


# Niche groups (kept in sync with app/agents/niches.py).
_CLINIC_NICHES = {"clinic", "dental", "spa"}
_RESTAURANT_NICHES = {"restaurant"}
_LEAD_NICHES = {"real_estate", "automotive", "services"}


def _kb_match(knowledge_base: dict, query: str) -> dict:
    """Pick the knowledge-base entries most relevant to the query. The KB is free-form
    JSON (hours, location, services, policies, products, …). We keyword-match the query
    against keys + stringified values and return the hits; with no clear hit we return the
    whole KB so the LLM can still answer if the fact is present. Either way the LLM may
    ONLY state what we return here."""
    if not isinstance(knowledge_base, dict) or not knowledge_base:
        return {}
    if not query:
        return knowledge_base
    needle = query.lower()
    words = {w for w in needle.replace("?", " ").split() if len(w) > 2}
    hits = {}
    for key, value in knowledge_base.items():
        hay = f"{key} {value}".lower()
        if key.lower() in needle or needle in key.lower() or (words & set(hay.split())):
            hits[key] = value
    return hits or knowledge_base


async def faq_lookup(query=None, tenant_id=None) -> dict:
    """Answer a general question from the tenant's knowledge base only. Returns the matched
    KB sections; the guardrail's strict wrapper makes the LLM phrase ONLY these, and offer a
    human handoff when the KB has nothing relevant."""
    require_tenant_id(tenant_id, "faq_lookup")
    async with AsyncSessionLocal() as db:
        tenant = await db.get(Tenant, tenant_id) if tenant_id else None
        kb = (tenant.knowledge_base if tenant else None) or {}
        if not kb:
            return {"success": True, "found": False, "knowledge": {},
                    "note": "No knowledge base configured — offer to connect to staff."}
        matched = _kb_match(kb, query or "")
        return {"success": True, "found": bool(matched), "query": query,
                "business_name": tenant.business_name if tenant else None,
                "knowledge": matched}


async def recognize_caller(phone=None, niche=None, tenant_id=None) -> dict:
    """Look the caller's phone up within THIS tenant's records and return their name + a
    short summary of prior activity, so the agent can greet a returning caller personally.

    Scoped strictly to the tenant and to the niche's relevant store:
      clinic/dental/spa → patients (+ upcoming appointments)
      restaurant        → reservations / orders by phone
      real_estate/...   → existing leads
    Returns {found: False} for an unknown caller — the agent just greets normally."""
    require_tenant_id(tenant_id, "recognize_caller")
    if not phone:
        return {"found": False}
    niche = (niche or "clinic").lower()
    async with AsyncSessionLocal() as db:
        if niche in _RESTAURANT_NICHES:
            return await _recognize_restaurant(db, phone, tenant_id)
        if niche in _LEAD_NICHES:
            return await _recognize_lead(db, phone, tenant_id)
        return await _recognize_clinic(db, phone, tenant_id)


async def _recognize_clinic(db, phone, tenant_id):
    patient = (await db.execute(
        _scope(select(Patient).where(Patient.phone == phone), Patient, tenant_id)
    )).scalars().first()
    if not patient:
        return {"found": False}
    from datetime import date
    upcoming = (await db.execute(
        _scope(select(Appointment), Appointment, tenant_id)
        .where(Appointment.patient_id == patient.id,
               Appointment.date >= date.today().isoformat(),
               Appointment.status.notin_([AppointmentStatus.cancelled]))
        .order_by(Appointment.date, Appointment.time)
    )).scalars().first()
    return {"found": True, "name": patient.name, "phone": phone,
            "has_upcoming": bool(upcoming),
            "upcoming": ({"date": upcoming.date, "time": upcoming.time} if upcoming else None)}


async def _recognize_restaurant(db, phone, tenant_id):
    resv = (await db.execute(
        _scope(select(Reservation).where(
            Reservation.phone == phone,
            Reservation.status.notin_([ReservationStatus.cancelled])),
            Reservation, tenant_id).order_by(Reservation.date.desc())
    )).scalars().first()
    order = (await db.execute(
        _scope(select(Order).where(Order.phone == phone), Order, tenant_id)
        .order_by(Order.created_at.desc())
    )).scalars().first()
    name = (resv.customer_name if resv else None) or (order.customer_name if order else None)
    if not name:
        return {"found": False}
    return {"found": True, "name": name, "phone": phone,
            "has_reservation": bool(resv),
            "last_reservation": ({"date": resv.date, "time": resv.time} if resv else None),
            "has_order": bool(order)}


async def _recognize_lead(db, phone, tenant_id):
    lead = (await db.execute(
        _scope(select(Lead).where(Lead.phone == phone), Lead, tenant_id)
        .order_by(Lead.created_at.desc())
    )).scalars().first()
    if not lead:
        return {"found": False}
    return {"found": True, "name": lead.name, "phone": phone,
            "lead_type": lead.lead_type, "status": lead.status.value}
