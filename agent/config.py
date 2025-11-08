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
        # For dropdowns: Common options include Google, Indeed, LinkedIn, Company Website, Friend, Recruiter, Other
        # Use "Google job search" or similar generic option that's likely to be present
        "how did you hear": "Google job search",
        "how did you find": "Google job search",
        "where did you hear": "Google job search",
        "where did you find": "Google job search",
        "source of application": "Google job search",
        "how did you learn": "Google job search",
        "hear about this": "Google job search",
        "find this position": "Google job search",
        "find this job": "Google job search",
        "learn about this": "Google job search",
        "source of referral": "Google job search",
        "please specify": "Online job board",  # For "Other" follow-up questions
        "specify other": "Online job board",
        "if other": "Online job board",
        
        # Clearance and export control questions
        "clearance eligibility": "Yes, I am eligible for a U.S. security clearance",
        "security clearance": "N/A - have never held U.S. security clearance",
        "u.s. person status": "Yes, I am a U.S. person",
        "export control": "I understand and acknowledge these requirements",
        "held a u.s. security clearance": "N/A - have never held U.S. security clearance",
        
        # Company history questions
        "history with": "No, I have not previously worked for or applied to this company",
        "ever been employed": "No",
        "previously worked": "No",
        "applied before": "No",
        
        # Onsite/location availability
        "able to be onsite": "Yes",
        "work onsite": "Yes",
        "able to work onsite": "Yes",
        "relocate": "Yes, I am willing to relocate",
        "willing to relocate": "Yes",
        
        # Demographics (EEO questions) - User's actual information
        "gender": "Male",
        "race": "Asian",  # Will try "South Asian" first if available, fall back to "Asian"
        "ethnicity": "Asian",
        "asian": "South Asian",  # Specific Asian subgroup if asked
        "hispanic/latino": "No",
        "hispanic or latino": "No",
        "veteran status": "I am not a protected veteran",
        "protected veteran": "I am not a protected veteran",
        "disability status": "No, I do not have a disability",
        "disability": "No, I do not have a disability",
        "have a disability": "No",
        
        # Location/country
        "country": "United States",
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
