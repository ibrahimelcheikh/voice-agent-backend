"""
Agent action tools — shared by the live voice agent (pipecat_agent.py) and the
demo simulation endpoint (/demo/simulate-call).

Each tool is exposed to the LLM via OpenAI function-calling. When the model
decides to call a tool we run the matching async executor against the database
and feed the natural-language result back into the conversation.
"""
from datetime import datetime, date
from sqlalchemy import select, desc
from app.db.database import AsyncSessionLocal
from app.models.models import (
    Reservation, Order, FAQ, Call,
    ReservationStatus, OrderType, OrderStatus, CallOutcome,
)

# ── OpenAI function-calling schemas ──────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "create_reservation",
            "description": "Book a table reservation for a customer at one of the Golden Fork locations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "customer_phone": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "date": {"type": "string", "description": "Reservation date, ISO format YYYY-MM-DD"},
                    "time": {"type": "string", "description": "Reservation time, 24h HH:MM"},
                    "location": {"type": "string", "enum": ["Downtown", "Midtown", "Uptown", "Airport"]},
                },
                "required": ["customer_name", "customer_phone", "party_size", "date", "time", "location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reservation",
            "description": "Cancel an existing reservation by phone number or reservation id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_phone": {"type": "string"},
                    "reservation_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_reservation",
            "description": "Look up a customer's upcoming reservation by phone number.",
            "parameters": {
                "type": "object",
                "properties": {"customer_phone": {"type": "string"}},
                "required": ["customer_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_faq",
            "description": "Answer a common customer question (hours, parking, delivery, menu, policies) from the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_order",
            "description": "Place a food order for delivery, pickup, or dine-in.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "customer_phone": {"type": "string"},
                    "order_type": {"type": "string", "enum": ["delivery", "pickup", "dine_in"]},
                    "items": {
                        "type": "array",
                        "description": "Ordered items",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "qty": {"type": "integer"},
                                "price": {"type": "number", "description": "Unit price in dollars"},
                            },
                            "required": ["name", "qty"],
                        },
                    },
                    "address": {"type": "string", "description": "Required for delivery orders"},
                },
                "required": ["customer_name", "customer_phone", "order_type", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_order_status",
            "description": "Check the status of a customer's latest order by phone number.",
            "parameters": {
                "type": "object",
                "properties": {"customer_phone": {"type": "string"}},
                "required": ["customer_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "Escalate the call to a human team member when the customer is upset, the request is out of scope, or they explicitly ask for a person.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
        },
    },
]

# Menu used to fill in prices when the model omits them.
MENU_PRICES = {
    "grilled salmon": 2400, "burger": 1600, "caesar salad": 1400,
    "margherita pizza": 1800, "ribeye steak": 3200, "pasta alfredo": 1900,
    "fish tacos": 1500, "chicken wings": 1200, "tiramisu": 900,
    "lemonade": 500, "espresso": 400, "house wine": 1100,
}


def _to_cents(price) -> int:
    try:
        return int(round(float(price) * 100))
    except (TypeError, ValueError):
        return 0


# ── Executors ────────────────────────────────────────────────────────────────
# Each returns (response_text, result_payload). `escalated` flag in the payload
# lets the caller flag the call for human handoff.

async def _create_reservation(args, db):
    res = Reservation(
        customer_name=args.get("customer_name", "Guest"),
        customer_phone=args.get("customer_phone", ""),
        party_size=int(args.get("party_size", 2)),
        date=args.get("date", date.today().isoformat()),
        time=args.get("time", "19:00"),
        location=args.get("location", "Downtown"),
        status=ReservationStatus.confirmed,
        created_via="voice",
    )
    db.add(res)
    await db.commit()
    msg = (f"Perfect! I've booked a table for {res.party_size} on {res.date} at "
           f"{res.time} at our {res.location} location. See you then!")
    return msg, {"reservation_id": res.id, "status": "confirmed"}


async def _cancel_reservation(args, db):
    q = select(Reservation)
    if args.get("reservation_id"):
        q = q.where(Reservation.id == args["reservation_id"])
    elif args.get("customer_phone"):
        q = q.where(Reservation.customer_phone == args["customer_phone"]).order_by(desc(Reservation.created_at))
    else:
        return "I need your phone number or reservation ID to cancel.", {"cancelled": False}
    res = (await db.execute(q)).scalars().first()
    if not res:
        return "I couldn't find a reservation under that information.", {"cancelled": False}
    res.status = ReservationStatus.cancelled
    await db.commit()
    return "I've cancelled your reservation. We hope to see you again soon!", {"reservation_id": res.id, "cancelled": True}


async def _check_reservation(args, db):
    today = date.today().isoformat()
    res = (await db.execute(
        select(Reservation)
        .where(Reservation.customer_phone == args.get("customer_phone", ""),
               Reservation.date >= today,
               Reservation.status != ReservationStatus.cancelled)
        .order_by(Reservation.date)
    )).scalars().first()
    if not res:
        return "I don't see any upcoming reservations under that number.", {"found": False}
    return (f"I found your reservation for {res.party_size} on {res.date} at "
            f"{res.time} at our {res.location} location."), {"found": True, "reservation_id": res.id}


async def _answer_faq(args, db):
    question = (args.get("question") or "").lower()
    faqs = (await db.execute(select(FAQ))).scalars().all()
    best, best_score = None, 0
    q_words = {w for w in question.replace("?", "").split() if len(w) > 2}
    for f in faqs:
        f_words = {w for w in f.question.lower().replace("?", "").split() if len(w) > 2}
        score = len(q_words & f_words)
        if score > best_score:
            best, best_score = f, score
    if best and best_score > 0:
        best.times_asked = (best.times_asked or 0) + 1
        await db.commit()
        return best.answer, {"matched_question": best.question}
    return ("I'm not certain about that one — let me note it down and a team member "
            "can follow up."), {"matched_question": None}


async def _take_order(args, db):
    raw_items = args.get("items") or []
    items, total = [], 0
    for it in raw_items:
        name = it.get("name", "item")
        qty = int(it.get("qty", 1))
        price_cents = _to_cents(it.get("price")) or MENU_PRICES.get(name.lower(), 0)
        items.append({"name": name, "qty": qty, "price": price_cents})
        total += price_cents * qty
    order_type = args.get("order_type", "pickup")
    order = Order(
        customer_name=args.get("customer_name", "Guest"),
        customer_phone=args.get("customer_phone", ""),
        order_type=OrderType(order_type) if order_type in OrderType._value2member_map_ else OrderType.pickup,
        items=items,
        total=total,
        status=OrderStatus.received,
        address=args.get("address"),
        created_via="voice",
    )
    db.add(order)
    await db.commit()
    return ("Your order has been placed! Estimated time is 30-45 minutes."), {
        "order_id": order.id, "total_cents": total, "status": "received"}


async def _check_order_status(args, db):
    order = (await db.execute(
        select(Order)
        .where(Order.customer_phone == args.get("customer_phone", ""))
        .order_by(desc(Order.created_at))
    )).scalars().first()
    if not order:
        return "I don't see any recent orders under that number.", {"found": False}
    eta = {"received": "30-45 minutes", "preparing": "20-30 minutes",
           "ready": "ready for pickup now", "delivered": "already delivered"}.get(order.status.value, "soon")
    return (f"Your order is currently {order.status.value}. Estimated delivery in {eta}."), {
        "found": True, "order_id": order.id, "status": order.status.value}


async def _transfer_to_human(args, db):
    return ("Let me transfer you to one of our team members right away."), {
        "escalated": True, "reason": args.get("reason", "customer requested human")}


_EXECUTORS = {
    "create_reservation": _create_reservation,
    "cancel_reservation": _cancel_reservation,
    "check_reservation": _check_reservation,
    "answer_faq": _answer_faq,
    "take_order": _take_order,
    "check_order_status": _check_order_status,
    "transfer_to_human": _transfer_to_human,
}


async def execute_tool(name: str, args: dict, db=None):
    """Run a tool by name. If no db session is supplied, open a fresh one.

    Returns (response_text: str, result_payload: dict).
    """
    executor = _EXECUTORS.get(name)
    if not executor:
        return f"Unknown tool: {name}", {"error": "unknown_tool"}
    if db is not None:
        return await executor(args or {}, db)
    async with AsyncSessionLocal() as session:
        return await executor(args or {}, session)
