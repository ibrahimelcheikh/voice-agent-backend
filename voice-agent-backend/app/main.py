import sys

# Ensure emoji/unicode console output (✅ ⚠️) doesn't crash on Windows cp1252.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import (
    auth, agents, calls, behavior, campaigns, whatsapp, twilio_webhooks,
    appointments, patients, clinic_info, demo, livekit_webhooks,
)
from app.db.database import engine, Base, reset_schema
from app.db.seed import seed_mock_data
from app.core.config import settings
import app.models.models  # noqa: F401  (ensure all models are registered on Base)

app = FastAPI(
    title="Prime Tech AI — Clinic Voice Agent API",
    description="""
    Prime Health Clinic AI receptionist — Twilio (SIP) → LiveKit → Pipecat pipeline.

    ## Features
    - **Inbound Calls**: Twilio + LiveKit + Pipecat voice agent (Silero VAD, barge-in)
    - **Anti-Hallucination Guardrail**: intent → real DB function → strict LLM formatting
    - **Multi-language**: English, Arabic, French, Spanish
    - **Behavior Lock Files**: versioned, exportable/importable agent behavior configs
    - **Call Analytics**: transcripts, scoring, sentiment timelines, AI analysis
    - **Appointments / Patients / Clinic Info**: the real data the agent speaks from
    - **Demo Simulator**: run full AI conversations without a phone (`POST /demo/simulate-call`)

    ## Demo Credentials
    - Email: admin@primetechai.com
    - Password: demo1234
    """,
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    # Create tables only if they don't already exist — never drop. Data persists
    # across restarts; seed runs once on the first-ever boot (see seed guard).
    # Set RESET_DB=true in .env to deliberately wipe and reseed a fresh demo DB.
    # FORCE_SEED behaves like RESET_DB — a one-shot full wipe + reseed. Set it on
    # Railway for a single deploy to rebuild an empty/stale DB, then unset it. The wipe
    # drops the whole schema (clears orphan tables from the old restaurant schema that
    # a model-only drop_all can't remove); the normal path only creates missing tables.
    if settings.RESET_DB or settings.FORCE_SEED:
        await reset_schema()
        print(f"DB reset — public schema dropped + recreated (RESET_DB={settings.RESET_DB} FORCE_SEED={settings.FORCE_SEED})")
    else:
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))
    print("Checking if seed needed...")
    await seed_mock_data()
    print("Seed check complete")
    await configure_twilio_webhook()

    # Generate prerecorded greeting/goodbye/thinking clips (once) for fast call start.
    try:
        from app.agents.audio import ensure_audio_files
        await ensure_audio_files()
    except Exception as e:
        print(f"⚠️ Could not prepare audio clips: {e}")

    # NOTE: This web service does NOT spawn voice agents. The dedicated worker
    # process (`python -m app.agents.agent_worker`, a separate Railway service) is
    # the ONLY thing that joins call rooms — exactly one agent per call.

    print("=" * 60)
    print("  Prime Tech AI — Voice Agent API is READY")
    print("  Docs:   http://localhost:8030/docs")
    print("  Health: http://localhost:8030/health")
    print("  Demo login: admin@primetechai.com / demo1234")
    print("=" * 60)


async def configure_twilio_webhook():
    """Point the Twilio number's voice webhook + status callback at PUBLIC_URL."""
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        phone_numbers = client.incoming_phone_numbers.list()
        for number in phone_numbers:
            if number.phone_number == settings.TWILIO_PHONE_NUMBER:
                number.update(
                    voice_url=f"{settings.PUBLIC_URL}/twilio/inbound",
                    voice_method="POST",
                    status_callback=f"{settings.PUBLIC_URL}/twilio/status",
                    status_callback_method="POST",
                )
                print(f"✅ Twilio webhook set to: {settings.PUBLIC_URL}/twilio/inbound")
                break
    except Exception as e:
        print(f"⚠️ Could not auto-configure Twilio: {e}")


# Routes
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(calls.router, prefix="/calls", tags=["Calls"])
app.include_router(behavior.router, prefix="/behavior", tags=["Behavior Config"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
app.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp"])
app.include_router(twilio_webhooks.router, prefix="/twilio", tags=["Twilio Webhooks"])
app.include_router(livekit_webhooks.router, prefix="/livekit", tags=["LiveKit Webhooks"])
app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
app.include_router(patients.router, prefix="/patients", tags=["Patients"])
app.include_router(clinic_info.router, prefix="/clinic", tags=["Clinic Info"])
app.include_router(demo.router, prefix="/demo", tags=["Demo"])


@app.get("/")
async def root():
    return {
        "service": "Prime Tech AI — Voice Agent",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "voice-agent"}


@app.get("/ngrok-setup")
async def ngrok_setup():
    return {
        "current_ngrok_url": settings.NGROK_URL or None,
        "instructions": "Run ngrok in a separate terminal: ngrok http 8030",
        "then": "Restart the server — it auto-detects the tunnel and updates the Twilio webhook",
        "twilio_dashboard": "https://console.twilio.com/us1/develop/phone-numbers/manage/incoming",
    }
