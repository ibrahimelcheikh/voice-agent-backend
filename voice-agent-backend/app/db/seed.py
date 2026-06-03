"""
Rich demo seed — "Aria", the AI receptionist for the Golden Fork restaurant chain.

Seeds: admin user, 2 behavior configs, 4 agents, 3 campaigns, 30 FAQs,
50 reservations, 80 orders, 100 calls with realistic transcripts, and a
WhatsApp conversation.
"""
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.models import (
    User, Agent, BehaviorConfig, Campaign, Call,
    WhatsAppConversation, WhatsAppMessage,
    Reservation, Order, FAQ,
    AgentType, AgentStatus, CallDirection, CallOutcome, CampaignStatus,
    ReservationStatus, OrderType, OrderStatus,
)
from datetime import datetime, timedelta, date
import random
import uuid
import bcrypt


def safe_hash(password: str) -> str:
    """Hash a password with bcrypt, guarding the 72-byte limit.

    Uses the bcrypt library directly (not passlib) — passlib 1.7.4's bcrypt
    backend runs a self-test that hashes >72-byte strings and crashes on
    newer bcrypt releases with "password cannot be longer than 72 bytes".
    """
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")

LOCATIONS = ["Downtown", "Midtown", "Uptown", "Airport"]
NAMES = [
    "John Smith", "Maria Santos", "Omar Hassan", "Emily Chen", "David Johnson",
    "Aisha Khan", "Carlos Rivera", "Sophie Martin", "Liam O'Brien", "Fatima Ali",
    "Noah Williams", "Yuki Tanaka", "Grace Park", "Mohammed Saleh", "Olivia Brown",
    "Lucas Silva", "Hana Kim", "James Wilson", "Layla Ahmed", "Ethan Davis",
    "Priya Patel", "Daniel Lee", "Nadia Farah", "Mateo Gomez", "Chloe Taylor",
]
MENU = [
    ("Grilled Salmon", 2400), ("Burger", 1600), ("Caesar Salad", 1400),
    ("Margherita Pizza", 1800), ("Ribeye Steak", 3200), ("Pasta Alfredo", 1900),
    ("Fish Tacos", 1500), ("Chicken Wings", 1200), ("Tiramisu", 900),
    ("Lemonade", 500), ("Espresso", 400), ("House Wine", 1100),
]


def _uuid32():
    return str(uuid.uuid4()).replace("-", "")


def _phone():
    return f"+1415555{random.randint(1000, 9999)}"


async def seed_mock_data():
    async with AsyncSessionLocal() as db:
        if (await db.execute(select(User))).scalars().first():
            return  # already seeded

        _seed_core(db)
        await db.flush()  # ensure agents/configs exist before FK-dependent rows
        _seed_faqs(db)
        _seed_reservations(db)
        _seed_orders(db)
        _seed_calls(db)
        _seed_whatsapp(db)

        await db.commit()
        print("[seed] Golden Fork demo data seeded "
              "(4 agents · 3 campaigns · 30 FAQs · 50 reservations · 80 orders · 100 calls)")


def _seed_core(db):
    db.add(User(id="usr-admin-001", name="Ibrahim Admin",
                email="admin@primetechai.com", password_hash=safe_hash("demo1234")))

    inbound_config = BehaviorConfig(
        id="cfg-inbound-001",
        name="Golden Fork — Aria (Inbound Receptionist)",
        version=1,
        system_prompt=(
            "You are Aria, the warm and efficient AI receptionist for the Golden Fork "
            "restaurant chain (Downtown, Midtown, Uptown, Airport). You answer calls "
            "professionally, book and manage reservations, take orders, answer menu and "
            "policy questions, and escalate to a human when needed. Always collect the "
            "caller's name and phone number. Use your tools to take real actions."
        ),
        hard_rules=[
            {"rule": "Never discuss competitor restaurants", "enabled": True},
            {"rule": "Always collect caller name and phone", "enabled": True},
            {"rule": "Never stay on a call over 8 minutes", "enabled": True},
            {"rule": "Never promise refunds without manager approval", "enabled": True},
        ],
        soft_rules=[
            {"rule": "Use the customer's name when known", "enabled": True},
            {"rule": "Suggest popular dishes when taking orders", "enabled": True},
            {"rule": "Mention the loyalty program when appropriate", "enabled": True},
        ],
        blocked_topics=["competitors", "staff salaries", "pricing complaints"],
        escalation_triggers=["angry customer", "refund request over $50", "legal threat",
                             "wants to speak to a human"],
        data_extraction_fields=["name", "phone", "reservation_date", "party_size", "issue_type"],
        max_call_duration=480,
        versions=[],
    )
    outbound_config = BehaviorConfig(
        id="cfg-outbound-001",
        name="Golden Fork — Win-back Outbound",
        version=1,
        system_prompt=(
            "You are an AI agent for Golden Fork making friendly outbound calls to past "
            "guests, inviting them back with a seasonal offer and optionally booking a table. "
            "Always identify yourself as an AI assistant. Never be pushy."
        ),
        hard_rules=[
            {"rule": "Always identify yourself as an AI agent", "enabled": True},
            {"rule": "Respect Do Not Call requests immediately", "enabled": True},
            {"rule": "Never make false promises about offers", "enabled": True},
        ],
        soft_rules=[
            {"rule": "Keep calls under 4 minutes", "enabled": True},
            {"rule": "Offer to book a table on the spot", "enabled": True},
        ],
        blocked_topics=["competitors", "guaranteed results"],
        escalation_triggers=["wants to speak to a human", "complaint"],
        data_extraction_fields=["name", "phone", "interested", "preferred_location"],
        max_call_duration=300,
        versions=[],
    )
    db.add_all([inbound_config, outbound_config])

    db.add_all([
        Agent(id="agt-001", name="Aria — Inbound Receptionist", type=AgentType.inbound,
              language="en", voice_id="shimmer", status=AgentStatus.active,
              behavior_config_id="cfg-inbound-001", phone_number="+16575347796",
              calls_today=14, total_calls=486, avg_score=89.6),
        Agent(id="agt-002", name="Leo — Win-back Outbound", type=AgentType.outbound,
              language="en", voice_id="echo", status=AgentStatus.idle,
              behavior_config_id="cfg-outbound-001", phone_number="+16575347796",
              calls_today=9, total_calls=203, avg_score=81.4),
        Agent(id="agt-003", name="Zara — WhatsApp Agent", type=AgentType.whatsapp,
              language="en", voice_id="nova", status=AgentStatus.active,
              behavior_config_id="cfg-inbound-001",
              calls_today=27, total_calls=934, avg_score=92.1),
        Agent(id="agt-004", name="Milo — Order Follow-up", type=AgentType.track,
              language="en", voice_id="alloy", status=AgentStatus.idle,
              calls_today=6, total_calls=121, avg_score=94.3),
    ])

    db.add_all([
        Campaign(id="cmp-001", name="Spring Win-back Drive", agent_id="agt-002",
                 status=CampaignStatus.active, total_contacts=150, called_count=89,
                 connected_count=67, voicemail_count=15, failed_count=7,
                 calls_per_hour=12, retry_attempts=2,
                 contacts=[{"name": n, "phone": _phone()} for n in NAMES[:8]],
                 script="Hi, this is Leo from Golden Fork with a little something for you..."),
        Campaign(id="cmp-002", name="Reservation Confirmation Follow-up", agent_id="agt-001",
                 status=CampaignStatus.completed, total_contacts=50, called_count=50,
                 connected_count=43, voicemail_count=5, failed_count=2,
                 calls_per_hour=10, retry_attempts=1, contacts=[]),
        Campaign(id="cmp-003", name="Grand Re-opening Invitations", agent_id="agt-002",
                 status=CampaignStatus.draft, total_contacts=200, called_count=0,
                 connected_count=0, voicemail_count=0, failed_count=0,
                 calls_per_hour=15, retry_attempts=3,
                 contacts=[{"name": n, "phone": _phone()} for n in NAMES[8:16]]),
    ])


def _seed_faqs(db):
    faqs = [
        ("What are your hours?", "We're open 7 days a week, 11am to 11pm.", "hours"),
        ("Do you have vegetarian options?", "Yes, we have a dedicated vegetarian menu with over 12 dishes.", "menu"),
        ("What is your cancellation policy?", "You can cancel up to 2 hours before your reservation at no charge.", "policy"),
        ("Do you offer delivery?", "Yes, we deliver within 5 miles via our app and partner couriers.", "delivery"),
        ("Is parking available?", "Free parking is available at all of our locations.", "locations"),
        ("Do you take walk-ins?", "Absolutely! Walk-ins are welcome, though reservations are recommended on weekends.", "reservations"),
        ("Are you pet friendly?", "Our patios are pet friendly at the Downtown and Midtown locations.", "locations"),
        ("Do you have gluten-free options?", "Yes, many dishes can be prepared gluten-free — just let your server know.", "menu"),
        ("Can I book a private event?", "Yes! We host private events and catering. I can connect you with our events team.", "events"),
        ("Do you have a kids menu?", "Yes, we offer a kids menu for guests under 12.", "menu"),
        ("What payment methods do you accept?", "We accept all major cards, mobile payments, and cash.", "policy"),
        ("Is there a dress code?", "Smart casual is recommended, but we welcome all our guests comfortably dressed.", "policy"),
        ("Do you have outdoor seating?", "Yes, all locations have outdoor patios, weather permitting.", "locations"),
        ("How far in advance can I book?", "You can book up to 60 days in advance.", "reservations"),
        ("Do you have a loyalty program?", "Yes! Our Golden Rewards program earns you points on every visit.", "loyalty"),
        ("Where are you located?", "We have four locations: Downtown, Midtown, Uptown, and Airport.", "locations"),
        ("Do you cater large groups?", "Yes, we accommodate groups up to 12 in-house and cater larger events.", "events"),
        ("What is your most popular dish?", "Our Grilled Salmon and signature Burger are guest favorites.", "menu"),
        ("Do you serve alcohol?", "Yes, we have a full bar and curated wine list.", "menu"),
        ("Can I modify my reservation?", "Of course — I can update the time, party size, or location for you.", "reservations"),
        ("Do you have high chairs?", "Yes, high chairs and booster seats are available at all locations.", "locations"),
        ("Is delivery free?", "Delivery is free on orders over $30; otherwise a small fee applies.", "delivery"),
        ("How long does delivery take?", "Delivery typically takes 30–45 minutes depending on location.", "delivery"),
        ("Do you offer pickup?", "Yes, pickup orders are usually ready in 20–30 minutes.", "delivery"),
        ("Do you have vegan dishes?", "Yes, we have several vegan dishes clearly marked on our menu.", "menu"),
        ("Can I bring my own cake?", "Yes, a small plating fee applies for outside desserts.", "policy"),
        ("Do you validate parking?", "Parking is free, so no validation is needed.", "locations"),
        ("What's the wait time on weekends?", "Weekend waits range 15–30 minutes; reservations skip the line.", "reservations"),
        ("Do you have happy hour?", "Yes! Happy hour runs 4–6pm daily with drink and appetizer specials.", "menu"),
        ("Can I reserve for a birthday?", "Absolutely — let us know and we'll add a special touch for the celebration.", "events"),
    ]
    for q, a, cat in faqs:
        db.add(FAQ(agent_id="agt-001", question=q, answer=a, category=cat,
                   times_asked=random.randint(0, 140)))


def _seed_reservations(db):
    statuses = list(ReservationStatus)
    for i in range(50):
        upcoming = i < 30
        if upcoming:
            d = date.today() + timedelta(days=random.randint(0, 7))
            status = random.choice([ReservationStatus.confirmed, ReservationStatus.confirmed,
                                    ReservationStatus.pending])
        else:
            d = date.today() - timedelta(days=random.randint(1, 40))
            status = random.choice([ReservationStatus.completed, ReservationStatus.completed,
                                    ReservationStatus.no_show, ReservationStatus.cancelled])
        hour = random.choice([12, 13, 18, 19, 19, 20, 20, 21])
        minute = random.choice([0, 0, 15, 30, 45])
        db.add(Reservation(
            agent_id="agt-001",
            customer_name=random.choice(NAMES),
            customer_phone=_phone(),
            party_size=random.randint(2, 12),
            date=d.isoformat(),
            time=f"{hour:02d}:{minute:02d}",
            location=random.choice(LOCATIONS),
            status=status,
            created_via=random.choice(["voice", "voice", "whatsapp", "manual"]),
            notes=random.choice([None, None, "Window seat please", "Birthday celebration",
                                 "Allergic to nuts", "Anniversary dinner"]),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
        ))


def _seed_orders(db):
    for i in range(80):
        otype = random.choice(list(OrderType))
        n_items = random.randint(1, 4)
        items, total = [], 0
        for _ in range(n_items):
            name, price = random.choice(MENU)
            qty = random.randint(1, 3)
            items.append({"name": name, "qty": qty, "price": price})
            total += price * qty
        status = random.choice([OrderStatus.received, OrderStatus.preparing, OrderStatus.ready,
                                OrderStatus.delivered, OrderStatus.delivered, OrderStatus.cancelled])
        db.add(Order(
            agent_id="agt-001",
            customer_name=random.choice(NAMES),
            customer_phone=_phone(),
            order_type=otype,
            items=items,
            total=total,
            status=status,
            address=f"{random.randint(1, 200)} {random.choice(['Oak', 'Maple', 'Main', 'Pine', 'Cedar'])} Street"
                    if otype == OrderType.delivery else None,
            created_via=random.choice(["voice", "voice", "whatsapp"]),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 14),
                                                     hours=random.randint(0, 23)),
        ))


# Transcript templates keyed to scenario -> (transcript, extracted_data, outcome, score_range)
def _call_templates():
    return [
        ("reservation",
         "Aria: Thank you for calling Golden Fork, this is Aria. How can I help you?\n"
         "Customer: I'd like to book a table for 4 this Saturday at 7pm.\n"
         "Aria: Wonderful! Which location would you prefer?\n"
         "Customer: Downtown please.\n"
         "Aria: Great. May I have your name and phone number?\n"
         "Customer: John Smith, 415-555-0142.\n"
         "Aria: Perfect! I've booked a table for 4 on Saturday at 7pm at our Downtown location. See you then, John!",
         {"name": "John Smith", "phone": "+14155550142", "party_size": 4, "location": "Downtown", "intent": "reservation"},
         CallOutcome.resolved, (88, 97)),
        ("order",
         "Aria: Thanks for calling Golden Fork, this is Aria. How can I help?\n"
         "Customer: I'd like to place a delivery order.\n"
         "Aria: Of course! What would you like?\n"
         "Customer: Two burgers and a Caesar salad.\n"
         "Aria: Got it. Your name, phone, and delivery address?\n"
         "Customer: Maria Santos, 415-555-0188, 22 Oak Street.\n"
         "Aria: Your order has been placed! Estimated time is 30 to 45 minutes. Thank you, Maria!",
         {"name": "Maria Santos", "phone": "+14155550188", "order_type": "delivery", "intent": "order"},
         CallOutcome.resolved, (85, 95)),
        ("faq",
         "Aria: Golden Fork, this is Aria. How can I help you?\n"
         "Customer: What are your hours, and is parking available?\n"
         "Aria: We're open 7 days a week, 11am to 11pm, and free parking is available at all locations.\n"
         "Customer: Great, do you have vegetarian options?\n"
         "Aria: Yes, we have a dedicated vegetarian menu. Anything else?\n"
         "Customer: That's all, thanks!\n"
         "Aria: Happy to help — have a great day!",
         {"intent": "faq", "topics": ["hours", "parking", "vegetarian"]},
         CallOutcome.resolved, (90, 98)),
        ("complaint",
         "Aria: Thank you for calling Golden Fork, this is Aria. How can I help?\n"
         "Customer: My last delivery arrived completely cold and I'm really upset.\n"
         "Aria: I'm so sorry to hear that — that's not the experience we want for you.\n"
         "Customer: I want to speak to a manager right now.\n"
         "Aria: Absolutely. Let me transfer you to one of our team members right away.",
         {"intent": "complaint", "issue_type": "cold_food", "escalated": True},
         CallOutcome.escalated, (62, 75)),
        ("cancel",
         "Aria: Golden Fork, this is Aria. How can I help?\n"
         "Customer: I need to cancel my reservation. My phone is 415-555-0142.\n"
         "Aria: Of course, let me find that for you.\n"
         "Customer: Yes, please cancel it.\n"
         "Aria: I've cancelled your reservation. We hope to see you again soon!",
         {"name": "John Smith", "phone": "+14155550142", "intent": "cancel"},
         CallOutcome.resolved, (84, 93)),
    ]


def _seed_calls(db):
    templates = _call_templates()
    for i in range(100):
        roll = random.random()
        started = datetime.utcnow() - timedelta(days=random.randint(0, 30),
                                                hours=random.randint(0, 23),
                                                minutes=random.randint(0, 59))
        agent_id = random.choice(["agt-001", "agt-001", "agt-002"])
        direction = CallDirection.outbound if agent_id == "agt-002" else CallDirection.inbound

        if roll < 0.15:
            # No-answer / voicemail — short, no transcript
            outcome = random.choice([CallOutcome.no_answer, CallOutcome.voicemail, CallOutcome.abandoned])
            duration = random.randint(5, 35)
            db.add(Call(
                agent_id=agent_id, direction=direction,
                campaign_id="cmp-001" if direction == CallDirection.outbound else None,
                twilio_call_sid=f"CA{_uuid32()}",
                caller_number=_phone(), called_number="+16575347796",
                duration_seconds=duration, outcome=outcome,
                recording_url="https://demo.example.com/recording.mp3",
                started_at=started, ended_at=started + timedelta(seconds=duration),
            ))
            continue

        scenario, transcript, extracted, outcome, score_range = random.choice(templates)
        duration = random.randint(60, 420)
        score = round(random.uniform(*score_range), 1)
        sentiment_overall = "negative" if outcome == CallOutcome.escalated else random.choice(
            ["positive", "positive", "neutral"])
        timeline = ([0.2, 0.3, -0.5, -0.4, -0.6] if outcome == CallOutcome.escalated
                    else [round(random.uniform(0.1, 0.5), 2)] + [round(random.uniform(0.4, 0.95), 2) for _ in range(4)])
        db.add(Call(
            agent_id=agent_id, direction=direction,
            campaign_id="cmp-001" if direction == CallDirection.outbound else None,
            twilio_call_sid=f"CA{_uuid32()}",
            caller_number=extracted.get("phone", _phone()), called_number="+16575347796",
            duration_seconds=duration, outcome=outcome, ai_score=score,
            transcript=transcript,
            recording_url="https://demo.example.com/recording.mp3",
            extracted_data=extracted,
            rule_violations=([] if outcome != CallOutcome.escalated
                             else ["Resolution incomplete — escalated to human"]),
            sentiment_data={"overall": sentiment_overall, "timeline": timeline},
            ai_analysis={
                "score": score,
                "summary": f"{scenario.capitalize()} call — {outcome.value}.",
                "greeting": random.randint(80, 100),
                "professionalism": random.randint(80, 100),
                "resolution": random.randint(60, 100) if outcome != CallOutcome.escalated else random.randint(40, 65),
                "recommendations": random.choice([
                    ["Excellent greeting", "Clear confirmation of details"],
                    ["Good empathy", "Could offer loyalty program"],
                    ["Strong close", "Confirm spelling of names"],
                ]),
            },
            started_at=started, ended_at=started + timedelta(seconds=duration),
        ))


def _seed_whatsapp(db):
    conv = WhatsAppConversation(
        id="wa-001", agent_id="agt-003",
        contact_number="+14155550188", contact_name="Maria Santos",
        status="active", message_count=6,
        last_message="See you then Maria! Have a wonderful evening.",
        last_message_at=datetime.utcnow() - timedelta(hours=2),
    )
    db.add(conv)
    messages = [
        ("customer", "Hi, I'd like to book a table for 2 tomorrow at 8pm"),
        ("agent", "Hi Maria! I'd be happy to help. We have availability at 8pm tomorrow. Which location and may I confirm your phone number?"),
        ("customer", "Downtown, and my number is 415-555-0188"),
        ("agent", "Perfect! I've booked a table for 2 at 8pm tomorrow at our Downtown location. You'll get a confirmation shortly."),
        ("customer", "Thank you! See you tomorrow."),
        ("agent", "See you then Maria! Have a wonderful evening."),
    ]
    for role, content in messages:
        db.add(WhatsAppMessage(conversation_id="wa-001", role=role, content=content))

    conv2 = WhatsAppConversation(
        id="wa-002", agent_id="agt-003",
        contact_number="+14155551234", contact_name="Omar Hassan",
        status="handed_off", message_count=4,
        last_message="You're being connected to a team member. They'll be with you shortly.",
        last_message_at=datetime.utcnow() - timedelta(hours=5),
    )
    db.add(conv2)
    for role, content in [
        ("customer", "My order was wrong and I'm not happy"),
        ("agent", "I'm very sorry about that, Omar. Can you tell me what was wrong?"),
        ("customer", "I want a refund and to talk to someone"),
        ("agent", "You're being connected to a team member. They'll be with you shortly."),
    ]:
        db.add(WhatsAppMessage(conversation_id="wa-002", role=role, content=content))
