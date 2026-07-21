"""
Reversible switch of the callable phone number between the live restaurant tenant and the
Divinia clinic tenant. This is how you point inbound calls at Divinia for the demo — and how
you point them straight back at the restaurant afterwards (ONE command, fully reversible).

NOTHING is deleted. Only ONE field changes: which tenant owns `CALLABLE_NUMBER`
(tenants.twilio_phone_number, a UNIQUE column). The previous owner is freed in the same
transaction. `divinia` also fills Divinia's FAQ KB + SAR currency if missing.

Shares its core with the boot hook (settings.ACTIVE_DEMO_TENANT) via
app.db.seed_atlasprimex.apply_call_number_switch, so both behave identically.

Usage (run where DATABASE_URL points at the target DB, e.g. on Railway or with the prod URL):
    python -m scripts.switch_call_number divinia
    python -m scripts.switch_call_number restaurant
    CALLABLE_NUMBER=+1... python -m scripts.switch_call_number divinia   # override the number
"""
import asyncio
import os
import sys

from app.db.database import AsyncSessionLocal
from app.db.seed_atlasprimex import apply_call_number_switch

# The live callable Twilio DID for the demo (confirmed: reassign from Beirut Bites to Divinia).
# Override with CALLABLE_NUMBER if this ever changes.
DEFAULT_CALLABLE_NUMBER = "+16575347796"


def _target_number() -> str:
    return (os.environ.get("CALLABLE_NUMBER") or DEFAULT_CALLABLE_NUMBER).strip()


async def switch(target: str):
    if target not in ("divinia", "restaurant"):
        print("Usage: python -m scripts.switch_call_number <divinia|restaurant>")
        sys.exit(2)
    number = _target_number()
    async with AsyncSessionLocal() as db:
        status = await apply_call_number_switch(db, target, number)
        await db.commit()
    print(f"✓ {status}")
    if target == "divinia":
        print("  REVERT with: python -m scripts.switch_call_number restaurant")


if __name__ == "__main__":
    tgt = sys.argv[1] if len(sys.argv) > 1 else ""
    asyncio.run(switch(tgt))
