"""
Local verification for niche-specific function sets (run against the real Postgres).

    python -m scripts.verify_niches

Does a clean reset + reseed (the exact fresh-seed path Railway FORCE_SEED runs), then
asserts, WITHOUT any phone/LLM:
  * phone -> tenant -> niche routing (clinic / restaurant / real_estate)
  * each niche loads ONLY its own function set + intents (no cross-niche intents)
  * restaurant: menu_lookup, take_order (incl. anti-hallucination on off-menu items),
    reservations create/check
  * lead capture: capture_lead
  * FAQ engine grounded in each tenant's knowledge base
  * caller recognition by phone, strictly tenant-scoped
  * cross-tenant isolation (no data leakage between businesses)
  * the original clinic (Tenant 1) still books/checks appointments unchanged

The live LLM classifier (GuardrailBrain.decide) is NOT exercised here — it needs an
OpenAI key, which isn't present locally. This verifies the grounded DATA layer the
classifier routes into, which is where the anti-hallucination guarantee lives.
"""
import asyncio
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.db.database import reset_schema, ensure_columns, backfill_default_tenant
from app.db.seed import seed_mock_data
from app.agents.niches import get_niche_spec
from app.agents import restaurant_functions as rf
from app.agents import lead_functions as lf
from app.agents import clinic_functions as cf
from app.agents.common_functions import faq_lookup, recognize_caller

CLINIC = "tenant-001"
RESTAURANT = "tenant-002"
LEAD = "tenant-003"

_passed = 0
_failed = 0


def check(label, cond):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ✅ {label}")
    else:
        _failed += 1
        print(f"  ❌ {label}")


async def main():
    print("Resetting + reseeding (fresh-seed path)...")
    await reset_schema()
    await ensure_columns()
    await seed_mock_data()
    await backfill_default_tenant()

    print("\n[1] Niche routing / function-set isolation")
    cs, rs, ls = get_niche_spec("clinic"), get_niche_spec("restaurant"), get_niche_spec("real_estate")
    check("clinic spec offers book_appointment", "book_appointment" in cs.intents)
    check("clinic spec does NOT offer take_order", "take_order" not in cs.intents)
    check("restaurant spec offers take_order + create_reservation",
          {"take_order", "create_reservation"} <= set(rs.intents))
    check("restaurant spec does NOT offer book_appointment", "book_appointment" not in rs.intents)
    check("lead spec offers capture_lead", "capture_lead" in ls.intents)
    check("lead spec does NOT offer book_appointment/take_order",
          not ({"book_appointment", "take_order"} & set(ls.intents)))
    check("FAQ available to ALL niches",
          all("faq" in s.intents for s in (cs, rs, ls)))
    check("dental + spa map to the clinic (appointment) spec",
          get_niche_spec("dental").key == "clinic" and get_niche_spec("spa").key == "clinic")
    check("automotive + services map to the lead spec",
          get_niche_spec("automotive").key == "lead" and get_niche_spec("services").key == "lead")

    print("\n[2] Restaurant — menu lookup (grounded in real menu)")
    m = await rf.menu_lookup(menu_query="latte", tenant_id=RESTAURANT)
    check("menu_lookup finds the Caramel Latte", m["found"] and any("Latte" in i["name"] for i in m["items"]))
    m_all = await rf.menu_lookup(tenant_id=RESTAURANT)
    check("menu_lookup lists the seeded menu", len(m_all["items"]) >= 10)
    m_clinic = await rf.menu_lookup(tenant_id=CLINIC)
    check("menu_lookup is empty for the clinic tenant (isolation)", m_clinic["items"] == [])

    print("\n[3] Restaurant — orders (anti-hallucination + save)")
    bad = await rf.take_order(items=[{"name": "Dragon Sushi", "quantity": 1}],
                              customer_name="Test", phone="+19610000099",
                              pickup_time="19:00", tenant_id=RESTAURANT)
    check("off-menu item is REJECTED, never invented",
          not bad["success"] and bad.get("reason") == "items_not_on_menu"
          and "Dragon Sushi" in bad.get("unmatched", []))
    good = await rf.take_order(items=[{"name": "beef burger", "quantity": 2},
                                      {"name": "Espresso", "quantity": 1}],
                               customer_name="Hungry Caller", phone="+19610000088",
                               pickup_time="19:30", tenant_id=RESTAURANT)
    # 2 * $15.00 + 1 * $3.50 = $33.50
    check("valid order saves with correct itemized total ($33.50)",
          good["success"] and good["total"] == "$33.50" and len(good["items"]) == 2)
    chk = await rf.check_order(phone="+19610000088", tenant_id=RESTAURANT)
    check("saved order is retrievable with status 'received'",
          chk["found"] and chk["status"] == "received")
    no_menu = await rf.take_order(items=[{"name": "Espresso", "quantity": 1}],
                                  customer_name="X", phone="+1", tenant_id=CLINIC)
    check("clinic tenant has no menu so order can't be taken (isolation)",
          not no_menu["success"])

    print("\n[4] Restaurant — reservations")
    r = await rf.create_reservation(customer_name="Verify Diner", phone="+19610000077",
                                    party_size=3, date="2026-07-01", time="20:00",
                                    notes="quiet table", tenant_id=RESTAURANT)
    check("reservation created", r["success"] and r["party_size"] == 3)
    rc = await rf.check_reservation(phone="+19610000077", tenant_id=RESTAURANT)
    check("reservation retrievable by phone", rc["found"])
    rc_iso = await rf.check_reservation(phone="+19610000077", tenant_id=CLINIC)
    check("reservation NOT visible to clinic tenant (isolation)", not rc_iso["found"])
    miss = await rf.create_reservation(customer_name="No Phone", tenant_id=RESTAURANT)
    check("incomplete reservation is not saved (asks for missing)", not miss["success"])

    print("\n[5] Lead capture")
    lead = await lf.capture_lead(customer_name="Lead Tester", phone="+19620000088",
                                 lead_type="villa", budget="$500k",
                                 requirements="sea view, Jbeil", tenant_id=LEAD)
    check("lead captured", lead["success"] and lead["lead_type"] == "villa")
    lc = await lf.check_lead(phone="+19620000088", tenant_id=LEAD)
    check("lead retrievable", lc["found"])
    lc_iso = await lf.check_lead(phone="+19620000088", tenant_id=RESTAURANT)
    check("lead NOT visible to restaurant tenant (isolation)", not lc_iso["found"])

    print("\n[6] FAQ engine (grounded in each tenant's knowledge base)")
    faq_r = await faq_lookup(query="what are your hours", tenant_id=RESTAURANT)
    check("restaurant FAQ returns its own hours", faq_r["found"] and "hours" in faq_r["knowledge"])
    faq_c = await faq_lookup(query="parking", tenant_id=CLINIC)
    # Clinic KB has no 'parking' key -> _kb_match returns the full clinic KB, never restaurant's.
    check("clinic FAQ never leaks restaurant data",
          "Gemmayze" not in str(faq_c.get("knowledge", {})))

    print("\n[7] Caller recognition (tenant-scoped)")
    # Recognize a seeded restaurant customer by phone.
    rec = await recognize_caller(phone="+19610000003", niche="restaurant", tenant_id=RESTAURANT)
    check("returning restaurant caller recognized by name", rec["found"] and rec.get("name"))
    rec_iso = await recognize_caller(phone="+19610000003", niche="clinic", tenant_id=CLINIC)
    check("same number NOT recognized under the clinic tenant (isolation)", not rec_iso["found"])

    print("\n[8] Clinic (Tenant 1) still works unchanged")
    b = await cf.book_appointment(patient_name="Verify Patient", phone="+14150009999",
                                  doctor="dentist", date="2026-07-02", time="10:00",
                                  reason="cleaning", tenant_id=CLINIC)
    check("clinic books an appointment", b["success"] and b["doctor"])
    ca = await cf.check_appointment(phone="+14150009999", tenant_id=CLINIC)
    check("clinic checks the appointment back", ca["found"])
    svc = await cf.get_services(tenant_id=CLINIC)
    check("clinic services still listed", len(svc["services"]) >= 8)

    print(f"\n{'=' * 50}\n  RESULT: {_passed} passed, {_failed} failed\n{'=' * 50}")
    return _failed == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    raise SystemExit(0 if ok else 1)
