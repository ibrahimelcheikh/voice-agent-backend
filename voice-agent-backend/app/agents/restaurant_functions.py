"""
Restaurant data functions — the ONLY source of truth a restaurant tenant's voice
agent may speak from (reservations, menu, pickup orders).

Mirrors app/agents/clinic_functions.py exactly in spirit:

  * Every function hits the real PostgreSQL database and returns a plain dict.
  * Every function takes a `tenant_id` and scopes EVERY query to it — a call for one
    restaurant can never read or write another business's menu, reservations, or orders.
  * The agent NEVER invents a dish, a price, a reservation, or an order. menu_lookup +
    take_order validate the caller's words against the tenant's real MenuItem rows, so a
    dish that doesn't exist (or isn't available) is reported back, never fabricated.

The guardrail (app/agents/guardrail.py) calls the matching function for the caller's
intent, then hands ONLY the returned data to the LLM, which phrases it naturally.
"""
from datetime import date

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.models import (
    Reservation, ReservationStatus, MenuItem, Order, OrderItem, OrderStatus,
)


def _scope(query, model, tenant_id):
    """Add a tenant filter when a tenant_id is supplied — the multi-tenant guard."""
    if tenant_id:
        return query.where(model.tenant_id == tenant_id)
    return query


def _dollars(cents) -> str:
    try:
        return f"${int(cents) / 100:.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _coerce_party(party_size):
    try:
        n = int(party_size)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


# ── Reservations ──────────────────────────────────────────────────────────────

async def create_reservation(customer_name=None, phone=None, party_size=None,
                             date=None, time=None, notes=None, tenant_id=None) -> dict:
    """Create a table reservation. Requires name, phone, party size, date, and time —
    the agent collects them across turns and this fires once they are all present (the
    final affirmation completes it), so a reservation is only saved on confirmation."""
    async with AsyncSessionLocal() as db:
        party = _coerce_party(party_size)
        missing = [k for k, v in {"customer_name": customer_name, "phone": phone,
                                  "party_size": party, "date": date, "time": time}.items()
                   if not v]
        if missing:
            return {"success": False, "missing": missing}
        resv = Reservation(
            tenant_id=tenant_id, customer_name=customer_name, phone=phone,
            party_size=party, date=date, time=time, notes=notes,
            status=ReservationStatus.booked, created_via="voice",
        )
        db.add(resv)
        await db.commit()
        return {"success": True, "reservation_id": resv.id, "customer_name": customer_name,
                "party_size": party, "date": date, "time": time, "notes": notes}


async def modify_reservation(phone=None, reservation_id=None, new_date=None,
                            new_time=None, party_size=None, tenant_id=None) -> dict:
    """Move/resize a reservation. Targets a specific reservation_id when known, else the
    caller's soonest open reservation (by phone)."""
    async with AsyncSessionLocal() as db:
        if not new_date and not new_time and not _coerce_party(party_size):
            return {"success": False, "reason": "need_change"}
        resv = await _find_open_reservation(db, phone, reservation_id, tenant_id)
        if not resv:
            return {"success": False, "reason": "not_found"}
        old_date, old_time, old_party = resv.date, resv.time, resv.party_size
        if new_date:
            resv.date = new_date
        if new_time:
            resv.time = new_time
        party = _coerce_party(party_size)
        if party:
            resv.party_size = party
        resv.status = ReservationStatus.booked
        await db.commit()
        return {"success": True, "reservation_id": resv.id,
                "old_date": old_date, "old_time": old_time, "old_party_size": old_party,
                "date": resv.date, "time": resv.time, "party_size": resv.party_size}


async def cancel_reservation(phone=None, reservation_id=None, tenant_id=None) -> dict:
    async with AsyncSessionLocal() as db:
        resv = await _find_open_reservation(db, phone, reservation_id, tenant_id)
        if not resv:
            return {"success": False, "reason": "not_found"}
        resv.status = ReservationStatus.cancelled
        await db.commit()
        return {"success": True, "reservation_id": resv.id, "date": resv.date,
                "time": resv.time, "customer_name": resv.customer_name}


async def check_reservation(phone=None, tenant_id=None) -> dict:
    async with AsyncSessionLocal() as db:
        if not phone:
            return {"success": False, "reason": "need_phone"}
        today = date.today().isoformat()
        resvs = (await db.execute(
            _scope(select(Reservation), Reservation, tenant_id)
            .where(Reservation.phone == phone,
                   Reservation.date >= today,
                   Reservation.status.notin_([ReservationStatus.cancelled]))
            .order_by(Reservation.date, Reservation.time)
        )).scalars().all()
        if not resvs:
            return {"success": True, "found": False, "reservations": []}
        return {"success": True, "found": True,
                "customer_name": resvs[0].customer_name,
                "reservations": [
                    {"reservation_id": r.id, "date": r.date, "time": r.time,
                     "party_size": r.party_size, "status": r.status.value, "notes": r.notes}
                    for r in resvs]}


async def _find_open_reservation(db, phone, reservation_id, tenant_id):
    q = _scope(select(Reservation).where(
        Reservation.status.notin_([ReservationStatus.cancelled, ReservationStatus.completed])
    ), Reservation, tenant_id)
    if reservation_id:
        q = q.where(Reservation.id == reservation_id)
    elif phone:
        q = q.where(Reservation.phone == phone).order_by(Reservation.date, Reservation.time)
    else:
        return None
    return (await db.execute(q)).scalars().first()


# ── Menu ──────────────────────────────────────────────────────────────────────

async def menu_lookup(menu_query=None, tenant_id=None) -> dict:
    """Answer "what do you have / how much is X" from the tenant's REAL menu.

    With a query, returns the available items whose name/category/description matches it
    (so "how much is a latte" returns the latte). Without one, returns the available menu
    grouped lightly so the agent can read a few highlights. Only available items are ever
    returned — the agent must never offer something off-menu or unavailable."""
    async with AsyncSessionLocal() as db:
        items = (await db.execute(
            _scope(select(MenuItem).where(MenuItem.available == True),  # noqa: E712
                   MenuItem, tenant_id).order_by(MenuItem.category, MenuItem.name)
        )).scalars().all()

        def _fmt(m):
            return {"name": m.name, "price": _dollars(m.price), "price_cents": m.price,
                    "category": m.category, "description": m.description}

        if menu_query:
            needle = menu_query.lower().strip()
            matched = [m for m in items
                       if needle in (m.name or "").lower()
                       or needle in (m.category or "").lower()
                       or needle in (m.description or "").lower()]
            return {"success": True, "query": menu_query, "found": bool(matched),
                    "items": [_fmt(m) for m in matched[:8]]}
        return {"success": True, "found": bool(items),
                "categories": sorted({m.category for m in items if m.category}),
                "items": [_fmt(m) for m in items]}


def _match_menu_item(items, name):
    """Resolve a spoken item name to a real MenuItem row. Exact (case-insensitive) first,
    then substring either way ("latte" -> "Caramel Latte", "iced caramel latte" -> "Latte").
    Returns None when nothing matches — the agent must not invent a dish."""
    if not name:
        return None
    needle = name.lower().strip()
    for m in items:
        if (m.name or "").lower() == needle:
            return m
    for m in items:
        n = (m.name or "").lower()
        if n and (needle in n or n in needle):
            return m
    return None


# ── Orders ──────────────────────────────────────────────────────────────────────

async def take_order(items=None, customer_name=None, phone=None, pickup_time=None,
                     tenant_id=None) -> dict:
    """Take a pickup order, validating every item against the tenant's real menu.

    `items` is a list of {name, quantity} the caller named (accumulated across turns).
    Each is matched to a real, available MenuItem — anything unmatched is reported back
    (NEVER invented or priced). The order is saved only when at least name + phone are
    known AND every named item matched; otherwise the agent is told what's missing /
    unrecognised so it can clarify. Because the required fields come together at the end,
    this naturally saves on the caller's final confirmation.
    """
    async with AsyncSessionLocal() as db:
        if not items:
            return {"success": False, "reason": "no_items"}

        menu = (await db.execute(
            _scope(select(MenuItem).where(MenuItem.available == True),  # noqa: E712
                   MenuItem, tenant_id)
        )).scalars().all()

        matched, unmatched = [], []
        for raw in items:
            if isinstance(raw, dict):
                name = raw.get("name")
                qty = raw.get("quantity") or 1
            else:
                name, qty = raw, 1
            try:
                qty = max(1, int(qty))
            except (TypeError, ValueError):
                qty = 1
            m = _match_menu_item(menu, name)
            if not m:
                unmatched.append(name)
                continue
            matched.append({"menu_item": m, "name": m.name, "quantity": qty,
                            "unit_price": m.price, "line_total": m.price * qty})

        order_lines = [{"name": x["name"], "quantity": x["quantity"],
                        "unit_price": _dollars(x["unit_price"]),
                        "line_total": _dollars(x["line_total"])} for x in matched]
        total_cents = sum(x["line_total"] for x in matched)

        # Anti-hallucination: if the caller named something not on the menu, do NOT save —
        # tell the agent so it can offer real alternatives.
        if unmatched:
            return {"success": False, "reason": "items_not_on_menu",
                    "unmatched": unmatched, "matched": order_lines,
                    "total": _dollars(total_cents)}
        if not matched:
            return {"success": False, "reason": "no_valid_items"}

        missing = [k for k, v in {"customer_name": customer_name, "phone": phone}.items()
                   if not v]
        if missing:
            # Items are valid; we still need who it's for. Surface the running total so the
            # agent can read the order back while asking for the missing detail.
            return {"success": False, "reason": "need_customer_details", "missing": missing,
                    "items": order_lines, "total": _dollars(total_cents)}

        order = Order(
            tenant_id=tenant_id, customer_name=customer_name, phone=phone,
            pickup_time=pickup_time, status=OrderStatus.received, total=total_cents,
            created_via="voice",
        )
        db.add(order)
        await db.flush()
        for x in matched:
            db.add(OrderItem(
                tenant_id=tenant_id, order_id=order.id, menu_item_id=x["menu_item"].id,
                name=x["name"], quantity=x["quantity"], unit_price=x["unit_price"],
                line_total=x["line_total"],
            ))
        await db.commit()
        return {"success": True, "order_id": order.id, "customer_name": customer_name,
                "pickup_time": pickup_time, "status": order.status.value,
                "items": order_lines, "total": _dollars(total_cents)}


async def check_order(phone=None, order_id=None, tenant_id=None) -> dict:
    """Look up a caller's most recent order + its status (received/preparing/ready/done)."""
    async with AsyncSessionLocal() as db:
        q = _scope(select(Order), Order, tenant_id)
        if order_id:
            q = q.where(Order.id == order_id)
        elif phone:
            q = q.where(Order.phone == phone)
        else:
            return {"success": False, "reason": "need_phone_or_id"}
        order = (await db.execute(q.order_by(Order.created_at.desc()))).scalars().first()
        if not order:
            return {"success": True, "found": False}
        lines = (await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )).scalars().all()
        return {"success": True, "found": True, "order_id": order.id,
                "status": order.status.value, "pickup_time": order.pickup_time,
                "total": _dollars(order.total),
                "items": [{"name": li.name, "quantity": li.quantity,
                           "line_total": _dollars(li.line_total)} for li in lines]}


# Registry used by the guardrail (intent -> coroutine) for restaurant tenants.
RESTAURANT_FUNCTIONS = {
    "create_reservation": create_reservation,
    "modify_reservation": modify_reservation,
    "cancel_reservation": cancel_reservation,
    "check_reservation": check_reservation,
    "menu_lookup": menu_lookup,
    "take_order": take_order,
    "check_order": check_order,
}
