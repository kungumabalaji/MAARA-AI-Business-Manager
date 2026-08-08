import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_jwt_audience: str = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")

    # Comma-separated list of allowed frontend origins. Defaults cover local Vite dev.
    cors_allow_origins: str = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
