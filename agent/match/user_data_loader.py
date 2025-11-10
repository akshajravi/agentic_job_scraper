"""
User data loader - loads personal information from JSON file instead of parsing resume.
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UserData:
    """Container for user application data loaded from JSON."""

    def __init__(self, data: dict):
        """Initialize user data from dictionary.

        Args:
            data: Dictionary containing all user data fields
        """
        self._data = data

        # Extract commonly used fields for easy access
        self.contact = data.get('contact', {})
        self.education = data.get('education', {})
        self.work_authorization = data.get('work_authorization', {})
        self.demographics = data.get('demographics', {})
        self.experiences = data.get('experience', [])
        
        # Flatten skills into a single list for backward compatibility
        skills_dict = data.get('skills', {})
        self.skills = (
            skills_dict.get('programming_languages', []) +
            skills_dict.get('frameworks', []) +
            skills_dict.get('tools', []) +
            skills_dict.get('technologies', [])
        )
        
        self.projects = data.get('projects', [])
        self.certifications = data.get('certifications', [])
        self.questions = data.get('questions', {})
        self.internship_specific = data.get('internship_specific', {})
        self.technical_background = data.get('technical_background', {})
        self.behavioral_questions = data.get('behavioral_questions', {})
        self.preferences = data.get('preferences', {})
        self.legal_questions = data.get('legal_questions', {})
        self.additional_info = data.get('additional_info', {})

    def get(self, key: str, default=None):
        """Get a value from the raw data dictionary.

        Args:
            key: Key to look up
            default: Default value if key not found

        Returns:
            Value for the key or default
        """
        return self._data.get(key, default)

    def to_dict(self) -> dict:
        """Convert user data back to dictionary format.

        Returns:
            Dictionary containing all user data
        """
        return self._data

    def get_summary_text(self) -> str:
        """Generate a text summary of user data for embeddings/matching.

        Returns:
            Formatted text summary suitable for job matching
        """
        summary_parts = []

        # Add contact name
        if self.contact.get('full_name'):
            summary_parts.append(f"Name: {self.contact['full_name']}")
        elif self.contact.get('first_name'):
            name = f"{self.contact['first_name']} {self.contact.get('last_name', '')}".strip()
            summary_parts.append(f"Name: {name}")

        # Add skills
        if self.skills:
            summary_parts.append(f"Technical Skills: {', '.join(self.skills[:20])}")

        # Add experiences
        if self.experiences:
            exp_texts = []
            for exp in self.experiences[:3]:  # Top 3 experiences
                exp_text = f"{exp.get('title', 'Unknown')} at {exp.get('company', 'Unknown')}"
                if exp.get('description'):
                    exp_text += f": {exp['description'][:200]}"
                exp_texts.append(exp_text)
            summary_parts.append("Experience: " + "; ".join(exp_texts))

        # Add education
        if self.education:
            edu = self.education
            edu_text = f"Education: {edu.get('degree', 'Unknown')} in {edu.get('major', edu.get('degree', 'Unknown'))}"
            if edu.get('school'):
                edu_text += f" from {edu['school']}"
            if edu.get('graduation_date') or edu.get('expected_graduation'):
                grad_date = edu.get('graduation_date') or edu.get('expected_graduation')
                edu_text += f" (Expected: {grad_date})"
            if edu.get('gpa'):
                edu_text += f" | GPA: {edu['gpa']}"
            summary_parts.append(edu_text)

        # Add projects
        if self.projects:
            project_texts = []
            for proj in self.projects[:3]:  # Top 3 projects
                proj_text = f"{proj.get('name', 'Project')}"
                if proj.get('description'):
                    proj_text += f": {proj['description'][:150]}"
                project_texts.append(proj_text)
            summary_parts.append("Projects: " + "; ".join(project_texts))

        return "\n\n".join(summary_parts)


def load_user_data(json_path: str | Path = "user_data.json") -> UserData:
    """Load user data from JSON file.

    Args:
        json_path: Path to the user data JSON file

    Returns:
        UserData object with loaded information

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        json.JSONDecodeError: If JSON file is invalid
    """
    json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(
            f"User data file not found: {json_path}\n"
            "Please create a user_data.json file with your personal information.\n"
            "See user_data.json template for the expected structure."
        )

    logger.info(f"Loading user data from: {json_path}")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        user_data = UserData(data)
        logger.info(f"Successfully loaded user data for: {user_data.contact.get('full_name', 'Unknown')}")
        return user_data

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in user data file: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load user data: {e}")
        raise


def validate_user_data(user_data: UserData) -> tuple[bool, list[str]]:
    """Validate that required user data fields are filled in.

    Args:
        user_data: UserData object to validate

    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    missing_fields = []

    # Check required contact fields
    required_contact = ['first_name', 'last_name', 'email', 'phone']
    for field in required_contact:
        if not user_data.contact.get(field):
            missing_fields.append(f"contact.{field}")

    # Check required education fields
    required_education = ['school', 'degree', 'major']
    for field in required_education:
        if not user_data.education.get(field):
            missing_fields.append(f"education.{field}")

    # Check if there are any skills
    if not user_data.skills:
        missing_fields.append("skills (at least one category)")

    # Warn about work authorization (not required but important)
    if user_data.work_authorization.get('require_visa_sponsorship') is None:
        logger.warning("Work authorization information not filled out - this may cause application issues")

    is_valid = len(missing_fields) == 0
    return is_valid, missing_fields

