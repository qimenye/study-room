"""应用配置：统一从环境变量 / .env 读取，避免硬编码。"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_list(key: str, default: str) -> list:
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """轻量配置对象，不依赖 pydantic-settings。"""

    app_name = "线上自习室 API"
    version = "0.1.0"
    base_dir = BASE_DIR

    env = os.getenv("ENV", "dev")
    app_timezone = os.getenv("APP_TIMEZONE", "Asia/Shanghai")

    # 默认 SQLite，保证零配置可跑
    database_url = os.getenv("DATABASE_URL") or "sqlite:///" + (BASE_DIR / "studyroom.db").as_posix()

    DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-before-deploying-0123456789"
    jwt_secret = os.getenv("JWT_SECRET", DEV_JWT_SECRET)
    jwt_algorithm = "HS256"
    access_token_expire_minutes = _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)

    cors_origins = _get_list(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
    )

    llm_provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    llm_api_key = os.getenv("LLM_API_KEY", "").strip()
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").strip()
    llm_model = os.getenv("LLM_MODEL", "deepseek-chat").strip()
    agent_rate_limit_per_minute = _get_int("AGENT_RATE_LIMIT_PER_MINUTE", 6)

    ws_heartbeat_timeout = _get_int("WS_HEARTBEAT_TIMEOUT", 60)
    ws_sweep_interval = _get_int("WS_SWEEP_INTERVAL", 15)

    @property
    def jwt_secret_is_weak(self) -> bool:
        """HS256 建议密钥不短于 32 字节；等于内置开发密钥也算弱。"""
        return len(self.jwt_secret.encode("utf-8")) < 32 or self.jwt_secret == self.DEV_JWT_SECRET

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"prod", "production"}

    @property
    def jwt_secret_is_weak(self) -> bool:
        """HS256 建议密钥不短于 32 字节；等于内置开发密钥也算弱。"""
        return len(self.jwt_secret.encode("utf-8")) < 32 or self.jwt_secret == self.DEV_JWT_SECRET

    @property
    def llm_enabled(self) -> bool:
        """没有配 Key 或明确用 mock 时，走本地模板兜底。"""
        if self.llm_provider in {"mock", "none", ""}:
            return False
        # 本地 Ollama 不需要 Key
        if self.llm_provider == "ollama":
            return True
        return bool(self.llm_api_key)


settings = Settings()
