"""Normalize and store job listings in the database."""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from agent.storage.db import get_db
from agent.storage.models import Job, JobStatus

logger = logging.getLogger(__name__)


class JobNormalizer:
    """Normalize and store job listings."""

    def normalize_and_store(self, raw_jobs: list[dict]) -> tuple[int, int]:
        """
        Normalize raw job data and store in database.

        Args:
            raw_jobs: List of raw job dictionaries from scrapers

        Returns:
            Tuple of (new_jobs, skipped_jobs)
        """
        new_count = 0
        skipped_count = 0

        with get_db() as db:
            for raw_job in raw_jobs:
                try:
                    # Check if job already exists by URL
                    existing = db.query(Job).filter_by(url=raw_job["url"]).first()

                    if existing:
                        logger.debug(f"Job already exists: {raw_job['title']} at {raw_job['company']}")
                        skipped_count += 1
                        continue

                    # Create new job
                    job = Job(
                        title=raw_job["title"],
                        company=raw_job["company"],
                        location=raw_job.get("location"),
                        remote=raw_job.get("remote", False),
                        url=raw_job["url"],
                        ats_type=raw_job.get("ats_type"),
                        source=raw_job.get("source", "unknown"),
                        source_id=raw_job.get("source_id"),
                        description=raw_job.get("description"),
                        requirements=raw_job.get("requirements"),
                        posted_date=raw_job.get("posted_date"),
                        deadline=raw_job.get("deadline"),
                        status=JobStatus.NEW,
                    )

                    db.add(job)
                    new_count += 1
                    logger.info(f"Added new job: {job.title} at {job.company}")

                except IntegrityError as e:
                    logger.warning(f"Duplicate job URL: {raw_job.get('url')}")
                    db.rollback()
                    skipped_count += 1
                except Exception as e:
                    logger.error(f"Error storing job: {e}")
                    db.rollback()
                    skipped_count += 1

        logger.info(f"Normalization complete: {new_count} new, {skipped_count} skipped")
        return new_count, skipped_count

    def get_new_jobs(self, limit: Optional[int] = None) -> list[Job]:
        """Get all jobs with NEW status."""
        with get_db() as db:
            query = db.query(Job).filter_by(status=JobStatus.NEW)

            if limit:
                query = query.limit(limit)

            return query.all()

    def get_matched_jobs(self, limit: Optional[int] = None) -> list[Job]:
        """Get all jobs with MATCHED status."""
        with get_db() as db:
            query = db.query(Job).filter_by(status=JobStatus.MATCHED).order_by(
                Job.match_score.desc()
            )

            if limit:
                query = query.limit(limit)

            return query.all()

    def update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        match_score: Optional[float] = None,
        match_reason: Optional[str] = None
    ) -> None:
        """Update job status and matching information."""
        with get_db() as db:
            job = db.query(Job).filter_by(id=job_id).first()

            if not job:
                logger.error(f"Job {job_id} not found")
                return

            job.status = status

            if match_score is not None:
                job.match_score = match_score

            if match_reason is not None:
                job.match_reason = match_reason

            logger.info(f"Updated job {job_id} status to {status}")
