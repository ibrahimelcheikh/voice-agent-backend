"""
Tenant resolution + config loading — the heart of the multi-tenant platform.

One codebase serves many businesses. The routing key is the DIALED phone number:
an inbound call's destination number (the tenant's Twilio number) is matched to
exactly one Tenant, whose config + data scope the entire call. Every agent path
(inbound Twilio webhook, the LiveKit agent worker, outbound reminders) resolves the
tenant through this module so behavior and data never cross tenant boundaries.

Pieces:
  * normalize_number(num)                 — loose phone key (last 10 digits)
  * resolve_tenant_by_number(db, number)  — Tenant for a dialed number, or None
  * get_default_tenant(db)                 — single-tenant fallback (the original clinic)
  * resolve_tenant_id(db, tenant_id)       — validate a supplied id, else default tenant
  * load_tenant_config(db, tenant)         — the dict the agent session runs from
  * sip_called_number(room)                — read the dialed number off a LiveKit SIP join
  * tenant_context_for_room(db, room)      — full (tenant_id, config) for a joined room
"""
import re

from sqlalchemy import select

from app.models.models import Tenant, Agent, AgentType, BehaviorConfig

# Default greeting/system prompt when a tenant hasn't set its own. Kept generic; the
# seeded clinic supplies its own greeting so existing behavior is unchanged.
_DEFAULT_GREETING = "Thank you for calling. This is the AI assistant, how may I help you?"
_DEFAULT_SYSTEM_PROMPT = (
    "You are a receptionist AI on a PHONE call. You may ONLY state information provided "
    "to you in the function results. NEVER invent appointment times, prices, names, or "
    "policies. When the caller says a relative date like 'next Monday' or 'tomorrow', the "
    "actual calendar date is computed for you — confirm it back and NEVER ask them for a "
    "specific calendar date. Keep every response to ONE short sentence, maximum 15 words. "
    "Never list more than 2 items; if listing services, say only the top 2-3 then ask if "
    "they want more. Be brief and natural, like a real receptionist. If you don't have the "
    "data, offer to connect to staff."
)


def normalize_number(number: str | None) -> str:
    """Loose comparison key for a phone number: digits only, last 10 (drops country-code /
    formatting differences so '+1 657-534-7796' and '6575347796' match)."""
    digits = re.sub(r"\D", "", number or "")
    return digits[-10:] if len(digits) >= 10 else digits


async def resolve_tenant_by_number(db, number: str | None) -> Tenant | None:
    """Find the tenant whose Twilio number matches the DIALED number. Tries an exact
    match first, then a normalized (last-10-digits) match so formatting never breaks
    routing. Returns None when no tenant owns the number (caller hears the generic
    'not configured' message)."""
    if not number:
        return None
    exact = (await db.execute(
        select(Tenant).where(Tenant.twilio_phone_number == number,
                             Tenant.is_active == True)  # noqa: E712
    )).scalars().first()
    if exact:
        return exact
    key = normalize_number(number)
    if not key:
        return None
    tenants = (await db.execute(
        select(Tenant).where(Tenant.is_active == True)  # noqa: E712
    )).scalars().all()
    for t in tenants:
        if t.twilio_phone_number and normalize_number(t.twilio_phone_number) == key:
            return t
    return None


async def get_default_tenant(db) -> Tenant | None:
    """The fallback tenant for single-tenant continuity (the original Prime Health clinic).
    Prefers the well-known seed id, else the oldest tenant. Used when a number can't be
    read off a call (best-effort SIP attributes) so the existing clinic keeps working."""
    t = (await db.execute(select(Tenant).where(Tenant.id == "tenant-001"))).scalars().first()
    if t:
        return t
    return (await db.execute(
        select(Tenant).where(Tenant.is_active == True).order_by(Tenant.created_at)  # noqa: E712
    )).scalars().first()


async def resolve_tenant_id(db, tenant_id: str | None) -> str | None:
    """Validate a caller-supplied tenant_id, else fall back to the default tenant. Returns
    the resolved id (or None if there are no tenants at all). Used by REST endpoints that
    accept an optional tenant_id so they can be scoped without breaking the existing
    single-tenant dashboard."""
    if tenant_id:
        t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
        if t:
            return t.id
    default = await get_default_tenant(db)
    return default.id if default else None


async def resolve_tenant_id_for_niche(db, tenant_id: str | None, niches) -> str | None:
    """Resolve a tenant_id for a niche-specific endpoint (menu/reservations/orders/leads).

    If a tenant_id is supplied it is validated and used. Otherwise we pick the first active
    tenant whose niche is in `niches` (so POST /menu/quick with no body still lands on the
    restaurant tenant during /docs testing). Falls back to the default tenant when there is
    no niche match. `niches` is a string or an iterable of niche values."""
    if tenant_id:
        t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
        if t:
            return t.id
    wanted = {niches} if isinstance(niches, str) else set(niches)
    t = (await db.execute(
        select(Tenant).where(Tenant.is_active == True)  # noqa: E712
        .order_by(Tenant.created_at)
    )).scalars().all()
    for tenant in t:
        if tenant.niche and tenant.niche.value in wanted:
            return tenant.id
    return await resolve_tenant_id(db, None)


async def load_tenant_config(db, tenant: Tenant) -> dict:
    """Build the config dict the agent session runs from for a given tenant: greeting,
    system prompt, voice, call-duration cap, language, and knowledge base. The system
    prompt + voice + duration come from the tenant's inbound BehaviorConfig when present
    (preserving the locked clinic prompt), else sensible defaults."""
    system_prompt = None
    voice_id = "shimmer"
    max_call_duration = 300

    agent = (await db.execute(
        select(Agent).where(Agent.tenant_id == tenant.id,
                            Agent.type == AgentType.inbound,
                            Agent.is_active == True)  # noqa: E712
    )).scalars().first()
    if agent:
        voice_id = agent.voice_id or voice_id
        if agent.behavior_config_id:
            cfg = (await db.execute(
                select(BehaviorConfig).where(BehaviorConfig.id == agent.behavior_config_id)
            )).scalars().first()
            if cfg:
                system_prompt = cfg.system_prompt or system_prompt
                max_call_duration = cfg.max_call_duration or max_call_duration

    return {
        "tenant_id": tenant.id,
        "agent_id": agent.id if agent else None,
        "business_name": tenant.business_name,
        "niche": tenant.niche.value if tenant.niche else "clinic",
        "greeting_message": tenant.greeting_message or _DEFAULT_GREETING,
        "system_prompt": system_prompt or _DEFAULT_SYSTEM_PROMPT,
        "voice_id": voice_id,
        "max_call_duration": max_call_duration,
        "language": tenant.default_language or "en",
        "supported_languages": tenant.supported_languages or ["en"],
        "timezone": tenant.timezone or "Asia/Beirut",
        "knowledge_base": tenant.knowledge_base or {},
        "config": tenant.config or {},
        "twilio_phone_number": tenant.twilio_phone_number,
    }


# ── LiveKit SIP helpers ───────────────────────────────────────────────────────

def sip_called_number(room) -> str | None:
    """Best-effort DIALED (destination) number for a LiveKit SIP call — i.e. the tenant's
    Twilio number that the caller dialed. LiveKit exposes it on the SIP participant's
    attributes (sip.trunkPhoneNumber is the trunk/called number; sip.to_number on some
    setups). This is the phone -> tenant routing key at the agent layer."""
    try:
        participants = list(getattr(room, "remote_participants", {}).values())
    except Exception:
        return None
    for p in participants:
        attrs = getattr(p, "attributes", None) or {}
        for key in ("sip.trunkPhoneNumber", "sip.to_number", "sip.dnis",
                    "sip.calledNumber", "sip.ruleID"):
            val = attrs.get(key)
            if val and re.search(r"\d", val):
                return val
    return None


def sip_caller_number(room) -> str | None:
    """Best-effort CALLER (origin) number for a LiveKit SIP call — i.e. the number the
    person is calling FROM. Used for caller recognition (greet a returning caller by name).
    LiveKit exposes it on the SIP participant attributes (sip.phoneNumber is the caller;
    sip.from_number on some setups). Distinct from sip_called_number (the dialed/tenant
    number). Returns None when it can't be read."""
    try:
        participants = list(getattr(room, "remote_participants", {}).values())
    except Exception:
        return None
    for p in participants:
        attrs = getattr(p, "attributes", None) or {}
        for key in ("sip.phoneNumber", "sip.from_number", "sip.from", "sip.ani"):
            val = attrs.get(key)
            if val and re.search(r"\d", val):
                return val
    return None


async def tenant_context_for_room(db, room) -> tuple[str, dict] | None:
    """Resolve (tenant_id, config) for a freshly-joined inbound `call-*` room.

    Reads the dialed number off the SIP join and matches it to a tenant. If the number
    can't be read (SIP attributes are best-effort across providers), falls back to the
    default tenant so the original single-tenant clinic keeps working. Returns None only
    when there are no tenants at all (nothing to serve)."""
    number = sip_called_number(room)
    tenant = await resolve_tenant_by_number(db, number) if number else None
    if not tenant:
        tenant = await get_default_tenant(db)
    if not tenant:
        return None
    config = await load_tenant_config(db, tenant)
    return tenant.id, config
