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
    email_user: Optional[str] = None  # For compatibility with greenhouse.py
    email_address: Optional[str] = None
    email_password: Optional[str] = None  # App password for Gmail
    notification_email: Optional[str] = None  # Where to send notifications

    # Scheduler
    schedule_enabled: bool = False
    schedule_time: str = "09:00"  # 24-hour format
    schedule_timezone: str = "America/New_York"

    # Selenium/Playwright Settings
    headless: bool = True
    browser_timeout: int = 30  # seconds

    # Rate Limiting
    request_delay: float = 1.0  # seconds between requests
    max_retries: int = 3

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/agent.log"

    # Predetermined Answers for Common Questions
    # These are used to avoid unnecessary OpenAI API calls for simple questions
    predetermined_answers: dict[str, str] = {
        # Conflict of interest questions
        "conflicts": "No",
        "conflict of interest": "No",
        "any conflicts": "No",
        "business conflicts": "No",
        
        # Previous employment questions
        "worked here before": "No",
        "previously employed": "No",
        "former employee": "No",
        "have you worked": "No",
        
        # Legal/compliance questions
        "authorized to work": "Yes",
        "work authorization": "Yes",
        "legally authorized": "Yes",
        "require sponsorship": "No",
        "visa sponsorship": "No",
        "need sponsorship": "No",
        
        # Criminal background
        "criminal record": "No",
        "convicted of": "No",
        "felony": "No",
        
        # Referrals
        "referred by": "No",
        "employee referral": "No",
        "know anyone": "No",
        
        # Age/discrimination
        "18 years": "Yes",
        "over 18": "Yes",
        "18 or older": "Yes",
        
        # General consent/acknowledgments
        "accurate information": "Yes",
        "information is true": "Yes",
        "certify that": "Yes",
        "acknowledge that": "Yes",
        
        # How did you hear about us / source questions
        # For dropdowns: tries "Corporate Website" first, falls back to "Other" if not available
        # For text fields: uses "Corporate Website"
        "how did you hear": "Corporate Website",
        "how did you find": "Corporate Website",
        "where did you hear": "Corporate Website",
        "where did you find": "Corporate Website",
        "source of application": "Corporate Website",
        "how did you learn": "Corporate Website",
        "hear about this": "Corporate Website",
        "find this position": "Corporate Website",
        "find this job": "Corporate Website",
        "learn about this": "Corporate Website",
        "source of referral": "Corporate Website",
        "please specify": "Corporate Website",  # For "Other" follow-up questions
        "specify other": "Corporate Website",
        "if other": "Corporate Website",
    }

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
