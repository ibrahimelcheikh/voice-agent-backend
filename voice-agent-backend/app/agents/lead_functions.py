"""
Lead-capture data functions — the source of truth for real_estate / automotive /
services tenants.

These tenants don't book appointments or take orders; their agent's job is to capture a
qualified lead and save it immediately. One flexible Lead row covers all three verticals:

  * real_estate → lead_type = property type, budget, requirements
  * automotive  → lead_type = vehicle interest, budget, requirements
  * services    → lead_type = service needed, requirements

Every function is tenant-scoped, so one business never sees another's leads. Nothing is
invented — the agent saves exactly what the caller said.
"""
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.core.tenant_scope import scope_query as _scope, require_tenant_id
from app.models.models import Lead, LeadStatus


async def capture_lead(customer_name=None, phone=None, lead_type=None, budget=None,
                       requirements=None, tenant_id=None) -> dict:
    """Save a lead. Requires at least a name + phone and one of lead_type/requirements so
    we never store an empty contact. The agent collects these conversationally; this fires
    once the essentials are present (the caller's confirmation completes it).

    If the same phone already has an open lead this call's details are merged into it
    rather than creating a duplicate, so a multi-turn collection stays one lead."""
    require_tenant_id(tenant_id, "capture_lead")
    async with AsyncSessionLocal() as db:
        missing = [k for k, v in {"customer_name": customer_name, "phone": phone}.items()
                   if not v]
        if missing:
            return {"success": False, "missing": missing}
        if not (lead_type or requirements):
            return {"success": False, "missing": ["lead_type"]}

        existing = (await db.execute(
            _scope(select(Lead).where(Lead.phone == phone,
                                      Lead.status == LeadStatus.new),
                   Lead, tenant_id).order_by(Lead.created_at.desc())
        )).scalars().first()

        if existing:
            existing.name = customer_name or existing.name
            if lead_type:
                existing.lead_type = lead_type
            if budget:
                existing.budget = budget
            if requirements:
                existing.requirements = requirements
            lead = existing
        else:
            lead = Lead(tenant_id=tenant_id, name=customer_name, phone=phone,
                        lead_type=lead_type, budget=budget, requirements=requirements,
                        status=LeadStatus.new, created_via="voice")
            db.add(lead)
        await db.commit()
        return {"success": True, "lead_id": lead.id, "customer_name": lead.name,
                "lead_type": lead.lead_type, "budget": lead.budget,
                "requirements": lead.requirements, "status": lead.status.value}


async def check_lead(phone=None, tenant_id=None) -> dict:
    """Look up whether this caller already has a lead on file (so a returning caller isn't
    re-interviewed from scratch)."""
    require_tenant_id(tenant_id, "check_lead")
    async with AsyncSessionLocal() as db:
        if not phone:
            return {"success": False, "reason": "need_phone"}
        lead = (await db.execute(
            _scope(select(Lead).where(Lead.phone == phone), Lead, tenant_id)
            .order_by(Lead.created_at.desc())
        )).scalars().first()
        if not lead:
            return {"success": True, "found": False}
        return {"success": True, "found": True, "lead_id": lead.id, "customer_name": lead.name,
                "lead_type": lead.lead_type, "budget": lead.budget,
                "requirements": lead.requirements, "status": lead.status.value}


# Registry used by the guardrail (intent -> coroutine) for lead-capture tenants.
LEAD_FUNCTIONS = {
    "capture_lead": capture_lead,
    "check_lead": check_lead,
}
