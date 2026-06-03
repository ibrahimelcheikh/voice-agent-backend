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
    reservations, orders, faq, demo, livekit_webhooks,
)
from app.db.database import engine, Base
from app.db.seed import seed_mock_data
from app.core.config import settings
import app.models.models  # noqa: F401  (ensure all models are registered on Base)

app = FastAPI(
    title="Prime Tech AI — Voice Agent API",
    description="""
    Atlas PrimeX Voice Agent Platform — "Aria" AI receptionist for the Golden Fork restaurant chain.

    ## Features
    - **Inbound / Outbound Calls**: Twilio + Pipecat + LiveKit voice agent with real action tools
    - **Outbound Campaigns**: rate-limited AI calling campaigns
    - **WhatsApp Agent**: contextual AI WhatsApp replies via Twilio
    - **Behavior Lock Files**: versioned, exportable/importable agent behavior configs
    - **Call Analytics**: transcripts, scoring, sentiment timelines, AI analysis
    - **Reservations / Orders / FAQ**: restaurant operations powered by the agent's tools
    - **Demo Simulator**: run full AI conversations without a phone (`POST /demo/simulate-call`)

    ## Demo Credentials
    - Email: admin@primetechai.com
    - Password: demo1234
    """,
    version="2.0.0",
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
    async with engine.begin() as conn:
        if settings.RESET_DB:
            await conn.run_sync(Base.metadata.drop_all)
            print("DB reset — all tables dropped (RESET_DB=true)")
        await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))
    await seed_mock_data()
    await configure_twilio_webhook()

    # Fallback to the LiveKit webhook: poll for new SIP call rooms and join an
    # agent. Needs LiveKit creds; skip if running the dedicated agent_worker.
    if settings.ENABLE_ROOM_WATCHER and settings.LIVEKIT_API_KEY:
        import asyncio
        asyncio.create_task(agent_room_watcher())
        print("[watcher] room watcher started")

    print("=" * 60)
    print("  Prime Tech AI — Voice Agent API is READY")
    print("  Docs:   http://localhost:8030/docs")
    print("  Health: http://localhost:8030/health")
    print("  Demo login: admin@primetechai.com / demo1234")
    print("=" * 60)


async def agent_room_watcher():
    """Poll LiveKit every 2s for new `call-*` rooms with a caller present, and
    spawn the Aria agent into them. Webhook-independent fallback so calls connect
    even if the LiveKit webhook isn't configured. run_agent_in_room is idempotent
    per room, so this is safe alongside the webhook."""
    import asyncio
    from livekit import api as lkapi
    from app.agents.pipecat_agent import run_agent_in_room

    handled_rooms: set[str] = set()
    lk = lkapi.LiveKitAPI(
        url=settings.LIVEKIT_URL.replace("wss://", "https://"),
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        while True:
            try:
                rooms = await lk.room.list_rooms(lkapi.ListRoomsRequest())
                for room in rooms.rooms:
                    if (room.name.startswith("call-")
                            and room.name not in handled_rooms
                            and room.num_participants > 0):
                        handled_rooms.add(room.name)
                        print(f"[watcher] new call room {room.name} — spawning agent")
                        asyncio.create_task(run_agent_in_room(room.name, {}))
            except Exception as e:
                print(f"[watcher] error: {type(e).__name__}: {e}")
            await asyncio.sleep(2)
    finally:
        await lk.aclose()


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
app.include_router(reservations.router, prefix="/reservations", tags=["Reservations"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(faq.router, prefix="/faq", tags=["FAQ"])
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
