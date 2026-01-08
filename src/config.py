from typing import Dict, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DefaultSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        frozen=True,
        env_nested_delimiter="__",
    )


class ArxivSettings(DefaultSettings):
    """ArXiv API settings."""

    base_url: str = "https://export.arxiv.org/api/query"
    search_category: str = "cond-mat.mtrl-sci"
    max_results: int = 10
    rate_limit_delay: float = 3.0
    timeout_seconds: int = 30
    pdf_cache_dir: str = "./pdf_cache"
    namespaces: Dict[str, str] = Field(
        default_factory=lambda: {
            "atom": "http://www.w3.org/2005/Atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
    )


class Settings(DefaultSettings):
    """Application settings."""

    app_version: str = "0.1.0"
    debug: bool = True
    environment: str = "development"
    service_name: str = "arxiv-pdf-downloader"

    # PostgreSQL configuration
    postgres_database_url: str = "postgresql://user:local_downloader@localhost:5432/arxiv_downloader"
    postgres_echo_sql: bool = False
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 0

    # ArXiv configuration
    arxiv: ArxivSettings = Field(default_factory=ArxivSettings)


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
