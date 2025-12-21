"""
ChainIQ Core Configuration

Application settings loaded from environment variables.
All configuration is centralized here for consistency.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""

    # Service metadata
    service_name: str = Field(default="chainiq", description="Service identifier")
    service_version: str = Field(default="2.0.0", description="Service version")

    # Database
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection URL",
    )

    # ML Shadow Mode
    enable_shadow_mode: bool = Field(
        default=False,
        description="Enable shadow mode for parallel real ML model scoring",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    class Config:
        """Pydantic configuration."""

        env_prefix = ""
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
