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
from agent.storage.db import get_db
from agent.storage.models import Application, ApplicationStatus, Job, JobStatus, ResumeData

logger = logging.getLogger(__name__)


class GreenhouseApplier:
    """Automates job applications on Greenhouse ATS platform."""

    def __init__(
        self,
        resume_data: ResumeData,
        resume_pdf_path: str | Path,
        headless: bool = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize Greenhouse applier.

        Args:
            resume_data: Parsed resume data
            resume_pdf_path: Path to resume PDF file for upload
            headless: Run browser in headless mode (default from settings)
            openai_api_key: OpenAI API key for answering custom questions
        """
        self.resume_data = resume_data
        self.resume_pdf_path = Path(resume_pdf_path)
        self.headless = headless if headless is not None else settings.headless
        self.openai_client = OpenAI(api_key=openai_api_key or settings.openai_api_key)

        if not self.resume_pdf_path.exists():
            raise FileNotFoundError(f"Resume PDF not found: {self.resume_pdf_path}")

    def _check_predetermined_answer(self, question: str) -> Optional[str]:
        """Check if question matches a predetermined answer pattern.
        
        This avoids unnecessary OpenAI API calls for simple yes/no questions
        like "Do you have any conflicts?" or "Have you worked here before?"
        
        Args:
            question: The question text from the application form.
            
        Returns:
            Predetermined answer if pattern matches, None otherwise.
        """
        question_lower = question.lower()
        
        # Check each predetermined answer pattern
        for pattern, answer in settings.predetermined_answers.items():
            if pattern.lower() in question_lower:
                logger.info(f"✓ Matched predetermined answer for '{pattern}': {answer}")
                return answer
        
        return None

    def _build_custom_answer_messages(
        self,
        question: str,
        resume_context: str,
        field_type: str,
        options: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """Build chat messages for answering a custom application question.

        Args:
            question: The question text from the application form.
            resume_context: Brief, structured resume context for grounding.
            field_type: Field type (e.g., "text", "textarea", "select", "yesno").
            options: Optional list of allowed options for select fields.

        Returns:
            Messages formatted for chat completion API.
        """
        # Field-specific guidance
        length_rules = (
            "If the question is yes/no, answer strictly 'Yes' or 'No'. "
            "For short text fields, keep answers under 100 words. "
            "For longer text fields (cover-letter style), write 200-300 words."
        )

        if field_type.lower() in {"yesno", "yes_no", "boolean"}:
            length_rules = "Answer strictly 'Yes' or 'No'."
        elif field_type.lower() in {"text"}:
            length_rules = "Keep the answer under 100 words."
        elif field_type.lower() in {"textarea", "longtext", "long_text"}:
            length_rules = "Write 200-300 words, concise and focused."
        elif field_type.lower() in {"select", "dropdown"}:
            if options:
                # Constrain output to exactly one of the provided options
                joined = ", ".join(options)
                length_rules = (
                    "Return exactly one of the provided options verbatim with no extra text: "
                    f"{joined}."
                )
            else:
                length_rules = "Return a concise option label with no extra text."

        # Core style and grounding guidance
        system_content = (
            "You are helping fill out a job application. Use a neutral, professional tone "
            "with light humanization: use contractions, vary sentence length, avoid clichés "
            "and generic openers, and prefer concrete specifics grounded in the resume. "
            "Be honest and grounded: do not fabricate facts. If the resume lacks a detail, "
            "you may lightly extrapolate to keep flow using brief qualifiers such as 'not "
            "specified in my resume' or 'typically', but do not invent dates, numbers, or "
            "employers. "
            + length_rules
        )

        user_content = (
            f"Resume Context:\n{resume_context}\n\n"
            f"Question: {question}\n\n"
            "Provide a professional answer suitable for a job application."
        )

        # If options are present, include them in user message for visibility
        if field_type.lower() in {"select", "dropdown"} and options:
            user_content += "\nOptions (choose exactly one, return only the option text):\n- " + "\n- ".join(options)

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _answer_custom_question(self, question: str, field_type: str = "text", options: Optional[List[str]] = None) -> str:
        """Generate an answer to a custom application question.

        High-level: 
        1. First checks if question matches a predetermined answer pattern (e.g., "conflicts", "worked here before")
        2. If no match, uses OpenAI to generate a creative, personalized answer
        
        This approach significantly reduces API costs by avoiding unnecessary calls for simple questions.

        Args:
            question: The question text.
            field_type: Type of form field (e.g., "text", "textarea", "select").
            options: Optional list of options (for select/dropdown fields).

        Returns:
            Generated answer string suitable for direct form filling.
        """
        logger.info(f"Processing question: {question}")

        # STEP 1: Check for predetermined answers first (no API call needed!)
        predetermined = self._check_predetermined_answer(question)
        if predetermined:
            logger.info(f"Using predetermined answer: {predetermined} (saved API call)")
            return predetermined

        # STEP 2: Use OpenAI for creative/personalized questions
        logger.info("No predetermined answer found - using OpenAI API")
        
        resume_context = f"""
Name: {self.resume_data.contact.get('name', 'Unknown')}
Skills: {', '.join(self.resume_data.skills[:15])}
Latest Experience: {self.resume_data.experiences[0] if self.resume_data.experiences else 'N/A'}
Education: {self.resume_data.education.get('degree', 'N/A')} from {self.resume_data.education.get('school', 'N/A')}
"""

        try:
            messages = self._build_custom_answer_messages(
                question=question,
                resume_context=resume_context,
                field_type=field_type,
                options=options,
            )

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.5,
                max_tokens=400
            )

            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated answer via OpenAI (length: {len(answer)} chars)")
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
            contact = self.resume_data.contact

            # First name
            first_name_input = page.locator('input[name*="first_name"], input[id*="first_name"]').first
            if first_name_input.count() > 0:
                first_name = contact.get('name', '').split()[0] if contact.get('name') else ''
                first_name_input.fill(first_name)
                logger.info(f"Filled first name: {first_name}")

            # Last name
            last_name_input = page.locator('input[name*="last_name"], input[id*="last_name"]').first
            if last_name_input.count() > 0:
                last_name = ' '.join(contact.get('name', '').split()[1:]) if contact.get('name') else ''
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

            # Resume upload
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
                        question=question_info['question'],
                        field_type=question_info['type'],
                        options=question_info.get('options') if isinstance(question_info, dict) else None,
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
                                # Smart selection: try exact match first, then fallback to "Other"
                                try:
                                    element.select_option(label=field_data['answer'])
                                    logger.info(f"Selected option: {field_data['answer']}")
                                except Exception as select_error:
                                    # If exact match fails (e.g., "Corporate Website" not in options)
                                    # Try "Other" as fallback
                                    logger.info(f"Option '{field_data['answer']}' not found, trying 'Other'...")
                                    try:
                                        element.select_option(label="Other")
                                        logger.info("Selected 'Other' as fallback")
                                    except:
                                        # Try case-insensitive match for "other"
                                        options = element.locator('option').all_inner_texts()
                                        other_option = next((opt for opt in options if 'other' in opt.lower()), None)
                                        if other_option:
                                            element.select_option(label=other_option)
                                            logger.info(f"Selected '{other_option}' as fallback")
                                        else:
                                            raise select_error  # Re-raise if no fallback found
                            logger.info(f"Filled custom field: {field_data['question'][:50]}...")
                    except Exception as e:
                        logger.warning(f"Could not fill field {field_id}: {e}")

                # Check for validation errors before submitting
                error_messages = page.locator('.error, .field-error, [class*="error"], [role="alert"]').all_inner_texts()
                if error_messages:
                    logger.warning(f"Found validation errors before submission: {error_messages}")
                
                # Submit the application
                submit_button = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
                if submit_button.count() > 0:
                    logger.info("Submitting application...")
                    
                    # Take screenshot before submission
                    pre_submit_path = f"screenshots/pre_submit_{job.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    Path("screenshots").mkdir(exist_ok=True)
                    page.screenshot(path=pre_submit_path)
                    logger.info(f"Pre-submission screenshot: {pre_submit_path}")
                    
                    submit_button.click()

                    # Wait for confirmation or error (increased wait time)
                    time.sleep(5)
                    
                    # Take screenshot after submission
                    post_submit_path = f"screenshots/post_submit_{job.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    page.screenshot(path=post_submit_path)
                    logger.info(f"Post-submission screenshot: {post_submit_path}")

                    # Check for error messages
                    error_messages = page.locator('.error, .field-error, [class*="error"], [role="alert"]').all_inner_texts()
                    if error_messages:
                        logger.error(f"Form validation errors: {error_messages}")
                        return False, f"Form validation errors: {'; '.join(error_messages)}"

                    # Check for success message
                    success_indicators = [
                        'Thank you', 'submitted', 'received', 'confirmation',
                        'We\'ll be in touch', 'Application complete', 'application has been',
                        'successfully submitted', 'we received your application'
                    ]

                    page_text = page.inner_text('body').lower()
                    logger.info(f"Page text after submission (first 500 chars): {page_text[:500]}")
                    
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
