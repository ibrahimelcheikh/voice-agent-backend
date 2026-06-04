from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid
import enum

def gen_uuid(): return str(uuid.uuid4())

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

class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class BehaviorConfig(Base):
    __tablename__ = "behavior_configs"
    id = Column(String, primary_key=True, default=gen_uuid)
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
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True)
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
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    hours = Column(JSON, default=dict)          # {"mon": "9:00 AM - 6:00 PM", ...}
    timezone = Column(String, default="Asia/Beirut")
    created_at = Column(DateTime, server_default=func.now())


class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(String, primary_key=True, default=gen_uuid)
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
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    name = Column(String, nullable=False)
    duration_minutes = Column(Integer, default=30)
    price = Column(Integer, default=0)              # cents
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    clinic = relationship("Clinic", foreign_keys=[clinic_id])


class Patient(Base):
    __tablename__ = "patients"
    id = Column(String, primary_key=True, default=gen_uuid)
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
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True)
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=True)
    service_id = Column(String, ForeignKey("services.id"), nullable=True)
    date = Column(String, nullable=False)           # YYYY-MM-DD
    time = Column(String, nullable=False)           # HH:MM (24h)
    status = Column(SAEnum(AppointmentStatus), default=AppointmentStatus.booked)
    reason = Column(Text, nullable=True)
    created_via = Column(String, default="voice")   # voice / whatsapp / manual
    created_at = Column(DateTime, server_default=func.now())
    patient = relationship("Patient", foreign_keys=[patient_id])
    doctor = relationship("Doctor", foreign_keys=[doctor_id])
    service = relationship("Service", foreign_keys=[service_id])


class InsuranceProvider(Base):
    __tablename__ = "insurance_providers"
    id = Column(String, primary_key=True, default=gen_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)
    name = Column(String, nullable=False)
    accepted = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    clinic = relationship("Clinic", foreign_keys=[clinic_id])
