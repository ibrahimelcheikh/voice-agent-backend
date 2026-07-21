"""
Reversible switch of the callable phone number between the live restaurant tenant and the
Divinia clinic tenant. This is how you point inbound calls at Divinia for the demo — and how
you point them straight back at the restaurant afterwards (ONE command, fully reversible).

NOTHING is deleted. Only ONE field changes: which tenant owns `CALLABLE_NUMBER`
(tenants.twilio_phone_number, a UNIQUE column). The previous owner is freed in the same
transaction and its id is printed so you can always revert.

Usage (run where DATABASE_URL points at the target DB, e.g. on Railway or with the prod URL):
    CALLABLE_NUMBER=+16575347796 python -m scripts.switch_call_number divinia
    CALLABLE_NUMBER=+16575347796 python -m scripts.switch_call_number restaurant

`divinia` also ensures Divinia's FAQ knowledge base is populated (idempotent; only fills it if
empty), since the one-time seed does not re-run on an already-seeded database.
"""
import asyncio
import os
import sys

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.models import Tenant, Niche
from app.db.seed_atlasprimex import _DIVINIA_KB, DIVINIA_ID


# The live callable Twilio DID for the demo (confirmed: reassign from Beirut Bites to Divinia).
# Override with CALLABLE_NUMBER if this ever changes.
DEFAULT_CALLABLE_NUMBER = "+16575347796"


def _target_number() -> str:
    return (os.environ.get("CALLABLE_NUMBER") or DEFAULT_CALLABLE_NUMBER).strip()


async def _free_number(db, number: str, keep_id: str | None):
    """Null the number on any tenant that currently holds it (except keep_id). Returns the
    freed tenant's id (for revert), or None."""
    rows = (await db.execute(select(Tenant).where(Tenant.twilio_phone_number == number))).scalars().all()
    freed = None
    for t in rows:
        if t.id != keep_id:
            freed = t.id
            t.twilio_phone_number = None
    return freed


async def switch(target: str):
    number = _target_number()
    async with AsyncSessionLocal() as db:
        if target == "divinia":
            div = await db.get(Tenant, DIVINIA_ID)
            if not div:
                print(f"ERROR: Divinia tenant '{DIVINIA_ID}' not found — is the DB seeded?")
                sys.exit(1)
            freed = await _free_number(db, number, keep_id=DIVINIA_ID)
            div.twilio_phone_number = number
            if not (div.knowledge_base or {}):
                div.knowledge_base = _DIVINIA_KB   # idempotent: only fill when empty
                print("• Divinia knowledge base was empty — populated FAQ KB.")
            cfg = dict(div.config or {})
            if cfg.get("currency") != "SAR":
                cfg["currency"] = "SAR"            # so the agent quotes prices as "900 SAR"
                div.config = cfg
                print("• Divinia currency set to SAR.")
            await db.commit()
            print(f"✓ {number} now routes to Divinia Clinic ({DIVINIA_ID}).")
            if freed:
                print(f"  Previous owner freed: {freed}")
                print(f"  REVERT with: CALLABLE_NUMBER={number} python -m scripts.switch_call_number restaurant")
        elif target == "restaurant":
            # Find the live restaurant tenant (Beirut Bites). Prefer an explicit RESTAURANT_TENANT_ID.
            rid = (os.environ.get("RESTAURANT_TENANT_ID") or "").strip()
            rest = await db.get(Tenant, rid) if rid else None
            if not rest:
                rows = (await db.execute(select(Tenant).where(Tenant.niche == Niche.restaurant))).scalars().all()
                if len(rows) == 1:
                    rest = rows[0]
                elif len(rows) > 1:
                    print("Multiple restaurant tenants — set RESTAURANT_TENANT_ID to disambiguate:")
                    for t in rows:
                        print(f"  {t.id}  {t.business_name}")
                    sys.exit(1)
            if not rest:
                print("ERROR: no restaurant tenant found; set RESTAURANT_TENANT_ID explicitly.")
                sys.exit(1)
            await _free_number(db, number, keep_id=rest.id)
            rest.twilio_phone_number = number
            await db.commit()
            print(f"✓ {number} now routes back to {rest.business_name} ({rest.id}).")
        else:
            print("Usage: python -m scripts.switch_call_number <divinia|restaurant>")
            sys.exit(2)


if __name__ == "__main__":
    tgt = sys.argv[1] if len(sys.argv) > 1 else ""
    asyncio.run(switch(tgt))
