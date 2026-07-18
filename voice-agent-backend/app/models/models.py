from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid
import enum

def gen_uuid(): return str(uuid.uuid4())


class Niche(str, enum.Enum):
    """Vertical a tenant operates in. Drives niche-specific config/behavior later;
    for now all niches share the existing appointment functions."""
    clinic = "clinic"
    dental = "dental"
    real_estate = "real_estate"
    restaurant = "restaurant"
    spa = "spa"


class UserRole(str, enum.Enum):
    """Dashboard role of a staff member within their tenant."""
    owner = "owner"
    manager = "manager"
    staff = "staff"


class AgentType(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"
    whatsapp = "whatsapp"
    track = "track"

class AgentStatus(str, enum.Enum):
    active = "active"
    idle = "idle"
    offline = "offline"

class CallDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"

class CallOutcome(str, enum.Enum):
    resolved = "resolved"
    escalated = "escalated"
    voicemail = "voicemail"
    no_answer = "no_answer"
    abandoned = "abandoned"
    in_progress = "in_progress"


class ReminderOutcome(str, enum.Enum):
    """How an outbound appointment-reminder call turned out. Stored on the Appointment
    so we never lose the result; 'no_answer'/'voicemail' are the cases the WhatsApp
    fallback (next step) will pick up."""
    calling = "calling"          # call placed, not yet resolved
    answered = "answered"        # a human answered but took no confirm/reschedule/cancel action
    confirmed = "confirmed"
    rescheduled = "rescheduled"
    cancelled = "cancelled"
    no_answer = "no_answer"
    voicemail = "voicemail"
    failed = "failed"            # Twilio could not place/complete the call

class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"

class Tenant(Base):
    """A single business served by the platform. The inbound Twilio number is the
    routing key: an incoming call's destination number is matched to exactly one
    tenant, whose config + data scope the whole call. Every domain table carries a
    tenant_id so no business can ever see another's data."""
    __tablename__ = "tenants"
    id = Column(String, primary_key=True, default=gen_uuid)
    business_name = Column(String, nullable=False)
    niche = Column(SAEnum(Niche), nullable=False, default=Niche.clinic)
    # The dialed Twilio number that routes inbound calls to this tenant. Unique — it is
    # the single source of truth for phone -> tenant resolution.
    twilio_phone_number = Column(String, unique=True, nullable=True)
    default_language = Column(String, default="en")          # en / ar
    supported_languages = Column(JSON, default=lambda: ["en"])
    timezone = Column(String, default="Asia/Beirut")
    # First line the agent speaks on an inbound call for this tenant.
    greeting_message = Column(Text, nullable=True)
    # Greeting spoken when the clinic is CLOSED (outside hours / holiday / temp closure).
    # Surfaced in load_tenant_config; NULL keeps the existing single-greeting behavior.
    closed_greeting = Column(Text, nullable=True)
    # FAQ knowledge the agent may state: hours, services, pricing, locations, policies.
    # Free-form JSON so each niche can shape it without a schema change.
    knowledge_base = Column(JSON, default=dict)
    # Niche-specific settings / business rules (booking windows, deposit policy, etc.).
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    # Staff member of a tenant (owner/manager/staff) for the dashboard. Nullable so a
    # platform-level superuser can exist without a tenant.
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.owner)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    # Human-readable job title shown in the PrimeOps Users screen (e.g. "Support Lead",
    # "Onboarding"). Independent of the auth `role`. Operators have tenant_id = NULL.
    title = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class BehaviorConfig(Base):
    __tablename__ = "behavior_configs"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String, nullable=False)
    version = Column(Integer, default=1)
    system_prompt = Column(Text)
    hard_rules = Column(JSON, default=list)
    soft_rules = Column(JSON, default=list)
    blocked_topics = Column(JSON, default=list)
    escalation_triggers = Column(JSON, default=list)
    data_extraction_fields = Column(JSON, default=list)
    max_call_duration = Column(Integer, default=300)
    versions = Column(JSON, default=list)  # version history snapshots
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(SAEnum(AgentType), nullable=False)
    language = Column(String, default="en")
    voice_id = Column(String, default="alloy")
    status = Column(SAEnum(AgentStatus), default=AgentStatus.idle)
    behavior_config_id = Column(String, ForeignKey("behavior_configs.id"), nullable=True)
    phone_number = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)
    calls_today = Column(Integer, default=0)
    total_calls = Column(Integer, default=0)
    avg_score = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    behavior_config = relationship("BehaviorConfig", foreign_keys=[behavior_config_id])

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String, nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"))
    status = Column(SAEnum(CampaignStatus), default=CampaignStatus.draft)
    total_contacts = Column(Integer, default=0)
    called_count = Column(Integer, default=0)
    connected_count = Column(Integer, default=0)
    voicemail_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    calls_per_hour = Column(Integer, default=10)
    retry_attempts = Column(Integer, default=2)
    contacts = Column(JSON, default=list)
    script = Column(Text, nullable=True)
    scheduled_start = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    agent = relationship("Agent", foreign_keys=[agent_id])

class Call(Base):
    __tablename__ = "calls"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)
    # Set for outbound reminder calls so a placed call can be tied back to the
    # appointment it is reminding about (used to resolve the agent's context when it
    # joins the room, and to record the outcome).
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=True)
    purpose = Column(String, nullable=True)  # e.g. "reminder" for outbound reminder calls
    twilio_call_sid = Column(String, nullable=True, unique=True)
    livekit_room = Column(String, nullable=True)
    direction = Column(SAEnum(CallDirection))
    caller_number = Column(String)
    called_number = Column(String, nullable=True)
    language = Column(String, default="en")  # detected caller language (en/ar/fr/es)
    duration_seconds = Column(Integer, nullable=True)
    outcome = Column(SAEnum(CallOutcome), default=CallOutcome.in_progress)
    ai_score = Column(Float, nullable=True)
    transcript = Column(Text, nullable=True)
    recording_url = Column(String, nullable=True)
    extracted_data = Column(JSON, default=dict)
    rule_violations = Column(JSON, default=list)
    sentiment_data = Column(JSON, default=dict)
    ai_analysis = Column(JSON, default=dict)
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    agent = relationship("Agent", foreign_keys=[agent_id])
    campaign = relationship("Campaign", foreign_keys=[campaign_id])

class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    agent_id = Column(String, ForeignKey("agents.id"))
    contact_number = Column(String, nullable=False)
    contact_name = Column(String, nullable=True)
    status = Column(String, default="active")
    message_count = Column(Integer, default=0)
    last_message = Column(Text, nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"
    id = Column(String, primary_key=True, default=gen_uuid)
    conversation_id = Column(String, ForeignKey("whatsapp_conversations.id"))
    role = Column(String)
    content = Column(Text)
    sent_at = Column(DateTime, server_default=func.now())


# ── Prime Health Clinic domain ───────────────────────────────────────────
# The voice agent is a medical-clinic receptionist. Every value the agent
# speaks about appointments, doctors, services, hours, and insurance comes
# from these tables — the LLM is forbidden from inventing any of it.

class AppointmentStatus(str, enum.Enum):
    booked = "booked"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class Clinic(Base):
    __tablename__ = "clinics"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    hours = Column(JSON, default=dict)          # {"mon": "9:00 AM - 6:00 PM", ...}
    timezone = Column(String, default="Asia/Beirut")
    created_at = Column(DateTime, server_default=func.now())


class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    available_days = Column(JSON, default=list)     # ["mon","tue",...]
    available_hours = Column(JSON, default=dict)    # {"start": "09:00", "end": "17:00"}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    clinic = relationship("Clinic", foreign_keys=[clinic_id])


class Service(Base):
    __tablename__ = "services"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    name = Column(String, nullable=False)
    duration_minutes = Column(Integer, default=30)
    price = Column(Integer, default=0)              # cents
    description = Column(Text, nullable=True)
    # Merchant-dashboard extras (additive). `category` groups services; `details` holds the
    # rich fields the merchant app shows (about / prep / after / pricing tiers, EN+AR).
    # The voice agent only reads name/price/duration, so these never affect it.
    category = Column(String, nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    clinic = relationship("Clinic", foreign_keys=[clinic_id])


class Patient(Base):
    __tablename__ = "patients"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)   # YYYY-MM-DD
    insurance_provider = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    clinic = relationship("Clinic", foreign_keys=[clinic_id])


class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True)
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=True)
    service_id = Column(String, ForeignKey("services.id"), nullable=True)
    date = Column(String, nullable=False)           # YYYY-MM-DD
    time = Column(String, nullable=False)           # HH:MM (24h)
    status = Column(SAEnum(AppointmentStatus), default=AppointmentStatus.booked)
    reason = Column(Text, nullable=True)
    created_via = Column(String, default="voice")   # voice / whatsapp / manual
    # Outbound reminder tracking. `reminder_sent_at` is set the moment a reminder call
    # is placed (it also guards against the scheduler calling the same appointment
    # twice); `reminder_outcome` records the result (ReminderOutcome values).
    reminder_sent_at = Column(DateTime, nullable=True)
    reminder_outcome = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    patient = relationship("Patient", foreign_keys=[patient_id])
    doctor = relationship("Doctor", foreign_keys=[doctor_id])
    service = relationship("Service", foreign_keys=[service_id])


class InsuranceProvider(Base):
    __tablename__ = "insurance_providers"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    name = Column(String, nullable=False)
    accepted = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    clinic = relationship("Clinic", foreign_keys=[clinic_id])


# ── Restaurant domain (niche = restaurant) ────────────────────────────────
# Reservations + menu-aware pickup orders. The agent reads the tenant's real
# MenuItem rows to take an order — it may NEVER invent a dish or a price (the same
# anti-hallucination guarantee the clinic appointment flow gives).
#
# NOTE on table names: an earlier build of this codebase left ORPHAN tables named
# `reservations` and `orders` (old restaurant schema) on persistent deploys. To avoid
# create_all(checkfirst=True) silently skipping a name-colliding stale table, these new
# tables use distinct names (restaurant_*). The orphans are dropped on boot
# (database.drop_orphan_tables).

class ReservationStatus(str, enum.Enum):
    booked = "booked"
    confirmed = "confirmed"
    cancelled = "cancelled"
    seated = "seated"
    completed = "completed"
    no_show = "no_show"


class OrderStatus(str, enum.Enum):
    received = "received"
    preparing = "preparing"
    ready = "ready"
    done = "done"
    cancelled = "cancelled"


class Reservation(Base):
    __tablename__ = "restaurant_reservations"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    party_size = Column(Integer, default=2)
    date = Column(String, nullable=False)           # YYYY-MM-DD
    time = Column(String, nullable=False)           # HH:MM (24h)
    notes = Column(Text, nullable=True)
    status = Column(SAEnum(ReservationStatus), default=ReservationStatus.booked)
    created_via = Column(String, default="voice")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, default=0)              # cents
    category = Column(String, nullable=True)        # e.g. "Coffee", "Mains", "Desserts"
    available = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Order(Base):
    __tablename__ = "restaurant_orders"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    pickup_time = Column(String, nullable=True)      # HH:MM (24h) or "ASAP"
    status = Column(SAEnum(OrderStatus), default=OrderStatus.received)
    total = Column(Integer, default=0)               # cents — sum of line items
    notes = Column(Text, nullable=True)
    created_via = Column(String, default="voice")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    items = relationship("OrderItem", back_populates="order",
                         cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "restaurant_order_items"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    order_id = Column(String, ForeignKey("restaurant_orders.id"), nullable=False)
    menu_item_id = Column(String, ForeignKey("menu_items.id"), nullable=True)
    name = Column(String, nullable=False)            # snapshot of the item name at order time
    quantity = Column(Integer, default=1)
    unit_price = Column(Integer, default=0)          # cents (snapshot)
    line_total = Column(Integer, default=0)          # cents (unit_price * quantity)
    order = relationship("Order", back_populates="items")


# ── Lead capture domain (niche = real_estate / automotive / services) ─────────
# A single flexible table covers all three verticals: the `lead_type` + `budget` +
# `requirements` shape describes a property interest, a vehicle interest, or a service
# request equally well. The agent collects these conversationally and saves immediately.

class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    closed = "closed"


class Lead(Base):
    __tablename__ = "leads"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    # Optional email — used by the website "Book a demo" lead form.
    email = Column(String, nullable=True)
    # What the caller is interested in: property type (real estate), vehicle interest
    # (automotive), or service needed (services). One column serves all three.
    lead_type = Column(String, nullable=True)
    budget = Column(String, nullable=True)          # free-form ("$300k", "around 50k", "flexible")
    requirements = Column(Text, nullable=True)      # extra detail / notes
    status = Column(SAEnum(LeadStatus), default=LeadStatus.new)
    created_via = Column(String, default="voice")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ── AtlasPrimeX dashboard/console domain (additive; agent never reads these) ──────
# Holiday special-hours (tenant-scoped, surfaced to the agent via load_tenant_config),
# plus operator-only Alerts and Tickets for the PrimeOps console.

class Holiday(Base):
    """Per-tenant holiday/special-hours entry, managed from the merchant Settings screen.
    Surfaced in load_tenant_config so the agent can honor closed-all-day / special hours."""
    __tablename__ = "holidays"
    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String, nullable=False)
    date = Column(String, nullable=True)            # free-form label or YYYY-MM-DD
    closed = Column(Boolean, default=True)          # closed all day
    hours = Column(String, nullable=True)           # special hours when not closed
    created_at = Column(DateTime, server_default=func.now())


class OpsAlert(Base):
    """Operator-facing system/health alert shown in the PrimeOps console. References a
    tenant (merchant) by id; not tenant-scoped for access (operators see the fleet)."""
    __tablename__ = "ops_alerts"
    id = Column(String, primary_key=True, default=gen_uuid)
    severity = Column(String, default="info")       # critical | warning | info
    title = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    merchant_name = Column(String, nullable=True)   # denormalized for display
    body = Column(Text, nullable=True)
    status = Column(String, default="active")       # active | dismissed
    created_at = Column(DateTime, server_default=func.now())


class OpsTicket(Base):
    """Operator-facing support ticket shown in the PrimeOps console."""
    __tablename__ = "ops_tickets"
    id = Column(String, primary_key=True, default=gen_uuid)
    code = Column(String, nullable=True)            # e.g. "T-1042"
    subject = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    merchant_name = Column(String, nullable=True)
    status = Column(String, default="open")         # open | in_progress | resolved
    priority = Column(String, default="medium")     # high | medium | low
    assignee = Column(String, nullable=True)        # internal agent name or "—"
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
