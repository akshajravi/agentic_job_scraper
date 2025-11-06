"""
Resume parser using pdfplumber for text extraction and OpenAI for structured parsing.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

import pdfplumber
from openai import OpenAI

from agent.config import settings
from agent.storage.db import get_db
from agent.storage.models import ResumeData

logger = logging.getLogger(__name__)


class ResumeParser:
    """Parses resume PDFs and extracts structured information using AI."""

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the resume parser.

        Args:
            openai_api_key: OpenAI API key. If not provided, uses settings.
        """
        self.client = OpenAI(api_key=openai_api_key or settings.openai_api_key)

    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract raw text from PDF using pdfplumber.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text from the PDF

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF extraction fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"Resume PDF not found: {pdf_path}")

        logger.info(f"Extracting text from PDF: {pdf_path}")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

                full_text = "\n\n".join(text_parts)
                logger.info(f"Extracted {len(full_text)} characters from {len(pdf.pages)} pages")
                return full_text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise

    def _calculate_file_hash(self, pdf_path: Path) -> str:
        """Calculate SHA256 hash of the PDF file for caching.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Hex string of the file hash
        """
        sha256_hash = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _parse_resume_with_ai(self, resume_text: str) -> dict:
        """Use OpenAI to extract structured data from resume text.

        Args:
            resume_text: Raw text extracted from resume

        Returns:
            Dictionary with structured resume data
        """
        logger.info("Parsing resume with OpenAI GPT-4")

        system_prompt = """You are a resume parsing assistant. Extract structured information from resumes.
Return a JSON object with the following fields:
- skills: Array of technical skills (programming languages, frameworks, tools)
- experiences: Array of objects with {title, company, duration, description}
- education: Object with {school, degree, graduation_date, gpa (optional)}
- contact: Object with {name, email, phone (optional), location (optional)}

Be precise and only extract information that is clearly stated in the resume.
For graduation_date, use format: "Month Year" (e.g., "May 2024")
"""

        user_prompt = f"""Extract structured information from this resume:

{resume_text}

Return ONLY valid JSON, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            parsed_data = json.loads(response.choices[0].message.content)
            logger.info(f"Successfully parsed resume: {parsed_data.get('contact', {}).get('name', 'Unknown')}")
            return parsed_data

        except Exception as e:
            logger.error(f"Failed to parse resume with AI: {e}")
            raise

    def parse_resume(self, pdf_path: str | Path, force_reparse: bool = False) -> ResumeData:
        """Parse a resume PDF and cache the results in the database.

        Args:
            pdf_path: Path to the resume PDF file
            force_reparse: If True, reparse even if cached data exists

        Returns:
            ResumeData object with parsed information
        """
        pdf_path = Path(pdf_path)
        file_hash = self._calculate_file_hash(pdf_path)

        # Check if we have cached data for this resume
        with get_db() as db:
            cached_resume = db.query(ResumeData).filter(
                ResumeData.file_hash == file_hash
            ).first()

            if cached_resume and not force_reparse:
                logger.info("Using cached resume data")
                return cached_resume

        # Extract and parse resume
        resume_text = self._extract_text_from_pdf(pdf_path)
        parsed_data = self._parse_resume_with_ai(resume_text)

        # Store in database
        with get_db() as db:
            # Delete old cached data for this file
            db.query(ResumeData).filter(ResumeData.file_hash == file_hash).delete()

            resume_data = ResumeData(
                file_hash=file_hash,
                raw_text=resume_text,
                structured_data=json.dumps(parsed_data),
                file_path=str(pdf_path)
            )

            db.add(resume_data)
            db.commit()
            db.refresh(resume_data)

            # Store ID before expunging
            resume_id = resume_data.id
            logger.info(f"Cached resume data in database (ID: {resume_id})")

            # Make a detached copy with all attributes loaded
            db.expunge(resume_data)

        return resume_data

    def get_resume_summary(self, resume_data: ResumeData) -> str:
        """Generate a text summary of the resume for embedding/matching.

        Args:
            resume_data: Parsed resume data

        Returns:
            Formatted text summary
        """
        summary_parts = []

        # Parse structured data from JSON
        try:
            parsed_data = json.loads(resume_data.structured_data) if resume_data.structured_data else {}
        except (json.JSONDecodeError, TypeError):
            parsed_data = {}

        # Add skills
        skills = parsed_data.get('skills', [])
        if skills:
            summary_parts.append(f"Skills: {', '.join(skills)}")

        # Add experiences
        experiences = parsed_data.get('experiences', [])
        if experiences:
            exp_texts = []
            for exp in experiences:
                exp_text = f"{exp.get('title', 'Unknown')} at {exp.get('company', 'Unknown')}"
                if 'description' in exp:
                    exp_text += f": {exp['description']}"
                exp_texts.append(exp_text)
            summary_parts.append("Experience: " + "; ".join(exp_texts))

        # Add education
        education = parsed_data.get('education', {})
        if education:
            edu_text = f"Education: {education.get('degree', 'Unknown')} from {education.get('school', 'Unknown')}"
            if 'graduation_date' in education:
                edu_text += f" (Graduated: {education['graduation_date']})"
            summary_parts.append(edu_text)

        return "\n\n".join(summary_parts)


def parse_resume(pdf_path: str | Path, force_reparse: bool = False) -> ResumeData:
    """Convenience function to parse a resume.

    Args:
        pdf_path: Path to the resume PDF file
        force_reparse: If True, reparse even if cached data exists

    Returns:
        ResumeData object with parsed information
    """
    parser = ResumeParser()
    return parser.parse_resume(pdf_path, force_reparse)
