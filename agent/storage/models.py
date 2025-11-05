"""SQLAlchemy models for job tracking database."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Float, Boolean, DateTime, Integer,
    ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class JobStatus(str, enum.Enum):
    """Status of a job listing."""
    NEW = "new"
    MATCHED = "matched"
    APPLIED = "applied"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApplicationStatus(str, enum.Enum):
    """Status of a job application."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    REJECTED = "rejected"
    INTERVIEWED = "interviewed"
    OFFER = "offer"


class ATSType(str, enum.Enum):
    """Types of Applicant Tracking Systems."""
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    ASHBY = "ashby"
    UNKNOWN = "unknown"


class Job(Base):
    """Job listing model."""
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Job Details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    remote: Mapped[bool] = mapped_column(Boolean, default=False)

    # Job Description
    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)

    # Application Details
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    ats_type: Mapped[ATSType] = mapped_column(
        SQLEnum(ATSType),
        default=ATSType.UNKNOWN
    )

    # Source Information
    source: Mapped[str] = mapped_column(String(200))  # e.g., "github:SimplifyJobs/Summer2025"
    source_id: Mapped[Optional[str]] = mapped_column(String(200))  # Original ID from source

    # Matching Score
    match_score: Mapped[Optional[float]] = mapped_column(Float)
    match_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Status
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus),
        default=JobStatus.NEW
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_company", "company"),
        Index("idx_jobs_match_score", "match_score"),
        Index("idx_jobs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}', status='{self.status}')>"


class Application(Base):
    """Job application tracking model."""
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign Key
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    # Application Details
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus),
        default=ApplicationStatus.PENDING
    )

    # Submission Details
    submitted_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON of form data
    response_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON of response

    # Error Tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="applications")

    # Indexes
    __table_args__ = (
        Index("idx_applications_job_id", "job_id"),
        Index("idx_applications_status", "status"),
        Index("idx_applications_submitted_at", "submitted_at"),
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, job_id={self.job_id}, status='{self.status}')>"


class ResumeData(Base):
    """Cached resume data for matching."""
    __tablename__ = "resume_data"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Resume Content
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON of parsed data

    # Embeddings
    embedding: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of floats

    # Metadata
    file_path: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<ResumeData(id={self.id}, file_path='{self.file_path}')>"
