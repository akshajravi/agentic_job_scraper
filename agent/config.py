"""Configuration management for the job scraper agent."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    database_url: str = "sqlite:///./jobs.db"

    # AI/ML Settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"  # OpenAI model
    match_threshold: float = 0.7  # Minimum similarity score for job matching

    # Resume
    resume_path: str = "./resume.pdf"

    # Job Sources
    github_repos: list[str] = [
        "SimplifyJobs/Summer2025-Internships",
        "ReaVNaiL/New-Grad-2024",
        "cvrve/New-Grad-2025"
    ]

    # Application Settings
    auto_apply: bool = False  # Safety switch - requires explicit enabling
    max_applications_per_day: int = 10

    # Email Notifications
    email_enabled: bool = True
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_address: Optional[str] = None
    email_password: Optional[str] = None  # App password for Gmail
    notification_email: Optional[str] = None  # Where to send notifications

    # Scheduler
    schedule_enabled: bool = False
    schedule_time: str = "09:00"  # 24-hour format
    schedule_timezone: str = "America/New_York"

    # Selenium/Playwright Settings
    headless_browser: bool = True
    browser_timeout: int = 30  # seconds

    # Rate Limiting
    request_delay: float = 1.0  # seconds between requests
    max_retries: int = 3

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/agent.log"

    @property
    def resume_file(self) -> Path:
        """Get resume path as Path object."""
        return Path(self.resume_path)

    @property
    def log_dir(self) -> Path:
        """Get log directory as Path object."""
        return Path(self.log_file).parent


# Global settings instance
settings = Settings()
