"""
Tenant-isolation test — proves the Phase 2 hardening holds.

Run it directly (single command), against the local Postgres the app uses:

    cd voice-agent-backend
    python -m tests.test_tenant_isolation

It seeds two restaurant tenants (A and B) with DIFFERENT menus, then asserts:

  1. menu_lookup / take_order / check_order scoped to tenant A NEVER return tenant B's
     rows (and vice-versa) — the structural isolation guarantee.
  2. A raw scoped_query(MenuItem, tenant_A) returns only tenant A's rows.
  3. Calling any tenant-scoped function with tenant_id=None RAISES (fail loud) instead
     of silently running an unscoped, cross-tenant query.

The test creates its own throwaway tenants (id prefix `test-iso-`) and deletes them
(and their rows) on the way in and out, so it is idempotent and leaves the real seed
data untouched. Prints a clear PASS/FAIL and exits non-zero on failure.
"""
import asyncio
import sys

from sqlalchemy import delete, select

from app.db.database import AsyncSessionLocal, engine, Base
from app.core.tenant_scope import scoped_query
from app.models.models import (
    Tenant, Niche, MenuItem, Order, OrderItem,
)
from app.agents.restaurant_functions import menu_lookup, take_order, check_order
from app.agents.clinic_functions import book_appointment
from app.agents.lead_functions import capture_lead
from app.agents.common_functions import faq_lookup, recognize_caller

TENANT_A = "test-iso-restaurant-a"
TENANT_B = "test-iso-restaurant-b"

# Distinct menus — no shared item names, so a leak is unambiguous.
MENU_A = [("Shawarma Alpha", 1200, "Mains"), ("Hummus Alpha", 600, "Mezze")]
MENU_B = [("Burger Bravo", 1500, "Mains"), ("Fries Bravo", 500, "Sides")]

PHONE_A = "+15550000001"


class Failed(Exception):
    pass


_passed = 0


def check(label, condition):
    global _passed
    if condition:
        _passed += 1
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}")
        raise Failed(label)


async def _raises_value_error(coro_factory, label):
    try:
        await coro_factory()
    except ValueError:
        check(label, True)
    else:
        check(label, False)


async def _cleanup(db):
    for tid in (TENANT_A, TENANT_B):
        await db.execute(delete(OrderItem).where(OrderItem.tenant_id == tid))
        await db.execute(delete(Order).where(Order.tenant_id == tid))
        await db.execute(delete(MenuItem).where(MenuItem.tenant_id == tid))
        await db.execute(delete(Tenant).where(Tenant.id == tid))
    await db.commit()


async def _seed(db):
    db.add(Tenant(id=TENANT_A, business_name="Iso Test A", niche=Niche.restaurant,
                  twilio_phone_number="+1999000111"))
    db.add(Tenant(id=TENANT_B, business_name="Iso Test B", niche=Niche.restaurant,
                  twilio_phone_number="+1999000222"))
    await db.flush()   # tenants must exist before their FK-bound menu items
    for name, price, cat in MENU_A:
        db.add(MenuItem(tenant_id=TENANT_A, name=name, price=price, category=cat, available=True))
    for name, price, cat in MENU_B:
        db.add(MenuItem(tenant_id=TENANT_B, name=name, price=price, category=cat, available=True))
    await db.commit()


async def main() -> int:
    # Tables must exist (the app creates them on boot; do it here so the test is standalone).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await _cleanup(db)   # idempotent: clear any leftovers from a prior run
        await _seed(db)

    try:
        print("\n[1] Reads scoped to tenant A never return tenant B's rows")
        a_menu = await menu_lookup(menu_query=None, tenant_id=TENANT_A)
        a_names = {i["name"] for i in a_menu["items"]}
        check("menu_lookup(A) returns A's items", a_names == {n for n, _, _ in MENU_A})
        check("menu_lookup(A) leaks NO B items", a_names.isdisjoint({n for n, _, _ in MENU_B}))

        b_menu = await menu_lookup(menu_query=None, tenant_id=TENANT_B)
        b_names = {i["name"] for i in b_menu["items"]}
        check("menu_lookup(B) returns B's items", b_names == {n for n, _, _ in MENU_B})
        check("menu_lookup(B) leaks NO A items", b_names.isdisjoint({n for n, _, _ in MENU_A}))

        # A specific lookup of B's dish against tenant A must NOT find it (falls back to A menu).
        cross = await menu_lookup(menu_query="Burger Bravo", tenant_id=TENANT_A)
        cross_names = {i["name"] for i in cross["items"]}
        check("specific lookup of B's dish under A does not surface it",
              "Burger Bravo" not in cross_names)

        print("\n[2] Orders are tenant-isolated")
        placed = await take_order(items=[{"name": "Shawarma Alpha", "quantity": 2}],
                                  customer_name="Tester", phone=PHONE_A, tenant_id=TENANT_A)
        check("take_order(A) succeeds for A's own item", placed.get("success") is True)
        seen_by_a = await check_order(phone=PHONE_A, tenant_id=TENANT_A)
        check("check_order(A) finds A's order", seen_by_a.get("found") is True)
        seen_by_b = await check_order(phone=PHONE_A, tenant_id=TENANT_B)
        check("check_order(B) does NOT see A's order", seen_by_b.get("found") is False)
        # take_order(B) for A's dish must reject it as off-B's-menu (never cross tenants).
        rejected = await take_order(items=[{"name": "Shawarma Alpha", "quantity": 1}],
                                    customer_name="Tester", phone=PHONE_A, tenant_id=TENANT_B)
        check("take_order(B) rejects A's dish as off-menu", rejected.get("success") is False)

        print("\n[3] Raw scoped_query only returns the scoped tenant's rows")
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(scoped_query(MenuItem, TENANT_A))).scalars().all()
            check("scoped_query(MenuItem, A) returns only A rows",
                  bool(rows) and all(r.tenant_id == TENANT_A for r in rows))

        print("\n[4] Missing tenant_id fails loud (no unscoped cross-tenant query)")
        await _raises_value_error(lambda: menu_lookup(menu_query=None, tenant_id=None),
                                  "menu_lookup(None) raises")
        await _raises_value_error(
            lambda: take_order(items=[{"name": "x"}], customer_name="t", phone="p", tenant_id=None),
            "take_order(None) raises")
        await _raises_value_error(lambda: check_order(phone=PHONE_A, tenant_id=None),
                                  "check_order(None) raises")
        await _raises_value_error(
            lambda: book_appointment(patient_name="t", phone="p", date="2026-06-10",
                                     time="10:00", tenant_id=None),
            "book_appointment(None) raises")
        await _raises_value_error(
            lambda: capture_lead(customer_name="t", phone="p", lead_type="x", tenant_id=None),
            "capture_lead(None) raises")
        await _raises_value_error(lambda: faq_lookup(query="hours", tenant_id=None),
                                  "faq_lookup(None) raises")
        await _raises_value_error(
            lambda: recognize_caller(phone=PHONE_A, niche="restaurant", tenant_id=None),
            "recognize_caller(None) raises")

        # Empty-string tenant_id is treated the same as missing.
        await _raises_value_error(lambda: menu_lookup(menu_query=None, tenant_id=""),
                                  "menu_lookup('') raises")
    finally:
        async with AsyncSessionLocal() as db:
            await _cleanup(db)

    print(f"\n==================  PASS  ({_passed} assertions)  ==================")
    return 0


if __name__ == "__main__":
    try:
        rc = asyncio.run(main())
    except Failed as e:
        print(f"\n==================  FAIL  ({e})  ==================")
        rc = 1
    except Exception as e:  # surface setup/DB errors clearly
        print(f"\n==================  ERROR  ({type(e).__name__}: {e})  ==================")
        rc = 2
    sys.exit(rc)
