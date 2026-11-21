"""Settings loaded from environment variables or a local .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: Literal["huggingface", "openai", "gemini"] = "huggingface"
    hf_api_key: str = ""
    hf_model: str = "Qwen/Qwen3.5-9B:fastest"
    hf_home: Path = Path("./.model-cache")
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    database_url: str = "sqlite:///./data/assistant.db"
    data_dir: Path = Path("./data")
    max_upload_size_mb: int = Field(default=25, ge=1, le=100)
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)
    retrieval_k: int = Field(default=3, ge=1, le=20)
    retrieval_min_relevance_score: float = Field(default=0.2, ge=0, le=1)
    llm_timeout_seconds: int = Field(default=45, ge=5, le=180)
    llm_max_tokens: int = Field(default=400, ge=64, le=2000)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "indexes"


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object for the application."""
    return Settings()
