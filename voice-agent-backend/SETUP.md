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

## Connect Real Phone Calls (Twilio + ngrok)

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
