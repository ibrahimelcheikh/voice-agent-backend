"""
Seed data — Prime Health Clinic AI receptionist demo.

Seeds: admin user, the clinic behavior lock config, inbound + WhatsApp agents,
the clinic, 5 doctors, 8 services, 6 insurance providers, 60 patients,
100 appointments (past + upcoming), and ~40 call records with clinic transcripts.
"""
from sqlalchemy import select, delete
from app.db.database import AsyncSessionLocal
from app.models.models import (
    Tenant, User, Agent, BehaviorConfig, Campaign, Call,
    WhatsAppConversation, WhatsAppMessage,
    Clinic, Doctor, Service, Patient, Appointment, InsuranceProvider,
    Niche, UserRole, AgentType, AgentStatus, CallDirection, CallOutcome, CampaignStatus,
    AppointmentStatus,
)
from datetime import datetime, timedelta, date
import random
import uuid
import bcrypt


def safe_hash(password: str) -> str:
    """Hash a password with bcrypt, guarding the 72-byte limit."""
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


# Tenant 1 — the original Prime Health clinic migrated into the multi-tenant model.
# The Twilio number is the routing key (inbound calls to it load this tenant's config).
TENANT_ID = "tenant-001"
TENANT_PHONE = "+16575347796"
TENANT_GREETING = (
    "Thank you for calling Prime Health Clinic. This is the AI assistant, how may I help you?"
)

CLINIC_ID = "clinic-001"

NAMES = [
    "John Smith", "Maria Santos", "Omar Hassan", "Emily Chen", "David Johnson",
    "Aisha Khan", "Carlos Rivera", "Sophie Martin", "Liam O'Brien", "Fatima Ali",
    "Noah Williams", "Yuki Tanaka", "Grace Park", "Mohammed Saleh", "Olivia Brown",
    "Lucas Silva", "Hana Kim", "James Wilson", "Layla Ahmed", "Ethan Davis",
    "Priya Patel", "Daniel Lee", "Nadia Farah", "Mateo Gomez", "Chloe Taylor",
    "Ali Mansour", "Rita Khoury", "Samir Haddad", "Lara Aoun", "Tarek Nasser",
]

# (name, specialty, available_days)
DOCTORS = [
    ("Dr. Sarah Haddad", "General Practitioner", ["mon", "tue", "wed", "thu", "fri"]),
    ("Dr. Karim Nassar", "Dentist", ["mon", "wed", "fri", "sat"]),
    ("Dr. Lina Aoun", "Dermatologist", ["tue", "thu", "sat"]),
    ("Dr. Omar Khalil", "Pediatrician", ["mon", "tue", "wed", "thu", "fri", "sat"]),
    ("Dr. Maya Fares", "Cardiologist", ["mon", "wed", "thu"]),
]

# (name, duration_minutes, price_cents, description)
SERVICES = [
    ("General Consultation", 30, 5000, "Standard check-up with a general practitioner."),
    ("Dental Cleaning", 45, 8000, "Professional teeth cleaning and oral exam."),
    ("Dental Filling", 60, 12000, "Cavity treatment and tooth filling."),
    ("Skin Consultation", 30, 7000, "Dermatology assessment for skin conditions."),
    ("Pediatric Check-up", 30, 4500, "Routine health check for children."),
    ("Cardiac Screening", 60, 15000, "ECG and cardiovascular risk assessment."),
    ("Vaccination", 15, 3000, "Routine and travel vaccinations."),
    ("Blood Test Panel", 20, 6000, "Comprehensive blood work and lab analysis."),
]

INSURANCE = [
    ("Bupa", True, "Direct billing accepted."),
    ("MedNet", True, "Pre-approval required for procedures over $200."),
    ("Allianz Care", True, "Direct billing accepted."),
    ("AXA", True, "Co-payment may apply."),
    ("GlobeMed", True, "Direct billing accepted."),
    ("Cigna", True, "Reimbursement claims supported."),
    ("Nextcare", False, "Not currently in network — patient pays out of pocket."),
]

CLINIC_HOURS = {
    "mon": "9:00 AM - 6:00 PM", "tue": "9:00 AM - 6:00 PM", "wed": "9:00 AM - 6:00 PM",
    "thu": "9:00 AM - 6:00 PM", "fri": "9:00 AM - 6:00 PM", "sat": "9:00 AM - 6:00 PM",
    "sun": "Closed",
}

CLINIC_SYSTEM_PROMPT = (
    "You are a clinic receptionist AI for Prime Health Clinic. You may ONLY state information "
    "provided to you in the function results. NEVER invent appointment times, prices, doctor "
    "names, or policies. If you don't have the data, offer to connect to staff. Keep responses "
    "under 2 sentences. Be warm and professional."
)


def _uuid32():
    return str(uuid.uuid4()).replace("-", "")


def _phone():
    return f"+1415555{random.randint(1000, 9999)}"


async def seed_mock_data():
    async with AsyncSessionLocal() as db:
        # Guard on appointments, NOT users: an earlier/partial deploy (or the old
        # restaurant-era schema) can leave a stale User row that made the old
        # `if User exists: return` guard skip seeding forever, leaving clinic data
        # empty. If there are real appointments, the demo data is present — skip.
        if (await db.execute(select(Appointment))).scalars().first():
            print("[seed] Data already present (appointments exist) — skipping")
            return

        print("[seed] No appointments found — seeding fresh clinic data...")
        # Clear any stale/partial seed rows first so the fixed-ID inserts below
        # (usr-admin-001, agt-001, clinic-001, …) can't collide with leftovers.
        # Safe: we only reach here when zero appointments exist, so nothing real is lost.
        await _clear_seed_tables(db)

        _seed_tenant(db)
        await db.flush()  # tenant must exist before tenant-scoped rows reference it
        _seed_core(db)
        _seed_clinic(db)
        await db.flush()  # ensure clinic/doctors/services/patients exist before appointments
        patient_ids = _seed_patients(db)
        await db.flush()
        _seed_appointments(db, patient_ids)
        _seed_calls(db)
        _seed_whatsapp(db)

        await db.commit()
        print("[seed] Prime Health Clinic demo seeded "
              "(5 doctors · 8 services · 60 patients · 100 appointments · 6 insurers)")


async def _clear_seed_tables(db):
    """Delete existing rows from every table the seed writes, in FK-safe order
    (children before parents). Idempotent and only invoked when no appointments
    exist, so it never destroys live data."""
    for model in (
        Appointment, WhatsAppMessage, WhatsAppConversation, Call, Campaign,
        Patient, Service, Doctor, InsuranceProvider, Clinic,
        Agent, BehaviorConfig, User, Tenant,
    ):
        await db.execute(delete(model))
    await db.flush()


def _seed_tenant(db):
    """Tenant 1 — the original Prime Health clinic as a tenant. Its Twilio number is the
    routing key, and its knowledge base mirrors the clinic's hours/services/insurance so
    the agent has a tenant-scoped FAQ source from day one."""
    db.add(Tenant(
        id=TENANT_ID,
        business_name="Prime Health Clinic",
        niche=Niche.clinic,
        twilio_phone_number=TENANT_PHONE,
        default_language="en",
        supported_languages=["en", "ar", "fr", "es"],
        timezone="Asia/Beirut",
        greeting_message=TENANT_GREETING,
        knowledge_base={
            "hours": CLINIC_HOURS,
            "location": "Hamra Street, Building 12, Beirut, Lebanon",
            "phone": TENANT_PHONE,
            "services": [{"name": n, "price": f"${p / 100:.2f}", "duration_minutes": d}
                         for n, d, p, _ in SERVICES],
            "insurance_accepted": [n for n, accepted, _ in INSURANCE if accepted],
            "policies": "Please arrive 10 minutes early. Cancellations require 24h notice.",
        },
        config={"booking_window_days": 30, "default_appointment_minutes": 30},
    ))


def _seed_core(db):
    db.add(User(id="usr-admin-001", tenant_id=TENANT_ID, role=UserRole.owner,
                name="Ibrahim Admin",
                email="admin@primetechai.com", password_hash=safe_hash("demo1234")))

    inbound_config = BehaviorConfig(
        id="cfg-inbound-001",
        tenant_id=TENANT_ID,
        name="Prime Health Clinic — Receptionist (Inbound)",
        version=1,
        system_prompt=CLINIC_SYSTEM_PROMPT,
        hard_rules=[
            {"rule": "Only state information returned by clinic functions", "enabled": True},
            {"rule": "Never invent appointment times, prices, doctor names, or policies", "enabled": True},
            {"rule": "Always collect patient name and phone before booking", "enabled": True},
            {"rule": "Offer to connect to staff when data is missing", "enabled": True},
        ],
        soft_rules=[
            {"rule": "Use the patient's name when known", "enabled": True},
            {"rule": "Confirm date and time back to the caller", "enabled": True},
        ],
        blocked_topics=["medical diagnosis", "prescription advice", "treatment recommendations"],
        escalation_triggers=["emergency", "wants to speak to a human", "complaint", "billing dispute"],
        data_extraction_fields=["patient_name", "phone", "doctor", "date", "time", "reason", "insurance_provider"],
        max_call_duration=300,
        versions=[],
    )
    db.add(inbound_config)

    db.add_all([
        Agent(id="agt-001", tenant_id=TENANT_ID, name="Clinic Receptionist (Inbound)",
              type=AgentType.inbound,
              language="en", voice_id="shimmer", status=AgentStatus.active,
              behavior_config_id="cfg-inbound-001", phone_number="+16575347796",
              calls_today=12, total_calls=412, avg_score=91.2),
        Agent(id="agt-002", tenant_id=TENANT_ID, name="Clinic WhatsApp Assistant",
              type=AgentType.whatsapp,
              language="en", voice_id="nova", status=AgentStatus.active,
              behavior_config_id="cfg-inbound-001",
              calls_today=19, total_calls=688, avg_score=90.4),
    ])

    db.add(Campaign(id="cmp-001", tenant_id=TENANT_ID, name="Appointment Reminder Calls",
                    agent_id="agt-001",
                    status=CampaignStatus.active, total_contacts=80, called_count=52,
                    connected_count=41, voicemail_count=8, failed_count=3,
                    calls_per_hour=12, retry_attempts=2, contacts=[]))


def _seed_clinic(db):
    db.add(Clinic(
        id=CLINIC_ID, tenant_id=TENANT_ID, name="Prime Health Clinic",
        address="Hamra Street, Building 12, Beirut, Lebanon",
        phone="+16575347796", hours=CLINIC_HOURS, timezone="Asia/Beirut",
    ))
    for i, (name, specialty, days) in enumerate(DOCTORS):
        db.add(Doctor(id=f"doc-{i+1:03d}", tenant_id=TENANT_ID, clinic_id=CLINIC_ID,
                      name=name, specialty=specialty,
                      available_days=days, available_hours={"start": "09:00", "end": "17:00"}))
    for i, (name, dur, price, desc) in enumerate(SERVICES):
        db.add(Service(id=f"svc-{i+1:03d}", tenant_id=TENANT_ID, clinic_id=CLINIC_ID, name=name,
                       duration_minutes=dur, price=price, description=desc))
    for i, (name, accepted, notes) in enumerate(INSURANCE):
        db.add(InsuranceProvider(id=f"ins-{i+1:03d}", tenant_id=TENANT_ID, clinic_id=CLINIC_ID,
                                 name=name, accepted=accepted, notes=notes))


def _seed_patients(db):
    ids = []
    used = set()
    for i in range(60):
        pid = f"pat-{i+1:03d}"
        phone = _phone()
        while phone in used:
            phone = _phone()
        used.add(phone)
        name = random.choice(NAMES)
        db.add(Patient(
            id=pid, tenant_id=TENANT_ID, clinic_id=CLINIC_ID, name=name, phone=phone,
            email=f"{name.split()[0].lower()}{random.randint(1, 999)}@example.com",
            date_of_birth=date(random.randint(1955, 2018),
                               random.randint(1, 12), random.randint(1, 28)).isoformat(),
            insurance_provider=random.choice([n for n, _, _ in INSURANCE] + [None, None]),
            notes=random.choice([None, None, "Prefers morning appointments", "Allergic to penicillin"]),
        ))
        ids.append(pid)
    return ids


def _seed_appointments(db, patient_ids):
    doctor_ids = [f"doc-{i+1:03d}" for i in range(len(DOCTORS))]
    service_ids = [f"svc-{i+1:03d}" for i in range(len(SERVICES))]
    reasons = ["Routine check-up", "Follow-up visit", "Tooth pain", "Skin rash",
               "Child vaccination", "Chest discomfort", "Blood test", "Annual physical"]
    for i in range(100):
        upcoming = i < 55
        if upcoming:
            d = date.today() + timedelta(days=random.randint(0, 30))
            status = random.choice([AppointmentStatus.booked, AppointmentStatus.booked,
                                    AppointmentStatus.confirmed])
        else:
            d = date.today() - timedelta(days=random.randint(1, 60))
            status = random.choice([AppointmentStatus.completed, AppointmentStatus.completed,
                                    AppointmentStatus.no_show, AppointmentStatus.cancelled])
        hour = random.choice([9, 10, 11, 12, 14, 15, 16, 17])
        minute = random.choice([0, 0, 15, 30])
        db.add(Appointment(
            id=f"apt-{i+1:03d}", tenant_id=TENANT_ID, clinic_id=CLINIC_ID,
            patient_id=random.choice(patient_ids),
            doctor_id=random.choice(doctor_ids),
            service_id=random.choice(service_ids),
            date=d.isoformat(), time=f"{hour:02d}:{minute:02d}",
            status=status, reason=random.choice(reasons),
            created_via=random.choice(["voice", "voice", "whatsapp", "manual"]),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 45)),
        ))


def _call_templates():
    return [
        ("book",
         "Assistant: Thank you for calling Prime Health Clinic. This is the AI assistant, how may I help you?\n"
         "Caller: I'd like to book an appointment with the dentist this Friday at 10am.\n"
         "Assistant: Of course. May I have your name and phone number?\n"
         "Caller: Omar Hassan, 415-555-0142.\n"
         "Assistant: You're booked with Dr. Karim Nassar this Friday at 10am. See you then, Omar!",
         {"patient_name": "Omar Hassan", "phone": "+14155550142", "doctor": "Dentist", "intent": "book_appointment"},
         CallOutcome.resolved, (88, 97)),
        ("hours",
         "Assistant: Thank you for calling Prime Health Clinic. This is the AI assistant, how may I help you?\n"
         "Caller: What are your opening hours?\n"
         "Assistant: We're open Monday to Saturday, 9am to 6pm, and closed on Sundays.\n"
         "Caller: Great, thanks!\n"
         "Assistant: Happy to help — have a great day!",
         {"intent": "clinic_hours"},
         CallOutcome.resolved, (90, 98)),
        ("insurance",
         "Assistant: Thank you for calling Prime Health Clinic, how may I help you?\n"
         "Caller: Do you accept Bupa insurance?\n"
         "Assistant: Yes, we accept Bupa with direct billing. Is there anything else?\n"
         "Caller: No that's all, thank you.\n"
         "Assistant: Thank you for calling, have a great day!",
         {"insurance_provider": "Bupa", "intent": "insurance_question"},
         CallOutcome.resolved, (89, 97)),
        ("reschedule",
         "Assistant: Thank you for calling Prime Health Clinic, how may I help you?\n"
         "Caller: I need to move my appointment to next Tuesday at 3pm. My number is 415-555-0188.\n"
         "Assistant: Done — I've moved your appointment to next Tuesday at 3pm.\n"
         "Caller: Perfect, thanks.\n"
         "Assistant: You're welcome, see you then!",
         {"phone": "+14155550188", "intent": "reschedule_appointment"},
         CallOutcome.resolved, (85, 95)),
        ("escalate",
         "Assistant: Thank you for calling Prime Health Clinic, how may I help you?\n"
         "Caller: I think I'm having chest pains right now.\n"
         "Assistant: This may be an emergency. Let me connect you to our staff right away — if it's severe, please call emergency services.",
         {"intent": "speak_to_human", "issue_type": "emergency", "escalated": True},
         CallOutcome.escalated, (60, 75)),
    ]


def _seed_calls(db):
    templates = _call_templates()
    langs = ["en", "en", "en", "ar", "fr", "es"]
    for i in range(40):
        started = datetime.utcnow() - timedelta(days=random.randint(0, 30),
                                                hours=random.randint(0, 23),
                                                minutes=random.randint(0, 59))
        if random.random() < 0.12:
            outcome = random.choice([CallOutcome.no_answer, CallOutcome.voicemail, CallOutcome.abandoned])
            duration = random.randint(5, 35)
            db.add(Call(
                tenant_id=TENANT_ID, agent_id="agt-001", direction=CallDirection.inbound,
                twilio_call_sid=f"CA{_uuid32()}",
                caller_number=_phone(), called_number="+16575347796",
                language="en", duration_seconds=duration, outcome=outcome,
                started_at=started, ended_at=started + timedelta(seconds=duration),
            ))
            continue

        scenario, transcript, extracted, outcome, score_range = random.choice(templates)
        duration = random.randint(40, 280)
        score = round(random.uniform(*score_range), 1)
        sentiment = "negative" if outcome == CallOutcome.escalated else random.choice(["positive", "positive", "neutral"])
        timeline = ([0.2, 0.1, -0.5, -0.6] if outcome == CallOutcome.escalated
                    else [round(random.uniform(0.2, 0.5), 2)] + [round(random.uniform(0.5, 0.95), 2) for _ in range(3)])
        db.add(Call(
            tenant_id=TENANT_ID, agent_id="agt-001", direction=CallDirection.inbound,
            twilio_call_sid=f"CA{_uuid32()}",
            caller_number=extracted.get("phone", _phone()), called_number="+16575347796",
            language=random.choice(langs),
            duration_seconds=duration, outcome=outcome, ai_score=score,
            transcript=transcript,
            extracted_data=extracted,
            rule_violations=([] if outcome != CallOutcome.escalated
                             else ["Escalated to human — clinical/emergency out of scope"]),
            sentiment_data={"overall": sentiment, "timeline": timeline},
            ai_analysis={
                "score": score,
                "summary": f"{scenario.capitalize()} call — {outcome.value}.",
                "greeting": random.randint(85, 100),
                "professionalism": random.randint(85, 100),
                "resolution": random.randint(70, 100) if outcome != CallOutcome.escalated else random.randint(40, 65),
                "recommendations": random.choice([
                    ["Confirmed details clearly", "Warm close"],
                    ["Correctly escalated emergency", "Stayed within scope"],
                    ["No hallucination — stuck to real data"],
                ]),
            },
            started_at=started, ended_at=started + timedelta(seconds=duration),
        ))


def _seed_whatsapp(db):
    conv = WhatsAppConversation(
        id="wa-001", tenant_id=TENANT_ID, agent_id="agt-002",
        contact_number="+14155550188", contact_name="Maria Santos",
        status="active", message_count=6,
        last_message="You're all set for Tuesday at 3pm with Dr. Sarah Haddad. See you then!",
        last_message_at=datetime.utcnow() - timedelta(hours=2),
    )
    db.add(conv)
    for role, content in [
        ("customer", "Hi, can I book a check-up this week?"),
        ("agent", "Hi Maria! I can help. Dr. Sarah Haddad has openings Tuesday. What time works, and may I confirm your phone number?"),
        ("customer", "Tuesday 3pm, my number is 415-555-0188"),
        ("agent", "You're all set for Tuesday at 3pm with Dr. Sarah Haddad. See you then!"),
        ("customer", "Thank you!"),
        ("agent", "You're welcome — take care!"),
    ]:
        db.add(WhatsAppMessage(conversation_id="wa-001", role=role, content=content))
