from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    MONGODB_URI: str = "mongodb://localhost:27017"
    CHROMA_PATH: str = str(_BACKEND_DIR / "chroma_db")
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    USE_RERANKER: bool = False

    SECRET_KEY: str = "changethis"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FIRST_SUPERUSER_EMAIL: str = "admin@procureai.local"
    FIRST_SUPERUSER_PASSWORD: str = "changethis"

    @field_validator("SECRET_KEY")
    @classmethod
    def warn_if_default_secret(cls, v: str) -> str:
        if v == "changethis":
            print("WARNING: SECRET_KEY is set to the default value. Change it before deploying to production.")
        return v

    @field_validator("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
