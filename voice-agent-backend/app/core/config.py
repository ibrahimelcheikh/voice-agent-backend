from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:resto99pass@127.0.0.1/voice_agent"
    JWT_SECRET: str = "primetech_voice_agent_secret_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    OPENAI_API_KEY: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    # Agent dispatch name. The LiveKit SIP dispatch rule routes inbound `call-*` rooms to a
    # named agent ("clinic-agent"); the worker MUST register with this same name (explicit
    # dispatch) or it is never offered the job. Set to "" to use AUTOMATIC dispatch instead
    # (worker registers with no name and is offered every room) — only do that if the
    # dispatch rule has NO explicit agent configured.
    AGENT_NAME: str = "clinic-agent"
    # DETERMINISTIC INBOUND ROUTING: when a dialed number matches NO tenant, the agent
    # ends the call rather than silently answering as the default clinic (answering as the
    # wrong business is worse than not answering). Set True ONLY to restore the old
    # single-tenant behavior where any unmatched call falls back to the default tenant.
    ALLOW_DEFAULT_TENANT_FALLBACK: bool = False
    DEEPGRAM_API_KEY: str = ""
    CARTESIA_API_KEY: str = ""
    # Voice pipeline tuning (low latency). TTS_PROVIDER: deepgram | cartesia | openai.
    # Deepgram aura is lowest-latency but ENGLISH-ONLY; use cartesia for multilingual.
    TTS_PROVIDER: str = "deepgram"
    DEEPGRAM_STT_MODEL: str = "nova-2-general"
    # Arabic STT (Phase 3b) — Deepgram with a monolingual Arabic language code (NOT multi). Nova-3
    # has a dedicated, production-grade Arabic model (17 dialect variants incl. Lebanese, streaming-
    # supported); Nova-3 'multi' EXCLUDES Arabic, so a monolingual code on nova-3 is the correct path.
    # ("nova-3" and "nova-3-general" are the same model.)
    DEEPGRAM_AR_STT_MODEL: str = "nova-3"
    # Phase 3b polish — Lebanese dialect. ar-LB is Nova-3's Lebanese (Levantine) variant; far more
    # accurate on Lebanese phone Arabic than bare "ar". Fall back to "ar" if ar-LB underperforms.
    DEEPGRAM_AR_LANGUAGE: str = "ar-LB"
    # Phase 3b polish — Nova-3 Keyterm Prompting: boost the menu's Arabic item names (comma-separated)
    # so the STT recognises them. Supported across all Arabic dialects incl. ar-LB (NOT with multi).
    # STATIC default = Beirut Bites demo list; a tenant can override via its config 'ar_keyterms'.
    # NOTE: the DB stores menu names in ENGLISH, so Arabic keyterms can't be auto-derived from it —
    # per-tenant Arabic keyterms must be supplied in tenant config (or extend this default).
    DEEPGRAM_AR_KEYTERMS: str = "فلافل,حمص,شاورما دجاج,شاورما لحمة,عصير ليمون,كابتشينو,لاتيه,برغر"
    # Phase 3b polish — Arabic turn-taking. Wider than English so brief mid-utterance pauses don't
    # cut the caller off (the right trade for ordering: a little latency vs. not getting interrupted).
    # endpointing_ms = Deepgram silence before end-of-speech; the delays bound the agent's turn commit.
    # Bumped (1000->1200 / 1.3->1.6s) so a pause between an order intro ("I'd like to order…") and
    # the items ("…one falafel and one hummus") stays ONE turn instead of splitting. The conversational
    # awaiting-items handling (guardrail) is the real safety net if it still splits.
    DEEPGRAM_AR_ENDPOINTING_MS: int = 1200
    AR_MIN_ENDPOINTING_DELAY: float = 1.6
    AR_MAX_ENDPOINTING_DELAY: float = 5.0
    DEEPGRAM_TTS_MODEL: str = "aura-asteria-en"
    CARTESIA_TTS_MODEL: str = "sonic-2"
    CARTESIA_VOICE: str = ""  # optional Cartesia voice id; blank = plugin default
    # Arabic (MSA) TTS — used ONLY for calls whose selected language is "ar" (Phase 3b).
    # sonic-2 does NOT support Arabic; Arabic needs sonic-3/sonic-3.5. A valid Arabic voice id
    # MUST be supplied (Cartesia requires a voice id and we never guess one) — until
    # CARTESIA_AR_VOICE is set, Arabic callers safely fall back to the English path.
    CARTESIA_AR_MODEL: str = "sonic-3.5"
    CARTESIA_AR_VOICE: str = ""  # REQUIRED for Arabic TTS; blank = Arabic falls back to English
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8030
    DEBUG: bool = True
    NGROK_URL: str = ""
    PUBLIC_URL: str = "https://voice-agent-backend-production-fa4e.up.railway.app"  # public base for Twilio webhooks + media stream
    RESET_DB: bool = False  # set true to drop+reseed a fresh demo DB on next boot
    # IMPORTANT: keep FALSE. Reminders write state (reminder_sent_at / reminder_outcome)
    # we must not lose, so the DB must persist across restarts. Only flip to true for a
    # single deliberate one-shot wipe+reseed, then set it back to false.
    FORCE_SEED: bool = False  # set true to wipe + reseed once (e.g. on Railway); same effect as RESET_DB

    # ── Outbound appointment reminders ──────────────────────────────────────
    # How many hours before an appointment the reminder call goes out.
    REMINDER_HOURS_BEFORE: int = 24
    # Background sweep that auto-places due reminder calls.
    REMINDER_SCHEDULER_ENABLED: bool = True
    REMINDER_INTERVAL_MINUTES: int = 15   # how often the sweep runs
    # Twilio Answering Machine Detection — lets us mark a call voicemail vs human.
    REMINDER_MACHINE_DETECTION: bool = True

    @property
    def async_database_url(self) -> str:
        """Normalize the DB URL to the asyncpg driver (Railway/Heroku hand out
        plain postgresql:// or postgres:// URLs that SQLAlchemy's async engine
        can't use directly)."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
