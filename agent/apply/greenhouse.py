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
        
        Also extracts answers from resume data where applicable (school, linkedin, etc.)
        
        Args:
            question: The question text from the application form.
            
        Returns:
            Predetermined answer if pattern matches, None otherwise.
        """
        question_lower = question.lower()
        
        # Check for resume data fields first (higher priority)
        if "school" in question_lower and "high" not in question_lower:
            school = self.resume_data.education.get('school')
            if school:
                logger.info(f"✓ Using school from resume: {school}")
                return school
        
        if "linkedin" in question_lower:
            linkedin = self.resume_data.contact.get('linkedin', '')
            if linkedin:
                logger.info(f"✓ Using LinkedIn from resume: {linkedin}")
                return linkedin
            else:
                logger.info("✓ No LinkedIn in resume, leaving blank")
                return ""  # Return empty string to skip this field
        
        if "website" in question_lower or "personal site" in question_lower:
            website = self.resume_data.contact.get('website', '')
            if website:
                logger.info(f"✓ Using website from resume: {website}")
                return website
            else:
                logger.info("✓ No website in resume, leaving blank")
                return ""  # Return empty string to skip this field
        
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

    def _answer_for_select_field(self, question: str, options: List[str]) -> Optional[str]:
        """Smart answer selection for dropdown/select fields.
        
        Tries to match options based on predetermined patterns and resume data
        without using OpenAI.
        
        Args:
            question: The question text
            options: List of available options in the dropdown
            
        Returns:
            Selected option, or None if we need OpenAI
        """
        if not options:
            return None
            
        question_lower = question.lower()
        
        # Country - look for United States variations
        if "country" in question_lower:
            for opt in options:
                if "united states" in opt.lower() or opt.lower() in ["us", "usa", "u.s.", "u.s.a."]:
                    logger.info(f"✓ Selected country: {opt}")
                    return opt
        
        # School - use from resume if it matches
        if "school" in question_lower and "high" not in question_lower:
            school = self.resume_data.education.get('school', '')
            if school:
                for opt in options:
                    if school.lower() in opt.lower() or opt.lower() in school.lower():
                        logger.info(f"✓ Selected school from resume: {opt}")
                        return opt
        
        # Clearance questions
        if "clearance" in question_lower:
            # Look for "No" or "None" options first
            for opt in options:
                if opt.lower() in ["no", "none", "no clearance", "n/a", "not applicable"]:
                    logger.info(f"✓ Selected clearance option: {opt}")
                    return opt
            # If asking about eligibility, look for Yes/Eligible
            if "eligible" in question_lower or "eligibility" in question_lower:
                for opt in options:
                    if "yes" in opt.lower() or "eligible" in opt.lower():
                        logger.info(f"✓ Selected clearance eligibility: {opt}")
                        return opt
        
        # Gender/Demographics - look for "Decline" option
        if any(word in question_lower for word in ["gender", "race", "ethnicity", "veteran", "disability"]):
            for opt in options:
                if "decline" in opt.lower() or "prefer not" in opt.lower():
                    logger.info(f"✓ Selected demographic option: {opt}")
                    return opt
        
        # Yes/No questions - use predetermined answer logic
        predetermined = self._check_predetermined_answer(question)
        if predetermined:
            # Try to find matching option
            for opt in options:
                if predetermined.lower() in opt.lower() or opt.lower() in predetermined.lower():
                    logger.info(f"✓ Matched option '{opt}' for predetermined answer '{predetermined}'")
                    return opt
            # Try exact Yes/No match
            if predetermined.lower() == "yes":
                for opt in options:
                    if opt.lower() in ["yes", "y"]:
                        return opt
            elif predetermined.lower() == "no":
                for opt in options:
                    if opt.lower() in ["no", "n"]:
                        return opt
        
        return None  # Need OpenAI for this one

    def _answer_custom_question(self, question: str, field_type: str = "text", options: Optional[List[str]] = None) -> str:
        """Generate an answer to a custom application question.

        High-level: 
        1. First checks if question matches a predetermined answer pattern (e.g., "conflicts", "worked here before")
        2. For select/dropdown fields, tries to intelligently pick from available options
        3. Only uses OpenAI for creative/personalized free-response questions
        
        This approach significantly reduces API costs by avoiding unnecessary calls.

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

        # STEP 2: For select/dropdown fields, try to pick from options intelligently
        if field_type == "select" and options:
            logger.info(f"Select field with {len(options)} options: {options[:5]}{'...' if len(options) > 5 else ''}")
            smart_answer = self._answer_for_select_field(question, options)
            if smart_answer:
                logger.info(f"✓ Smart selection: '{smart_answer}' (saved API call)")
                return smart_answer
            else:
                logger.info("Could not determine selection, falling back to OpenAI...")

        # STEP 3: Use OpenAI for creative/personalized questions
        logger.info("Using OpenAI API for personalized answer")
        
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

    def _fill_fake_dropdown(self, page: Page, selector: str, answer: str, options: List[str]) -> bool:
        """Fill a Greenhouse fake dropdown (text input with JS menu).
        
        Greenhouse uses custom dropdowns that look like regular select elements
        but are actually text inputs with JavaScript-powered menus. This method:
        1. Clicks the field to open the dropdown menu
        2. Waits for menu options to appear
        3. Clicks the correct option
        
        Args:
            page: Playwright page object
            selector: CSS selector for the dropdown field
            answer: The option text to select
            options: List of available options (may be empty, we'll find them dynamically)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Find the hidden input field
            field = page.locator(selector).first
            if field.count() == 0:
                logger.warning(f"Field not found: {selector}")
                return False
            
            field_id = field.get_attribute('id') or ''
            logger.info(f"Found field with id: {field_id}")
            
            # Special handling for searchable dropdowns (like School)
            # These allow typing to filter options
            if any(keyword in field_id.lower() for keyword in ['school', 'university', 'college']):
                logger.info("Detected searchable dropdown (school), typing to search...")
                try:
                    field.fill(answer)
                    time.sleep(0.5)  # Wait for search results
                    # Try to click the first matching option
                    first_option = page.locator('[role="option"]').first
                    if first_option.count() > 0:
                        first_option.click()
                        logger.info(f"✓ Successfully selected from searchable dropdown")
                        return True
                except Exception as e:
                    logger.warning(f"Searchable dropdown failed: {e}, falling back to click method...")
            
            # Step 2: Find the clickable element that opens the dropdown
            # For Greenhouse, the safest approach is to click the input field itself
            # since it has event listeners that open the dropdown
            clickable = field
            logger.info(f"Using input field itself as clickable element")
            
            # But also try to find a more specific clickable container if possible
            # This helps with some Greenhouse variations
            if field_id:
                # Look for parent container that wraps the input
                try:
                    parent = page.locator(f'#{field_id}').locator('xpath=..').first
                    if parent.count() > 0:
                        parent_class = parent.get_attribute('class') or ''
                        # If parent has select/control classes, it's likely the better target
                        if 'control' in parent_class.lower() or 'wrapper' in parent_class.lower():
                            # But only if it's not a placeholder or input container
                            if 'placeholder' not in parent_class.lower() and 'input-container' not in parent_class.lower():
                                clickable = parent
                                logger.info(f"Using parent container as clickable element")
                except:
                    pass
            
            # Step 3: Click to open the dropdown menu
            logger.info(f"Clicking dropdown to open menu...")
            clickable.scroll_into_view_if_needed()
            
            # Try regular click first
            try:
                clickable.click(timeout=5000)
            except Exception as click_error:
                # If regular click fails (element intercepted), try force click with JavaScript
                logger.info("  Regular click intercepted, trying JavaScript click...")
                try:
                    clickable.evaluate('el => el.click()')
                except:
                    # Last resort: click the input field directly
                    logger.info("  Trying to click input field directly...")
                    field.evaluate('el => el.click()')
            
            # Step 4: Wait for menu to appear
            time.sleep(0.8)  # Give time for menu animation and rendering
            
            # Step 5: Find the specific menu for this dropdown using aria-controls
            menu_id = field.get_attribute('aria-controls') or ''
            logger.info(f"Looking for menu with aria-controls: '{menu_id}'")
            
            # Build selectors that target ONLY this dropdown's menu
            if menu_id:
                menu_selector = f'#{menu_id}'
            else:
                # Fallback: look for visible menu with select__menu-list class (Greenhouse pattern)
                menu_selector = '.select__menu-list:visible, [role="listbox"]:visible'
            
            # Step 6: Find and click the correct option WITHIN the specific menu
            logger.info(f"Looking for option: '{answer}'")
            
            # Try exact match first (within the specific menu)
            option_selectors = [
                f'{menu_selector} [role="option"]:has-text("{answer}")',
                f'{menu_selector} div:has-text("{answer}")',
                f'{menu_selector} >> text="{answer}"',
            ]
            
            clicked = False
            for option_selector in option_selectors:
                try:
                    option_element = page.locator(option_selector).first
                    if option_element.count() > 0 and option_element.is_visible():
                        logger.info(f"Found option with selector: {option_selector}")
                        option_element.click()
                        clicked = True
                        time.sleep(0.4)  # Wait for selection to register
                        break
                except Exception as e:
                    logger.debug(f"Selector {option_selector} failed: {e}")
                    continue
            
            if not clicked:
                # Try fuzzy matching - look for any option WITHIN THIS MENU that contains our answer
                logger.info(f"Exact match not found, trying fuzzy match within menu...")
                
                # Get all options from the specific menu only
                try:
                    menu_options = page.locator(f'{menu_selector} [role="option"]').all()
                    logger.info(f"Found {len(menu_options)} options in menu '{menu_id or menu_selector}'")
                    
                    for opt in menu_options:
                        try:
                            opt_text = opt.inner_text().strip()
                            if not opt_text:
                                continue
                            
                            # Normalize both strings for comparison (lowercase, remove extra spaces/punctuation)
                            norm_answer = answer.lower().replace('-', ' ').replace('_', ' ')
                            norm_opt = opt_text.lower().replace('-', ' ').replace('_', ' ')
                            
                            # Check for fuzzy matches
                            if (norm_answer in norm_opt or 
                                norm_opt in norm_answer or
                                # Also check if most words match
                                len([w for w in norm_answer.split() if w in norm_opt.split()]) >= min(3, len(norm_answer.split()) - 1)):
                                logger.info(f"Fuzzy matched: '{opt_text}'")
                                opt.click()
                                clicked = True
                                time.sleep(0.4)
                                break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Error during fuzzy matching: {e}")
            
            if clicked:
                logger.info(f"✓ Successfully selected: {answer}")
                
                # Wait a moment for the dropdown to close and update
                time.sleep(0.5)
                
                # CRITICAL: Manually set the input value to ensure it's saved
                # Some Greenhouse dropdowns don't update the input value automatically
                try:
                    field.fill(answer)
                    logger.info(f"  Manually set field value to: '{answer}'")
                except:
                    pass
                
                # Trigger change/blur events to ensure Greenhouse registers the selection
                try:
                    field.evaluate('''(el) => {
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    }''')
                    time.sleep(0.3)  # Give JavaScript time to process
                except:
                    pass
                
                # Verify the selection stuck by checking the field value
                try:
                    current_value = field.input_value() or field.inner_text()
                    aria_expanded = field.get_attribute('aria-expanded')
                    if current_value:
                        logger.info(f"  Field value after selection: '{current_value[:50]}'")
                    if aria_expanded == 'false' or not aria_expanded:
                        logger.info(f"  Dropdown closed successfully")
                except:
                    pass
                
                return True
            else:
                logger.warning(f"Could not find option '{answer}' in menu")
                # Log available options for debugging (from the correct menu only)
                try:
                    menu_options = page.locator(f'{menu_selector} [role="option"]').all()
                    if menu_options:
                        option_texts = [opt.inner_text().strip() for opt in menu_options[:10] if opt.inner_text().strip()]
                        logger.info(f"Available options in menu (first 10): {option_texts}")
                except:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"Failed to fill fake dropdown: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _is_fake_dropdown_input(self, input_element, page: Page) -> bool:
        """Check if a text input is actually a fake dropdown.
        
        Greenhouse fake dropdowns are visible text inputs that:
        - Have readonly or aria-readonly attributes
        - Have role="combobox" or aria-haspopup
        - Have an adjacent dropdown arrow/button
        - Are styled to look like dropdowns
        
        Args:
            input_element: The input element to check
            page: Playwright page object
            
        Returns:
            True if it's a fake dropdown, False otherwise
        """
        try:
            input_id = input_element.get_attribute('id') or ''
            
            # Check for dropdown indicators
            readonly = input_element.get_attribute('readonly')
            aria_readonly = input_element.get_attribute('aria-readonly')
            role = input_element.get_attribute('role')
            aria_haspopup = input_element.get_attribute('aria-haspopup')
            
            # If it has dropdown-related attributes, it's a fake dropdown
            if role == 'combobox' or aria_haspopup == 'listbox':
                return True
            if readonly is not None or aria_readonly == 'true':
                return True
            
            # Check if there's a dropdown arrow/button next to it
            if input_id:
                # Look for adjacent dropdown indicators (common Greenhouse patterns)
                adjacent_dropdown = page.locator(f'''
                    #{input_id} ~ button[aria-label*="toggle"],
                    #{input_id} ~ div[class*="arrow"],
                    #{input_id} + div[class*="arrow"],
                    #{input_id} ~ svg
                ''').first
                if adjacent_dropdown.count() > 0:
                    return True
                
                # Check if wrapped in a container with dropdown classes
                parent = page.locator(f'#{input_id}').locator('xpath=..').first
                if parent.count() > 0:
                    parent_class = parent.get_attribute('class') or ''
                    if any(cls in parent_class.lower() for cls in ['select', 'dropdown', 'combobox']):
                        return True
            
            return False
        except:
            return False

    def _detect_custom_questions(self, page: Page) -> List[Dict[str, str]]:
        """Detect custom questions in the Greenhouse application form.

        Args:
            page: Playwright page object

        Returns:
            List of dictionaries with question details
        """
        questions = []
        processed_labels = set()  # Track which labels we've already used

        # Look for REAL select dropdowns FIRST (highest priority - they're most structured)
        # These are rare in modern Greenhouse but some forms still use them
        selects = page.locator('select').all()
        logger.info(f"Found {len(selects)} select elements on page")
        
        for select in selects:
            select_id = select.get_attribute('id') or ''
            select_name = select.get_attribute('name') or ''

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
                processed_labels.add(label_text.lower())  # Mark this label as processed
                logger.info(f"  Added SELECT: {label_text[:40]}...")
            else:
                logger.info(f"  Skipping select (id={select_id}, no valid label)")

        # Look for text inputs (may be real text fields OR fake dropdowns)
        standard_fields = ['first_name', 'last_name', 'email', 'phone']
        text_inputs = page.locator('input[type="text"], input[type="url"]').all()
        logger.info(f"Found {len(text_inputs)} text inputs on page")

        for input_elem in text_inputs:
            input_id = input_elem.get_attribute('id') or ''
            input_name = input_elem.get_attribute('name') or ''

            # Skip standard fields
            if any(field in input_id.lower() or field in input_name.lower() for field in standard_fields):
                continue

            # Try to find associated label
            label_text = ""
            try:
                if input_id:
                    label = page.locator(f'label[for="{input_id}"]').first
                    if label.count() > 0:
                        label_text = label.inner_text().strip()
            except:
                pass

            # Skip if we already processed this label
            if label_text and len(label_text) > 5 and label_text.lower() not in processed_labels:
                # Check if this is actually a fake dropdown
                is_fake_dropdown = self._is_fake_dropdown_input(input_elem, page)
                
                if is_fake_dropdown:
                    # It's a fake dropdown - mark it as select type
                    logger.info(f"  Detected FAKE DROPDOWN (text input styled as dropdown): {label_text[:50]}...")
                    questions.append({
                        'type': 'select',
                        'question': label_text,
                        'selector': f'#{input_id}' if input_id else f'[name="{input_name}"]',
                        'id': input_id or input_name,
                        'options': [],  # Will be populated dynamically when clicked
                        'is_fake_dropdown': True
                    })
                else:
                    # It's a real text input
                    logger.info(f"  Detected TEXT INPUT: {label_text[:50]}...")
                    questions.append({
                        'type': 'text',
                        'question': label_text,
                        'selector': f'#{input_id}' if input_id else f'[name="{input_name}"]',
                        'id': input_id or input_name
                    })
                processed_labels.add(label_text.lower())

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

            # Skip if we already processed this label
            if label_text and len(label_text) > 5 and label_text.lower() not in processed_labels:
                questions.append({
                    'type': 'textarea',
                    'question': label_text,
                    'selector': f'#{textarea_id}' if textarea_id else f'[name="{textarea_name}"]',
                    'id': textarea_id or textarea_name
                })
                processed_labels.add(label_text.lower())

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
            email_input = page.locator('input[type="email"], input[name*="email"], input[id*="email"]').first
            if email_input.count() > 0:
                email = contact.get('email', settings.email_user or settings.email_address or '')
                if email:
                    email_input.fill(email)
                    logger.info(f"Filled email: {email}")
                else:
                    logger.warning("No email found in resume or settings!")
            else:
                logger.warning("Email field not found on page")

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

                # Wait for custom questions to load (Greenhouse loads them dynamically)
                logger.info("Waiting for custom questions to load...")
                time.sleep(3)  # Give time for JavaScript to render dropdowns
                
                # DEBUG: Dump all form elements to understand structure
                element_info = page.evaluate("""() => {
                    const allInputs = Array.from(document.querySelectorAll('input, select, textarea'));
                    return allInputs.map(el => ({
                        tag: el.tagName,
                        type: el.type,
                        id: el.id,
                        name: el.name,
                        visible: el.offsetHeight > 0
                    }));
                }""")
                import json
                with open('element_debug.json', 'w') as f:
                    json.dump(element_info, f, indent=2)
                logger.info(f"Dumped {len(element_info)} elements to element_debug.json")
                logger.info(f"SELECT elements: {len([e for e in element_info if e['tag'] == 'SELECT'])}")
                
                # Detect custom questions
                custom_questions = self._detect_custom_questions(page)

                # Process and fill each question immediately (like Simplify does)
                form_data = {}  # Still track for review UI and database
                for question_info in custom_questions:
                    logger.info(f"Processing field: {question_info['question'][:60]}...")
                    
                    # Generate answer
                    answer = self._answer_custom_question(
                        question=question_info['question'],
                        field_type=question_info['type'],
                        options=question_info.get('options') if isinstance(question_info, dict) else None,
                    )
                    
                    # Skip empty optional fields
                    if not answer:
                        logger.info("  → Skipping (no answer)")
                        continue
                    
                    # Fill the field immediately
                    try:
                        element = page.locator(question_info['selector']).first
                        if element.count() > 0:
                            if question_info['type'] in ['text', 'textarea']:
                                element.fill(answer)
                                logger.info(f"  → Filled text field")
                            elif question_info['type'] == 'select':
                                # Detect if it's a real select or a fake Greenhouse dropdown
                                tag_name = element.evaluate('el => el.tagName').lower()
                                input_type = element.get_attribute('type') or ''
                                
                                # Check if marked as fake dropdown during detection OR if it's not a real select element
                                is_fake_dropdown = (
                                    question_info.get('is_fake_dropdown', False) or
                                    tag_name == 'input' or 
                                    input_type == 'hidden' or
                                    element.evaluate('el => el.style.display === "none"')
                                )
                                
                                if is_fake_dropdown:
                                    # Use our special fake dropdown handler
                                    logger.info(f"  → Detected fake dropdown, using click method...")
                                    success = self._fill_fake_dropdown(
                                        page=page,
                                        selector=question_info['selector'],
                                        answer=answer,
                                        options=question_info.get('options', [])
                                    )
                                    if not success:
                                        logger.warning(f"  → Failed to select from fake dropdown")
                                else:
                                    # Real select element - use standard method
                                    logger.info(f"  → Real select element, using select_option...")
                                    try:
                                        element.select_option(label=answer)
                                        logger.info(f"  → Selected: {answer}")
                                    except Exception as select_error:
                                        # If exact match fails, try "Other" as fallback
                                        logger.info(f"  → Option '{answer}' not found, trying 'Other'...")
                                        try:
                                            element.select_option(label="Other")
                                            logger.info("  → Selected 'Other' as fallback")
                                        except:
                                            # Try case-insensitive match for "other"
                                            options_list = element.locator('option').all_inner_texts()
                                            other_option = next((opt for opt in options_list if 'other' in opt.lower()), None)
                                            if other_option:
                                                element.select_option(label=other_option)
                                                logger.info(f"  → Selected '{other_option}' as fallback")
                                            else:
                                                raise select_error
                            
                            # Store for review UI and database
                            form_data[question_info['id']] = {
                                'question': question_info['question'],
                                'answer': answer,
                                'selector': question_info['selector'],
                                'type': question_info['type']
                            }
                        else:
                            logger.warning(f"  → Element not found: {question_info['selector']}")
                    except Exception as e:
                        logger.warning(f"  → Could not fill field: {e}")

                # Manual review if requested (fields are already filled, user can review the page)
                if manual_review and review_callback:
                    logger.info("All fields filled. Requesting manual review before submission...")
                    approved = review_callback(page, form_data, job)

                    if not approved:
                        logger.info("Application skipped by user")
                        return False, "Skipped by user during manual review"

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
