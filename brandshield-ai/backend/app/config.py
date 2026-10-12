from typing import List
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI (keep secret).",
        repr=False,
    )
    DATABASE_NAME: str = Field(
        default="brandshield_dev",
        description="Active application database name.",
    )
    TEST_DATABASE_NAME: str = Field(
        default="brandshield_test",
        description="Isolated test database name (never equal to DATABASE_NAME).",
    )
    FRONTEND_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated allowed CORS origins.",
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Current runtime environment (development, staging, production).",
    )
    PORT: int = Field(
        default=8000,
        description="HTTP server port.",
    )

    @model_validator(mode="after")
    def validate_test_database_distinct(self) -> "Settings":
        if self.DATABASE_NAME and self.TEST_DATABASE_NAME:
            if self.DATABASE_NAME.strip().lower() == self.TEST_DATABASE_NAME.strip().lower():
                raise ValueError(
                    f"TEST_DATABASE_NAME '{self.TEST_DATABASE_NAME}' cannot be the same as "
                    f"DATABASE_NAME '{self.DATABASE_NAME}'. Tests must use an isolated database."
                )
        return self

    @property
    def cors_origins(self) -> List[str]:
        """Parsed list of allowed origins."""
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]


settings = Settings()
