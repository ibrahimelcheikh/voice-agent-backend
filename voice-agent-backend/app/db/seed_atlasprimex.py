"""
AtlasPrimeX demo seed — additive & idempotent.

Creates the fleet the PrimeOps console + merchant app show:
  * one operator login (PrimeOps, tenant_id = NULL, sees all tenants)
  * six merchant tenants matching the design (Divinia, Lumière, Downtown Dental, Nova,
    Cedar, Pearl) with display config (city/type/plan/status/mrr/health)
  * a merchant login scoped to Divinia
  * Divinia fully populated: branch + hours + greetings, inbound agent + system prompt,
    six services (rich details), patients, appointments, calls with transcripts
  * operator alerts + tickets

Runs after the existing clinic seed and NEVER touches it. Skips cleanly if already seeded
(guarded by the operator user's email). Idempotent: safe to run on every boot.
"""
from datetime import datetime, timedelta

import bcrypt
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.models import (
    Tenant, User, UserRole, Agent, AgentType, AgentStatus, BehaviorConfig,
    Clinic, Service, Patient, Appointment, AppointmentStatus, Call, CallDirection,
    CallOutcome, Holiday, OpsAlert, OpsTicket, Niche,
)

OPERATOR_EMAIL = "operator@atlasprimex.ai"
MERCHANT_EMAIL = "merchant@atlasprimex.ai"
DEMO_PW = "demo1234"

DIVINIA_ID = "apx-divinia"


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


_FLEET = [
    # id, name, city, type, plan, status, mrr, health, langs, phone
    ("apx-divinia", "Divinia Clinic", "Riyadh", "Med Spa", "Premium", "live", 250, 98, ["ar", "en"], "+966500000001"),
    ("apx-lumiere", "Lumière Aesthetics", "Jeddah", "Clinic", "Pro", "live", 200, 95, ["ar", "en"], "+966500000002"),
    ("apx-downtown", "Downtown Dental", "Dubai", "Dental", "Pro", "live", 200, 91, ["ar", "en"], "+971500000003"),
    ("apx-nova", "Nova Skin Bar", "Riyadh", "Med Spa", "Starter", "onboarding", 150, 0, ["ar"], "+966500000004"),
    ("apx-cedar", "Cedar Wellness", "Doha", "Clinic", "Pro", "live", 200, 87, ["ar", "en"], "+974500000005"),
    ("apx-pearl", "Pearl Derma", "Kuwait City", "Dermatology", "Starter", "paused", 150, 40, ["ar"], "+965500000006"),
]

_SERVICES = [
    ("botox", "Botox", "بوتوكس", "Injectables", 900, 30,
     {"ar": "بوتوكس", "about": {"en": "A quick, precise injectable that relaxes targeted muscles to soften lines.", "ar": "حقن دقيق وسريع يرخي العضلات المستهدفة لتنعيم الخطوط."},
      "tiers": [{"en": "1 area", "ar": "منطقة واحدة", "price": 900}, {"en": "2 areas", "ar": "منطقتان", "price": 1600}, {"en": "3 areas", "ar": "٣ مناطق", "price": 2200}],
      "prep": {"en": "Avoid blood thinners and alcohol 24h before.", "ar": "تجنّب مميّعات الدم والكحول قبل ٢٤ ساعة."},
      "after": {"en": "Stay upright 4 hours, skip strenuous exercise for 24h.", "ar": "ابقَ منتصباً ٤ ساعات، تجنّب التمارين الشاقة ٢٤ ساعة."}}),
    ("filler", "Dermal Fillers", "الفيلر الجلدي", "Injectables", 1600, 45,
     {"ar": "الفيلر الجلدي", "about": {"en": "Hyaluronic-acid fillers restore volume and contour. Results last 9–12 months.", "ar": "فيلر حمض الهيالورونيك يعيد الحجم والتحديد. تدوم من ٩ إلى ١٢ شهراً."},
      "tiers": [{"en": "Lip", "ar": "الشفاه", "price": 1600}, {"en": "Cheek", "ar": "الخدود", "price": 2100}, {"en": "Jawline", "ar": "خط الفك", "price": 2600}],
      "prep": {"en": "Avoid blood thinners 24h before.", "ar": "تجنّب مميّعات الدم قبل ٢٤ ساعة."},
      "after": {"en": "Mild swelling is normal for 48h.", "ar": "التورّم الخفيف طبيعي لمدة ٤٨ ساعة."}}),
    ("hydra", "HydraFacial", "هيدرافيشل", "Facials", 650, 50,
     {"ar": "هيدرافيشل", "about": {"en": "A multi-step facial that cleanses, exfoliates, and hydrates. Instant glow.", "ar": "علاج متعدّد الخطوات ينظّف ويقشّر ويرطّب البشرة. نضارة فورية."},
      "tiers": [{"en": "Signature", "ar": "الأساسي", "price": 650}, {"en": "Deluxe", "ar": "المطوّر", "price": 900}, {"en": "Platinum", "ar": "البلاتيني", "price": 1200}],
      "prep": {"en": "Skip retinol and exfoliants 48h before.", "ar": "تجنّب الريتينول والمقشّرات قبل ٤٨ ساعة."},
      "after": {"en": "Use SPF, avoid direct sun for 24h.", "ar": "استخدم واقي الشمس وتجنّب الشمس المباشرة ٢٤ ساعة."}}),
    ("laser", "Laser Hair Removal", "إزالة الشعر بالليزر", "Laser", 400, 40,
     {"ar": "إزالة الشعر بالليزر", "about": {"en": "Diode laser targets hair follicles. 6–8 sessions give the best results.", "ar": "ليزر الدايود يستهدف بصيلات الشعر. جلسات من ٦ إلى ٨ تعطي أفضل النتائج."},
      "tiers": [{"en": "Small area", "ar": "منطقة صغيرة", "price": 400}, {"en": "Medium area", "ar": "منطقة متوسطة", "price": 700}, {"en": "Full body", "ar": "الجسم كامل", "price": 1500}],
      "prep": {"en": "Shave the area 24h before.", "ar": "احلق المنطقة قبل ٢٤ ساعة."},
      "after": {"en": "Avoid sun and hot showers for 48h.", "ar": "تجنّب الشمس والاستحمام الساخن ٤٨ ساعة."}}),
    ("prp", "PRP Hair Treatment", "علاج الشعر بالبلازما", "Restorative", 1200, 60,
     {"ar": "علاج الشعر بالبلازما", "about": {"en": "Platelet-rich plasma injected into the scalp to stimulate hair growth.", "ar": "البلازما الغنية بالصفائح تُحقن في فروة الرأس لتحفيز نمو الشعر."},
      "tiers": [{"en": "Single session", "ar": "جلسة واحدة", "price": 1200}, {"en": "Package of 3", "ar": "باقة ٣ جلسات", "price": 3200}],
      "prep": {"en": "Hydrate and eat before your visit.", "ar": "اشرب الماء وتناول الطعام قبل الزيارة."},
      "after": {"en": "Don't wash hair for 6 hours.", "ar": "لا تغسل الشعر ٦ ساعات."}}),
    ("consult", "Skin Consultation", "استشارة جلدية", "Consultation", 200, 20,
     {"ar": "استشارة جلدية", "about": {"en": "A one-on-one assessment with a female dermatologist.", "ar": "تقييم فردي مع طبيبة جلدية."},
      "tiers": [{"en": "Standard", "ar": "عادية", "price": 200}, {"en": "With skin analysis", "ar": "مع تحليل البشرة", "price": 350}],
      "prep": {"en": "Come with a clean face.", "ar": "احضري بوجه نظيف."},
      "after": {"en": "You'll receive a written plan by SMS.", "ar": "ستصلك خطة مكتوبة عبر SMS."}}),
]

_CONVOS = [
    ("Nour A.", "+966 55 214 8890", "ar", CallOutcome.resolved, 72,
     "Caller asked to book Botox for next Tuesday. Agent offered morning or evening, confirmed 6:00 PM, sent an SMS confirmation and set a 24-hour reminder.", True),
    ("+966 50 771 3320", "+966 50 771 3320", "ar", CallOutcome.resolved, 58,
     "Caller asked how long dermal filler lasts and whether a female doctor is available. Agent answered 9–12 months and confirmed a female doctor.", False),
    ("Sara K.", "+966 53 118 6642", "en", CallOutcome.resolved, 123,
     "English caller asked laser hair removal pricing and prep. Agent quoted 400 SAR/session and booked a session for Sunday.", True),
    ("+966 59 440 1187", "+966 59 440 1187", "ar", CallOutcome.escalated, 104,
     "Caller reported swelling after fillers and asked what to avoid. Agent flagged it urgent and transferred to the on-call clinician.", False),
]

_ALERTS = [
    ("critical", "Voice agent not registering", "Pearl Derma", "LiveKit worker for Pearl Derma stopped responding to health checks."),
    ("warning", "Cal.com sync delayed", "Cedar Wellness", "Booking sync latency above 30s. Calendar writes are queuing."),
    ("warning", "High after-hours volume", "Downtown Dental", "3x normal after-hours calls. Consider reviewing closed-hours greeting."),
    ("info", "Urgent call escalated", "Divinia Clinic", "Filler-swelling call transferred to on-call clinician. Resolved."),
]

_TICKETS = [
    ("T-1042", "Add Arabic voice to my number", "Nova Skin Bar", "open", "high", "—"),
    ("T-1041", "Wrong price quoted for laser", "Downtown Dental", "in_progress", "high", "Layla"),
    ("T-1039", "Reminder SMS not sending", "Cedar Wellness", "in_progress", "medium", "Sami"),
    ("T-1035", "Request: WhatsApp channel", "Lumière Aesthetics", "open", "medium", "—"),
    ("T-1030", "Update clinic hours for Eid", "Divinia Clinic", "resolved", "low", "Layla"),
]

_HOURS = {d: "1:00 PM → 9:00 PM" for d in ["sat", "sun", "mon", "tue", "wed", "thu"]}
_HOURS["fri"] = "Closed"

# Divinia FAQ knowledge base — the ONLY source faq_lookup may answer non-service questions
# from (keyword-matched by the agent). Service prices are also answered from the Service rows
# via the services_offered intent; this KB covers everything else the agent must handle.
_DIVINIA_KB = {
    "hours": "We're open Saturday to Thursday, 1:00 PM to 9:00 PM. We are closed on Fridays.",
    "location": "Divinia Clinic — Olaya, on Olaya Street, Riyadh 12211.",
    "booking": ("You can book right now by phone — just tell me the service, the day, and the "
                "time, and I'll confirm it and send an SMS confirmation."),
    "rescheduling and cancellation": ("To reschedule or cancel an existing appointment, tell me "
                                      "your name and I'll update or cancel your booking."),
    "botox price": "Botox starts from 900 SAR per area (two areas 1,600 SAR, three areas 2,200 SAR).",
    "filler duration": "Dermal fillers typically last 9 to 12 months.",
    "female doctors": "Yes — female doctors are available on request; just let us know when booking.",
    "laser preparation": ("For laser hair removal, shave the area 24 hours before your session, "
                          "and avoid sun exposure or tanning for two weeks beforehand."),
    "aftercare": ("After a treatment, avoid heat, direct sun, and strenuous exercise for 24 to 48 hours."),
    "payment": "We accept cash, mada, and major cards. Prices are in Saudi riyals (SAR).",
}


async def seed_atlasprimex_demo():
    async with AsyncSessionLocal() as db:
        exists = (await db.execute(select(User).where(User.email == OPERATOR_EMAIL))).scalars().first()
        if exists:
            return  # already seeded

        # Operator (PrimeOps) — platform user, no tenant.
        db.add(User(id="apx-operator", tenant_id=None, role=UserRole.owner, title="Owner",
                    name="Ibrahim El Cheikh", email=OPERATOR_EMAIL, password_hash=_hash(DEMO_PW), is_active=True))
        # A couple more internal team members for the Users screen.
        db.add(User(tenant_id=None, role=UserRole.owner, title="Support Lead", name="Layla Haddad",
                    email="layla@atlasprimex.ai", password_hash=_hash(DEMO_PW), is_active=True))
        db.add(User(tenant_id=None, role=UserRole.owner, title="Onboarding", name="Sami Nasr",
                    email="sami@atlasprimex.ai", password_hash=_hash(DEMO_PW), is_active=True))

        # Fleet tenants.
        for tid, name, city, typ, plan, status, mrr, health, langs, phone in _FLEET:
            db.add(Tenant(
                id=tid, business_name=name, niche=Niche.clinic, twilio_phone_number=phone,
                default_language=("ar" if "ar" in langs else "en"), supported_languages=langs,
                timezone="Asia/Riyadh", is_active=(status != "paused"),
                greeting_message=f"Hello, welcome to {name}. How may I help you today?",
                closed_greeting=(f"Thanks for calling {name}. We're currently closed, but I can "
                                 "schedule an appointment and we'll follow up during clinic hours."),
                knowledge_base=(_DIVINIA_KB if tid == DIVINIA_ID else {}),
                config={"city": city, "type": typ, "plan": plan, "status": status,
                        "mrr": mrr, "health": health, "currency": "SAR"},
            ))

        # Merchant login scoped to Divinia.
        db.add(User(id="apx-merchant", tenant_id=DIVINIA_ID, role=UserRole.owner, name="Divinia Manager",
                    email=MERCHANT_EMAIL, password_hash=_hash(DEMO_PW), is_active=True))

        # Divinia branch + agent + prompt.
        db.add(Clinic(id="apx-divinia-branch", tenant_id=DIVINIA_ID, name="Divinia Clinic — Olaya",
                      address="Olaya St, Riyadh 12211, KSA", phone="+966 11 234 5678",
                      hours=_HOURS, timezone="Asia/Riyadh"))
        bc = BehaviorConfig(id="apx-divinia-bc", tenant_id=DIVINIA_ID, name="Divinia prompt", version=1,
                            system_prompt=("You are the AI receptionist for Divinia Clinic, a med spa in "
                                           "Riyadh. Greet warmly and answer only from the clinic's real "
                                           "services, prices, and hours. Never invent prices or medical "
                                           "advice. Offer to book and send an SMS confirmation."))
        db.add(bc)
        db.add(Agent(id="apx-divinia-agent", tenant_id=DIVINIA_ID, name="Reem", type=AgentType.inbound,
                     language="ar", voice_id="reem", status=AgentStatus.active,
                     behavior_config_id="apx-divinia-bc", is_active=True))

        # Divinia services.
        for sid, en, ar, cat, price, dur, details in _SERVICES:
            db.add(Service(id=f"apx-svc-{sid}", tenant_id=DIVINIA_ID, clinic_id="apx-divinia-branch",
                           name=en, category=cat, price=price, duration_minutes=dur,
                           description=details["about"]["en"], details=details))

        # A holiday for Divinia (Settings ▸ Holiday Hours).
        db.add(Holiday(tenant_id=DIVINIA_ID, name="Saudi National Day", date="Sep 23, 2026", closed=True, hours=None))
        db.add(Holiday(tenant_id=DIVINIA_ID, name="Eid al-Fitr", date="Mar 20, 2026", closed=False, hours="4:00 PM → 9:00 PM"))

        # Patients + appointments + calls for Divinia.
        now = datetime.utcnow()
        appt_specs = [("Nour A.", "apx-svc-botox", 2, "18:00"), ("Sara K.", "apx-svc-laser", 1, "15:30"),
                      ("Layla M.", "apx-svc-hydra", 0, "17:00"), ("Huda R.", "apx-svc-consult", 3, "14:00")]
        for i, (pname, svc, day_off, tm) in enumerate(appt_specs):
            pid = f"apx-patient-{i}"
            db.add(Patient(id=pid, tenant_id=DIVINIA_ID, clinic_id="apx-divinia-branch",
                           name=pname, phone=f"+96650000{i:04d}"))
            d = (now + timedelta(days=day_off)).strftime("%Y-%m-%d")
            db.add(Appointment(tenant_id=DIVINIA_ID, clinic_id="apx-divinia-branch", patient_id=pid,
                               service_id=svc, date=d, time=tm, status=AppointmentStatus.booked,
                               created_via="voice"))

        for i, (name, phone, lang, outcome, dur, summary, booked) in enumerate(_CONVOS):
            db.add(Call(tenant_id=DIVINIA_ID, direction=CallDirection.inbound, caller_number=phone,
                        language=lang, duration_seconds=dur, outcome=outcome, transcript=summary,
                        appointment_id=None if not booked else None,
                        sentiment_data={"label": "concerned" if outcome == CallOutcome.escalated else "positive"},
                        started_at=now - timedelta(hours=i + 1)))

        # Operator alerts + tickets.
        name_to_tid = {n: tid for tid, n, *_ in _FLEET}
        for sev, title, merchant, body in _ALERTS:
            db.add(OpsAlert(severity=sev, title=title, merchant_name=merchant,
                            tenant_id=name_to_tid.get(merchant), body=body, status="active"))
        for code, subject, merchant, status, pri, assignee in _TICKETS:
            db.add(OpsTicket(code=code, subject=subject, merchant_name=merchant,
                             tenant_id=name_to_tid.get(merchant), status=status, priority=pri, assignee=assignee))

        await db.commit()
        print("[seed] AtlasPrimeX demo fleet seeded (operator + 6 tenants + Divinia data + alerts/tickets)")


async def apply_call_number_switch(db, target: str, number: str) -> str:
    """Point `number` at a demo tenant. Idempotent, additive, non-destructive: it only frees
    the number from its current holder (sets that field NULL) and assigns it to the target.
    `divinia` also fills Divinia's FAQ KB + SAR currency if missing. Does NOT commit — the
    caller commits. Returns a human-readable status string. Shared by the boot hook and the
    scripts/switch_call_number.py CLI so both behave identically."""
    number = (number or "").strip()
    if target not in ("divinia", "restaurant") or not number:
        return f"no-op (target={target!r}, number={number!r})"
    holders = (await db.execute(
        select(Tenant).where(Tenant.twilio_phone_number == number))).scalars().all()

    if target == "divinia":
        div = await db.get(Tenant, DIVINIA_ID)
        if not div:
            return f"Divinia tenant '{DIVINIA_ID}' not found — is the DB seeded?"
        for t in holders:
            if t.id != DIVINIA_ID:
                t.twilio_phone_number = None
        await db.flush()   # release the number before reassigning (UNIQUE column)
        div.twilio_phone_number = number
        if not (div.knowledge_base or {}):
            div.knowledge_base = _DIVINIA_KB
        cfg = dict(div.config or {})
        if cfg.get("currency") != "SAR":
            cfg["currency"] = "SAR"
            div.config = cfg
        return f"{number} -> Divinia Clinic ({DIVINIA_ID})"

    # target == "restaurant": hand the number back to the live restaurant tenant.
    rows = (await db.execute(select(Tenant).where(Tenant.niche == Niche.restaurant))).scalars().all()
    rest = rows[0] if len(rows) == 1 else None
    if not rest:
        return ("restaurant tenant ambiguous/missing — use scripts/switch_call_number.py with "
                "RESTAURANT_TENANT_ID set")
    for t in holders:
        if t.id != rest.id:
            t.twilio_phone_number = None
    await db.flush()   # release the number before reassigning (UNIQUE column)
    rest.twilio_phone_number = number
    return f"{number} -> {rest.business_name} ({rest.id})"


async def run_boot_demo_switch():
    """Startup hook: apply settings.ACTIVE_DEMO_TENANT to DEMO_CALLABLE_NUMBER. No-op (and
    never raises into boot) when ACTIVE_DEMO_TENANT is blank."""
    from app.core.config import settings
    target = (settings.ACTIVE_DEMO_TENANT or "").strip().lower()
    if not target:
        return
    async with AsyncSessionLocal() as db:
        status = await apply_call_number_switch(db, target, settings.DEMO_CALLABLE_NUMBER)
        await db.commit()
        print(f"[boot-switch] ACTIVE_DEMO_TENANT={target}: {status}")
