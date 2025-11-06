"""
Embedding-based job matching using OpenAI embeddings and cosine similarity.
"""
import json
import logging
from typing import List, Optional

import numpy as np
from openai import OpenAI

from agent.config import settings
from agent.storage.db import get_db
from agent.storage.models import Job, JobStatus, ResumeData

logger = logging.getLogger(__name__)


class EmbeddingMatcher:
    """Matches jobs to resumes using OpenAI embeddings and cosine similarity."""

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the embedding matcher.

        Args:
            openai_api_key: OpenAI API key. If not provided, uses settings.
        """
        self.client = OpenAI(api_key=openai_api_key or settings.openai_api_key)
        self.embedding_model = "text-embedding-3-small"

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for a text using OpenAI API.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            raise

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score between 0 and 1
        """
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)

        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _generate_match_reason(self, resume_data: ResumeData, job: Job, similarity_score: float) -> str:
        """Use OpenAI to generate a human-readable match reason.

        Args:
            resume_data: Parsed resume data
            job: Job posting
            similarity_score: Calculated similarity score

        Returns:
            Human-readable explanation of why this is a good match
        """
        # Parse structured data from JSON
        try:
            parsed_data = json.loads(resume_data.structured_data) if resume_data.structured_data else {}
        except (json.JSONDecodeError, TypeError):
            parsed_data = {}

        skills = parsed_data.get('skills', [])
        experiences = parsed_data.get('experiences', [])
        education = parsed_data.get('education', {})

        resume_summary = f"""
Skills: {', '.join(skills[:10]) if skills else 'N/A'}
Latest Experience: {experiences[0] if experiences else 'N/A'}
Education: {education.get('degree', 'N/A')} from {education.get('school', 'N/A')}
"""

        job_summary = f"""
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description[:500] if job.description else 'N/A'}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a career advisor. Explain in 1-2 sentences why a candidate is a good match for a job."
                    },
                    {
                        "role": "user",
                        "content": f"""Based on the resume and job posting below, explain why this is a good match (similarity score: {similarity_score:.2f}).

RESUME:
{resume_summary}

JOB:
{job_summary}

Provide a concise, specific reason focusing on relevant skills or experience."""
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"Failed to generate match reason: {e}")
            return f"Match score: {similarity_score:.2f}"

    def generate_resume_embedding(self, resume_data: ResumeData) -> List[float]:
        """Generate and cache embedding for resume.

        Args:
            resume_data: Parsed resume data

        Returns:
            Embedding vector for the resume
        """
        # Check if resume already has embedding
        if resume_data.embedding:
            logger.info("Using cached resume embedding")
            try:
                return json.loads(resume_data.embedding)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Failed to parse cached embedding, regenerating...")

        # Parse structured data from JSON
        try:
            parsed_data = json.loads(resume_data.structured_data) if resume_data.structured_data else {}
        except (json.JSONDecodeError, TypeError):
            parsed_data = {}

        skills = parsed_data.get('skills', [])
        experiences = parsed_data.get('experiences', [])
        education = parsed_data.get('education', {})

        # Generate resume summary text
        summary_parts = []

        if skills:
            summary_parts.append(f"Technical Skills: {', '.join(skills)}")

        if experiences:
            for exp in experiences[:3]:  # Top 3 experiences
                exp_text = f"{exp.get('title')} at {exp.get('company')}: {exp.get('description', '')[:200]}"
                summary_parts.append(exp_text)

        if education:
            summary_parts.append(f"{education.get('degree')} from {education.get('school')}")

        resume_summary = "\n".join(summary_parts)
        logger.info(f"Generating embedding for resume (length: {len(resume_summary)} chars)")

        embedding = self._get_embedding(resume_summary)

        # Cache the embedding in the database
        with get_db() as db:
            resume = db.query(ResumeData).filter(ResumeData.id == resume_data.id).first()
            if resume:
                resume.embedding = json.dumps(embedding)
                db.commit()
                logger.info("Cached resume embedding in database")

        return embedding

    def match_jobs(
        self,
        resume_data: ResumeData,
        threshold: float = None,
        generate_reasons: bool = True
    ) -> int:
        """Match jobs against resume using embeddings.

        Args:
            resume_data: Parsed resume data with embedding
            threshold: Minimum similarity score for a match (default from settings)
            generate_reasons: Whether to generate AI match reasons

        Returns:
            Number of jobs matched
        """
        if threshold is None:
            threshold = settings.match_threshold

        # Get all NEW jobs and match them (everything in one session)
        with get_db() as db:
            # Re-fetch resume data from database to ensure it's attached to this session
            resume_data = db.query(ResumeData).filter(ResumeData.id == resume_data.id).first()
            if not resume_data:
                logger.error("Resume data not found in database")
                return 0

            # Get resume embedding
            resume_embedding = self.generate_resume_embedding(resume_data)
            new_jobs = db.query(Job).filter(Job.status == JobStatus.NEW).all()
            logger.info(f"Found {len(new_jobs)} NEW jobs to match")

            if not new_jobs:
                return 0

            matched_count = 0

            for job in new_jobs:
                # Create job summary for embedding
                job_summary = f"{job.title} at {job.company}\n"
                if job.location:
                    job_summary += f"Location: {job.location}\n"
                if job.description:
                    job_summary += f"Description: {job.description[:500]}"

                # Generate job embedding
                job_embedding = self._get_embedding(job_summary)

                # Calculate similarity
                similarity = self._cosine_similarity(resume_embedding, job_embedding)

                logger.info(f"Job '{job.title}' at {job.company}: similarity = {similarity:.3f}")

                # Update job with match score
                if similarity >= threshold:
                    matched_count += 1

                    # Generate match reason
                    if generate_reasons:
                        try:
                            match_reason = self._generate_match_reason(resume_data, job, similarity)
                        except Exception as e:
                            logger.warning(f"Could not generate match reason: {e}")
                            match_reason = f"Similarity score: {similarity:.2f}"
                    else:
                        match_reason = f"Similarity score: {similarity:.2f}"

                    # Update job status
                    job.status = JobStatus.MATCHED
                    job.match_score = similarity
                    job.match_reason = match_reason

                    logger.info(f" MATCHED: {job.title} at {job.company} ({similarity:.3f})")
                else:
                    # Still store the score even if below threshold
                    job.match_score = similarity

            db.commit()
            logger.info(f"Matched {matched_count} jobs above threshold {threshold}")

            return matched_count


def match_jobs_for_resume(
    resume_data: ResumeData,
    threshold: float = None,
    generate_reasons: bool = True
) -> int:
    """Convenience function to match jobs against a resume.

    Args:
        resume_data: Parsed resume data
        threshold: Minimum similarity score for a match
        generate_reasons: Whether to generate AI match reasons

    Returns:
        Number of jobs matched
    """
    matcher = EmbeddingMatcher()
    return matcher.match_jobs(resume_data, threshold, generate_reasons)
