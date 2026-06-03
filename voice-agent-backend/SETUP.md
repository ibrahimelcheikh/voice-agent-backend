# Voice Agent Backend — Setup Guide

## Quick Start

### 1. Install dependencies
```
pip install -r requirements.txt
```

### 2. Start the server
```
uvicorn app.main:app --host 0.0.0.0 --port 8030 --reload
```

### 3. Open API docs
http://localhost:8030/docs

### 4. Demo login
POST http://localhost:8030/auth/demo-login
Returns token automatically

---

## Database Migrations (Alembic)

Tables are created automatically on first startup and data is seeded once.
Use Alembic to evolve the schema safely **after changing models** — it never
drops your data.

```
# Run migrations (apply latest schema)
alembic upgrade head

# After changing models in app/models/models.py
alembic revision --autogenerate -m "describe_your_change"
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

`alembic check` reports whether the models have drifted from the DB.

### Reset to fresh demo data
Normally data **persists across restarts**. To deliberately wipe and reseed a
clean demo database:

1. Set `RESET_DB=true` in `.env`
2. Restart the server once (drops all tables, recreates, reseeds)
3. Set `RESET_DB=false` in `.env`
4. Restart again — fresh demo data now persists

---

## Phone Calls via LiveKit SIP (Twilio → LiveKit → Agent)

Architecture: **Twilio number → LiveKit SIP trunk → LiveKit room → Aria agent joins**.

These are one-time, account-level steps (cannot be done from app code alone):

1. **Env vars** — ensure `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`,
   `TWILIO_PHONE_NUMBER`, and `PUBLIC_URL` are set (locally in `.env`, on Railway
   in the Variables tab).

2. **Create the SIP trunk + dispatch rule** (run once):
   ```
   python scripts/setup_livekit_sip.py
   ```
   It prints the LiveKit SIP host and the URLs to use below.

3. **Set the LiveKit webhook** — LiveKit Dashboard → Settings → Webhooks → add:
   ```
   https://voice-agent-backend-production-fa4e.up.railway.app/livekit/webhook
   ```
   This is what triggers the agent to join each call.

4. **Point Twilio at LiveKit** — two options:
   - **A (no change to Twilio number):** keep the Voice webhook on
     `{PUBLIC_URL}/twilio/inbound`. It now returns `<Dial><Sip>` TwiML that dials
     the call into LiveKit's SIP host.
   - **B (Elastic SIP Trunk):** in Twilio, create an Origination URI
     `sip:<project>.sip.livekit.cloud;transport=tcp` and attach the number.

5. **Call the number.** Flow: Twilio → LiveKit SIP → `call-*` room → Aria joins
   with VAD, barge-in, natural turns, and the booking/order/FAQ tools.

> Verify the exact SIP host in LiveKit Dashboard → Settings → SIP — the app
> derives `<project>.sip.livekit.cloud` from `LIVEKIT_URL`, which is correct for
> standard LiveKit Cloud projects.

---

## Legacy: Twilio Media Streams (ngrok)

### Step 1: Start ngrok in a NEW terminal
```
ngrok http 8030
```
Copy the https URL e.g. https://abc123.ngrok.io

### Step 2: Update .env
```
NGROK_URL=https://abc123.ngrok.io
```

### Step 3: Set Twilio webhook
1. Go to https://console.twilio.com
2. Phone Numbers → Manage → Active Numbers
3. Click your number +16575347796
4. Voice Configuration → A call comes in
5. Set webhook URL to: https://abc123.ngrok.io/twilio/inbound
6. Set HTTP method to: POST
7. Save

### Step 4: Call your number!
Call +16575347796 and the AI agent will answer.

---

## Demo Credentials
- Email: admin@primetechai.com  
- Password: demo1234

## API Endpoints
- GET  /agents/           — list agents
- GET  /calls/            — call history
- GET  /calls/stats       — dashboard stats
- GET  /behavior/         — behavior configs
- GET  /campaigns/        — campaigns
- GET  /whatsapp/conversations — WhatsApp chats
- POST /calls/make        — make outbound call
- POST /twilio/inbound    — Twilio webhook (inbound)
- POST /whatsapp/webhook  — Twilio WhatsApp webhook
