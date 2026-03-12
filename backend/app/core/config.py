"""Vayuntra — Core Configuration"""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    APP_SECRET_KEY: str = "dev-secret-change-in-prod"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    ALLOWED_HOSTS: List[str] = ["*"]

    # Database — local PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vayuntra"

    # JWT
    JWT_SECRET_KEY: str = "jwt-dev-secret-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours for demo

    # ML
    ANOMALY_DETECTION_THRESHOLD: float = 0.75

    # LLM — disabled by default; enable when Mistral GGUF model is present
    LLM_ENABLED: bool = False
    LLM_MODEL_PATH: str = "/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    LLM_CONTEXT_LENGTH: int = 4096
    LLM_N_THREADS: int = 4
    LLM_N_GPU_LAYERS: int = 0          # 0 = CPU-only; set >0 for GPU offload
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.1
    LLM_CLOUD_FALLBACK: bool = False
    LLM_CLOUD_API_KEY: Optional[str] = None
    LLM_CLOUD_ENDPOINT: str = "https://api.mistral.ai/v1"

    # Feature flags
    FEATURE_LLM_REMEDIATION: bool = True
    FEATURE_AUTO_ISOLATION: bool = True
    FEATURE_BEHAVIORAL_MEMORY: bool = True

    PROMETHEUS_ENABLED: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
