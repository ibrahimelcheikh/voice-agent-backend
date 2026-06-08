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
    DEEPGRAM_TTS_MODEL: str = "aura-asteria-en"
    CARTESIA_TTS_MODEL: str = "sonic-2"
    CARTESIA_VOICE: str = ""  # optional Cartesia voice id; blank = plugin default
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
