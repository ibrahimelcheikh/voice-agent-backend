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
    FORCE_SEED: bool = False  # set true to wipe + reseed once (e.g. on Railway); same effect as RESET_DB

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
