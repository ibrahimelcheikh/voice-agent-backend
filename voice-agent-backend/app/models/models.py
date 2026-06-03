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
    max_call_duration = Column(Integer, default=480)
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


# ── Golden Fork demo domain ──────────────────────────────────────────────

class ReservationStatus(str, enum.Enum):
    confirmed = "confirmed"
    pending = "pending"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class OrderType(str, enum.Enum):
    delivery = "delivery"
    pickup = "pickup"
    dine_in = "dine_in"


class OrderStatus(str, enum.Enum):
    received = "received"
    preparing = "preparing"
    ready = "ready"
    delivered = "delivered"
    cancelled = "cancelled"


class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(String, primary_key=True, default=gen_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    party_size = Column(Integer, default=2)
    date = Column(String, nullable=False)          # ISO date YYYY-MM-DD
    time = Column(String, nullable=False)           # HH:MM
    location = Column(String, default="Downtown")
    status = Column(SAEnum(ReservationStatus), default=ReservationStatus.pending)
    notes = Column(Text, nullable=True)
    created_via = Column(String, default="voice")   # voice / whatsapp / manual
    created_at = Column(DateTime, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, default=gen_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    order_type = Column(SAEnum(OrderType), default=OrderType.pickup)
    items = Column(JSON, default=list)              # [{name, qty, price}]
    total = Column(Integer, default=0)              # cents
    status = Column(SAEnum(OrderStatus), default=OrderStatus.received)
    address = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_via = Column(String, default="voice")
    created_at = Column(DateTime, server_default=func.now())


class FAQ(Base):
    __tablename__ = "faqs"
    id = Column(String, primary_key=True, default=gen_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String, default="general")
    times_asked = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
