"""Configuration management."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = "SPCA AI Assistant"
    app_version: str = "1.0.0"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://spca:spca_password@localhost:5432/spca",
        alias="DATABASE_URL",
    )

    # API Keys
    zyte_api_key: Optional[str] = Field(default=None, alias="ZYTE_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")

    # Scraping
    spca_base_url: str = Field(default="https://www.spca.com", alias="SPCA_BASE_URL")
    scrape_rate_limit: float = Field(default=0.5, alias="SCRAPE_RATE_LIMIT")
    max_concurrent_requests: int = Field(default=5, alias="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")

    # Content Storage
    content_dir: str = Field(default="./content", alias="CONTENT_DIR")
    animal_content_dir: str = Field(default="./content/animals", alias="ANIMAL_CONTENT_DIR")
    general_content_dir: str = Field(default="./content/general", alias="GENERAL_CONTENT_DIR")

    # Google File Search
    file_search_store_name: str = Field(
        default="spca_knowledge_base", alias="FILE_SEARCH_STORE_NAME"
    )
    sync_batch_size: int = Field(default=50, alias="SYNC_BATCH_SIZE")

    # API Server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_debug: bool = Field(default=False, alias="API_DEBUG")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    # Session
    session_expiry_hours: int = Field(default=1, alias="SESSION_EXPIRY_HOURS")
    max_sessions: int = Field(default=10000, alias="MAX_SESSIONS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, alias="LOG_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"


class YAMLConfig:
    """Load configuration from YAML files."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load base config and environment-specific overrides."""
        env = os.getenv("APP_ENV", "development")

        # Load base config
        base_path = self.config_dir / "config.yaml"
        if base_path.exists():
            with open(base_path) as f:
                self._config = yaml.safe_load(f) or {}

        # Load environment-specific overrides
        env_path = self.config_dir / f"config.{env}.yaml"
        if env_path.exists():
            with open(env_path) as f:
                env_config = yaml.safe_load(f) or {}
                self._deep_merge(self._config, env_config)

    def _deep_merge(self, base: dict, override: dict) -> None:
        """Recursively merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, path: str, default: Any = None) -> Any:
        """Get config value by dot-notation path."""
        keys = path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


@lru_cache()
def get_yaml_config() -> YAMLConfig:
    """Get cached YAML config instance."""
    return YAMLConfig()
