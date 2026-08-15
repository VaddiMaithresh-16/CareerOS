"""Env-driven config. No secrets hard-coded. Per spec section 51/52."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"

    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_database: str = "careeros"
    mysql_user: str = "careeros"
    mysql_password: str = ""

    database_url: str = ""

    jsearch_api_key: str = ""
    job_api_mode: str = "mock"  # "mock" | "live"

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "in"  # gb, us, in, etc — see Adzuna docs for supported codes

    job_sources: str = "jsearch,adzuna,remotive,remoteok,arbeitnow"  # comma-separated, used when job_api_mode=live

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"  # alias, auto-follows Google rollouts — never pin exact version
    llama_cpp_base_url: str = ""

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # NVIDIA NIM
    nvidia_api_key: str = ""
    nvidia_model: str = "meta/llama-3.1-70b-instruct"

    qdrant_url: str = ""

    firecrawl_api_key: str = ""

    api_key: str = ""  # set to require X-API-Key header on all endpoints; empty = open (dev default)
    rate_limit_per_minute: int = 60

    gradio_username: str = ""
    gradio_password: str = ""

    llm_provider_mode: str = "auto"  # "auto" | "llama" | "gemini" | "openrouter" | "nvidia" | "none"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def resolved_database_url(self) -> str:
        # Always use MySQL - never fall back to SQLite
        if self.database_url:
            return self.database_url

        # Build MySQL URL from components
        if all([self.mysql_host, self.mysql_port, self.mysql_database, self.mysql_user]):
            return (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            )

        # If neither is properly configured, raise an error
        raise ValueError(
            "MySQL database not properly configured. Either set DATABASE_URL or provide "
            "all of MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, and MYSQL_USER."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
