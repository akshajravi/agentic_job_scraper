"""
Greenhouse ATS application automation using Playwright.
"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout, sync_playwright

from agent.config import settings
from agent.match.user_data_loader import UserData
from agent.storage.db import get_db
from agent.storage.models import Application, ApplicationStatus, Job, JobStatus

logger = logging.getLogger(__name__)


class GreenhouseApplier:
    """Automates job applications on Greenhouse ATS platform."""

    def __init__(
        self,
        user_data: UserData,
        resume_pdf_path: str | Path = None,
        headless: bool = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize Greenhouse applier.

        Args:
            user_data: User data loaded from JSON
            resume_pdf_path: Path to resume PDF file for upload (optional)
            headless: Run browser in headless mode (default from settings)
            openai_api_key: OpenAI API key for answering custom questions
        """
        self.user_data = user_data
        self.resume_pdf_path = Path(resume_pdf_path) if resume_pdf_path else None
        self.headless = headless if headless is not None else settings.headless
        self.openai_client = OpenAI(api_key=openai_api_key or settings.openai_api_key)

        if self.resume_pdf_path and not self.resume_pdf_path.exists():
            raise FileNotFoundError(f"Resume PDF not found: {self.resume_pdf_path}")

    def _answer_custom_question(self, question: str, field_type: str = "text") -> str:
        """Use OpenAI to generate an answer to a custom application question.

        Args:
            question: The question text
            field_type: Type of form field (text, textarea, select, etc.)

        Returns:
            Generated answer
        """
        logger.info(f"Generating answer for: {question}")

        user_context = f"""
Name: {self.user_data.contact.get('full_name', 'Unknown')}
Skills: {', '.join(self.user_data.skills[:15])}
Latest Experience: {self.user_data.experiences[0] if self.user_data.experiences else 'N/A'}
Education: {self.user_data.education.get('degree', 'N/A')} from {self.user_data.education.get('school', 'N/A')}
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """You are helping fill out a job application. Answer questions concisely and professionally based on the candidate's resume.
For yes/no questions, answer with just "Yes" or "No".
For short text fields, keep answers under 100 words.
For longer text fields (cover letters, etc.), you can write 200-300 words."""
                    },
                    {
                        "role": "user",
                        "content": f"""User Context:
{user_context}

Question: {question}

Provide a professional answer suitable for a job application. Be honest and based only on the user information provided."""
                    }
                ],
                temperature=0.5,
                max_tokens=400
            )

            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated answer (length: {len(answer)} chars)")
            return answer

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return "I am very interested in this position and believe my background aligns well with the requirements."

    def _detect_custom_questions(self, page: Page) -> List[Dict[str, str]]:
        """Detect custom questions in the Greenhouse application form.

        Args:
            page: Playwright page object

        Returns:
            List of dictionaries with question details
        """
        questions = []

        # Look for text inputs (excluding standard fields)
        standard_fields = ['first_name', 'last_name', 'email', 'phone']
        text_inputs = page.locator('input[type="text"], input[type="email"], input[type="tel"]').all()

        for input_elem in text_inputs:
            input_id = input_elem.get_attribute('id') or ''
            input_name = input_elem.get_attribute('name') or ''

            # Skip standard fields
            if any(field in input_id.lower() or field in input_name.lower() for field in standard_fields):
                continue

            # Try to find associated label
            label_text = ""
            try:
                label = page.locator(f'label[for="{input_id}"]').first
                if label.count() > 0:
                    label_text = label.inner_text().strip()
            except:
                pass

            if label_text and len(label_text) > 5:  # Valid question
                questions.append({
                    'type': 'text',
                    'question': label_text,
                    'selector': f'#{input_id}' if input_id else f'[name="{input_name}"]',
                    'id': input_id or input_name
                })

        # Look for textareas
        textareas = page.locator('textarea').all()
        for textarea in textareas:
            textarea_id = textarea.get_attribute('id') or ''
            textarea_name = textarea.get_attribute('name') or ''

            # Try to find associated label
            label_text = ""
            try:
                label = page.locator(f'label[for="{textarea_id}"]').first
                if label.count() > 0:
                    label_text = label.inner_text().strip()
            except:
                pass

            if label_text and len(label_text) > 5:
                questions.append({
                    'type': 'textarea',
                    'question': label_text,
                    'selector': f'#{textarea_id}' if textarea_id else f'[name="{textarea_name}"]',
                    'id': textarea_id or textarea_name
                })

        # Look for select dropdowns (excluding standard ones like country)
        selects = page.locator('select').all()
        for select in selects:
            select_id = select.get_attribute('id') or ''
            select_name = select.get_attribute('name') or ''

            # Skip standard selects
            if 'country' in select_id.lower() or 'state' in select_id.lower():
                continue

            label_text = ""
            try:
                label = page.locator(f'label[for="{select_id}"]').first
                if label.count() > 0:
                    label_text = label.inner_text().strip()
            except:
                pass

            if label_text and len(label_text) > 5:
                # Get options
                options = select.locator('option').all_inner_texts()
                questions.append({
                    'type': 'select',
                    'question': label_text,
                    'selector': f'#{select_id}' if select_id else f'[name="{select_name}"]',
                    'id': select_id or select_name,
                    'options': options
                })

        logger.info(f"Detected {len(questions)} custom questions")
        return questions

    def fill_standard_fields(self, page: Page) -> bool:
        """Fill standard Greenhouse application fields.

        Args:
            page: Playwright page object

        Returns:
            True if successful, False otherwise
        """
        try:
            contact = self.user_data.contact

            # First name
            first_name_input = page.locator('input[name*="first_name"], input[id*="first_name"]').first
            if first_name_input.count() > 0:
                first_name = contact.get('first_name', '')
                first_name_input.fill(first_name)
                logger.info(f"Filled first name: {first_name}")

            # Last name
            last_name_input = page.locator('input[name*="last_name"], input[id*="last_name"]').first
            if last_name_input.count() > 0:
                last_name = contact.get('last_name', '')
                last_name_input.fill(last_name)
                logger.info(f"Filled last name: {last_name}")

            # Email
            email_input = page.locator('input[type="email"], input[name*="email"]').first
            if email_input.count() > 0:
                email = contact.get('email', settings.email_user or '')
                email_input.fill(email)
                logger.info(f"Filled email: {email}")

            # Phone
            phone_input = page.locator('input[type="tel"], input[name*="phone"]').first
            if phone_input.count() > 0:
                phone = contact.get('phone', '')
                if phone:
                    phone_input.fill(phone)
                    logger.info(f"Filled phone: {phone}")

            # Resume upload (only if provided)
            if self.resume_pdf_path:
                resume_upload = page.locator('input[type="file"]').first
                if resume_upload.count() > 0:
                    resume_upload.set_input_files(str(self.resume_pdf_path.absolute()))
                    logger.info(f"Uploaded resume: {self.resume_pdf_path.name}")
                    time.sleep(1)  # Wait for upload

            return True

        except Exception as e:
            logger.error(f"Failed to fill standard fields: {e}")
            return False

    def apply_to_job(
        self,
        job: Job,
        manual_review: bool = False,
        review_callback: Optional[callable] = None
    ) -> Tuple[bool, str]:
        """Apply to a job on Greenhouse.

        Args:
            job: Job object to apply to
            manual_review: If True, wait for user review before submitting
            review_callback: Function to call for manual review (receives form_data, returns approved: bool)

        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Starting application for: {job.title} at {job.company}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()

            try:
                # Navigate to job URL
                logger.info(f"Navigating to: {job.url}")
                page.goto(job.url, timeout=30000)
                time.sleep(2)

                # Look for "Apply" button or application form
                apply_button = page.locator('a:has-text("Apply"), button:has-text("Apply")').first
                if apply_button.count() > 0:
                    apply_button.click()
                    time.sleep(2)

                # Fill standard fields
                if not self.fill_standard_fields(page):
                    return False, "Failed to fill standard fields"

                # Detect custom questions
                custom_questions = self._detect_custom_questions(page)

                # Generate answers for custom questions
                form_data = {}
                for question_info in custom_questions:
                    answer = self._answer_custom_question(
                        question_info['question'],
                        question_info['type']
                    )
                    form_data[question_info['id']] = {
                        'question': question_info['question'],
                        'answer': answer,
                        'selector': question_info['selector'],
                        'type': question_info['type']
                    }

                # Manual review if requested
                if manual_review and review_callback:
                    logger.info("Requesting manual review...")
                    approved = review_callback(page, form_data, job)

                    if not approved:
                        logger.info("Application skipped by user")
                        return False, "Skipped by user during manual review"

                # Fill custom question fields
                for field_id, field_data in form_data.items():
                    try:
                        element = page.locator(field_data['selector']).first
                        if element.count() > 0:
                            if field_data['type'] in ['text', 'textarea']:
                                element.fill(field_data['answer'])
                            elif field_data['type'] == 'select':
                                # Try to select the best matching option
                                element.select_option(label=field_data['answer'])
                            logger.info(f"Filled custom field: {field_data['question'][:50]}...")
                    except Exception as e:
                        logger.warning(f"Could not fill field {field_id}: {e}")

                # Submit the application
                submit_button = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
                if submit_button.count() > 0:
                    logger.info("Submitting application...")
                    submit_button.click()

                    # Wait for confirmation or error
                    time.sleep(3)

                    # Check for success message
                    success_indicators = [
                        'Thank you', 'submitted', 'received', 'confirmation',
                        'We\'ll be in touch', 'Application complete'
                    ]

                    page_text = page.inner_text('body').lower()
                    if any(indicator.lower() in page_text for indicator in success_indicators):
                        logger.info("Application submitted successfully!")

                        # Take success screenshot
                        screenshot_path = f"screenshots/success_{job.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        Path("screenshots").mkdir(exist_ok=True)
                        page.screenshot(path=screenshot_path)

                        # Update database
                        with get_db() as db:
                            application = Application(
                                job_id=job.id,
                                status=ApplicationStatus.SUBMITTED,
                                submitted_at=datetime.now(),
                                form_data=form_data,
                                response_data={'success': True, 'screenshot': screenshot_path}
                            )
                            db.add(application)

                            # Update job status
                            db_job = db.query(Job).filter(Job.id == job.id).first()
                            if db_job:
                                db_job.status = JobStatus.APPLIED

                            db.commit()

                        return True, f"Successfully applied! Screenshot: {screenshot_path}"
                    else:
                        error_msg = "Submission unclear - no confirmation message found"
                        logger.warning(error_msg)
                        return False, error_msg
                else:
                    return False, "Submit button not found"

            except PlaywrightTimeout as e:
                logger.error(f"Timeout during application: {e}")
                return False, f"Timeout: {str(e)}"

            except Exception as e:
                logger.error(f"Application failed: {e}")

                # Take error screenshot
                try:
                    screenshot_path = f"screenshots/error_{job.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    Path("screenshots").mkdir(exist_ok=True)
                    page.screenshot(path=screenshot_path)
                    logger.info(f"Error screenshot saved: {screenshot_path}")
                except:
                    screenshot_path = None

                # Log failed application
                with get_db() as db:
                    application = Application(
                        job_id=job.id,
                        status=ApplicationStatus.FAILED,
                        error_message=str(e),
                        response_data={'screenshot': screenshot_path}
                    )
                    db.add(application)
                    db.commit()

                return False, f"Error: {str(e)}"

            finally:
                browser.close()
