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
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8030
    DEBUG: bool = True
    NGROK_URL: str = ""
    PUBLIC_URL: str = "https://stiffen-caterer-lying.ngrok-free.dev"  # public base for Twilio webhooks + media stream
    RESET_DB: bool = False  # set true to drop+reseed a fresh demo DB on next boot

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
