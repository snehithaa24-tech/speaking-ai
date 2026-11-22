from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List

_CORE_DIR = Path(__file__).resolve().parent
_APP_DIR = _CORE_DIR.parent
_BACKEND_DIR = _APP_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SAHAYAK AI"
    APP_VERSION: str = "1.0.0"
    APP_DEBUG: bool = Field(default=False, alias="APP_DEBUG")
    ENVIRONMENT: str = Field(default="development", alias="ENVIRONMENT")

    @property
    def DEBUG(self) -> bool:
        """Backward compatibility property for code using settings.DEBUG"""
        return self.APP_DEBUG

    # Server
    HOST: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    PORT: int = Field(default=8000, alias="BACKEND_PORT")
    WORKERS: int = Field(default=1, alias="BACKEND_WORKERS")

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./sahayak.db", alias="DATABASE_URL")

    # Security
    SECRET_KEY: str = Field(alias="SECRET_KEY", repr=False)
    JWT_ALGORITHM: str = Field(default="HS256", alias="JWT_ALGORITHM")
    JWT_EXPIRE_MINUTES: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")

    # Google Gemini
    GEMINI_API_KEY: str = Field(alias="GEMINI_API_KEY", repr=False)
    GEMINI_LIVE_MODEL: str = Field(default="gemini-2.0-flash", alias="GEMINI_LIVE_MODEL")

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_api_key(cls, v: str) -> str:
        placeholder_values = {"test_key_for_development", "your_api_key_here", "placeholder", ""}
        if v in placeholder_values or v.startswith("test_key") or v.startswith("placeholder"):
            import os
            env = os.getenv("ENVIRONMENT", "development")
            if env == "production":
                raise ValueError(
                    "GEMINI_API_KEY is not configured for production. Please set a valid API key from https://aistudio.google.com/apikey"
                )
            import logging
            logging.getLogger(__name__).warning(
                "GEMINI_API_KEY is using a placeholder. Live voice streaming will require a valid API key from https://aistudio.google.com/apikey"
            )
        return v

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_SECRET", repr=False)

    # Supabase Configuration
    SUPABASE_URL: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, alias="SUPABASE_PUBLISHABLE_KEY")
    SUPABASE_SECRET_KEY: Optional[str] = Field(default=None, alias="SUPABASE_SECRET_KEY", repr=False)

    # Frontend URL & CORS
    FRONTEND_URL: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    CORS_ORIGINS: Optional[str] = Field(default=None, alias="CORS_ORIGINS")

    @property
    def allowed_cors_origins(self) -> List[str]:
        origins = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
        if self.FRONTEND_URL:
            clean_url = self.FRONTEND_URL.strip().rstrip("/")
            if clean_url:
                origins.add(clean_url)
                if "localhost" in clean_url:
                    origins.add(clean_url.replace("localhost", "127.0.0.1"))
                elif "127.0.0.1" in clean_url:
                    origins.add(clean_url.replace("127.0.0.1", "localhost"))
        if self.CORS_ORIGINS:
            for item in self.CORS_ORIGINS.split(","):
                clean = item.strip().rstrip("/")
                if clean:
                    origins.add(clean)
        import os
        vercel_url = os.getenv("VERCEL_URL")
        if vercel_url:
            clean_v = vercel_url.strip().rstrip("/")
            origins.add(f"https://{clean_v}")
            origins.add(f"http://{clean_v}")
        return sorted(list(origins))

    # Logging
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")

    # Feature Flags
    ENABLE_OAUTH: bool = Field(default=False, alias="ENABLE_OAUTH")
    ENABLE_ADMIN_PANEL: bool = Field(default=False, alias="ENABLE_ADMIN_PANEL")
    ENABLE_AUDIO_RECORDING: bool = Field(default=False, alias="ENABLE_AUDIO_RECORDING")

    model_config = SettingsConfigDict(
        env_file=(
            _PROJECT_ROOT / ".env",
            _BACKEND_DIR / ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()