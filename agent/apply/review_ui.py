"""
Manual review interface for job applications - shows preview in browser.
"""
import logging
import tempfile
from pathlib import Path
from typing import Dict

from playwright.sync_api import Page

from agent.storage.models import Job

logger = logging.getLogger(__name__)


def generate_review_html(job: Job, form_data: Dict, resume_contact: Dict) -> str:
    """Generate HTML for the review interface.

    Args:
        job: Job object
        form_data: Dictionary of form fields with questions and AI-generated answers
        resume_contact: Contact information from resume

    Returns:
        HTML string for the review page
    """
    # Build custom questions HTML
    questions_html = ""
    for field_id, field_info in form_data.items():
        question = field_info['question']
        answer = field_info['answer']
        field_type = field_info['type']

        if field_type == 'textarea':
            questions_html += f"""
            <div class="question">
                <label>{question}</label>
                <textarea id="{field_id}" rows="5">{answer}</textarea>
            </div>
            """
        elif field_type == 'text':
            questions_html += f"""
            <div class="question">
                <label>{question}</label>
                <input type="text" id="{field_id}" value="{answer}">
            </div>
            """
        elif field_type == 'select':
            questions_html += f"""
            <div class="question">
                <label>{question}</label>
                <input type="text" id="{field_id}" value="{answer}">
                <small>Selected option: {answer}</small>
            </div>
            """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Review Application - {job.title}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px 20px;
            }}

            .container {{
                max-width: 900px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }}

            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}

            .header h1 {{
                font-size: 28px;
                margin-bottom: 10px;
            }}

            .header p {{
                font-size: 16px;
                opacity: 0.95;
            }}

            .job-details {{
                background: #f8f9fa;
                padding: 25px 30px;
                border-bottom: 2px solid #e9ecef;
            }}

            .job-details h2 {{
                color: #333;
                margin-bottom: 15px;
                font-size: 22px;
            }}

            .detail-row {{
                display: flex;
                margin-bottom: 12px;
                font-size: 15px;
            }}

            .detail-label {{
                font-weight: 600;
                color: #495057;
                min-width: 140px;
            }}

            .detail-value {{
                color: #212529;
            }}

            .match-score {{
                background: #28a745;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                display: inline-block;
                font-weight: 600;
                font-size: 14px;
            }}

            .match-reason {{
                background: #e7f5ff;
                border-left: 4px solid #1971c2;
                padding: 15px;
                margin-top: 15px;
                border-radius: 4px;
                font-style: italic;
                color: #1864ab;
            }}

            .form-section {{
                padding: 30px;
            }}

            .form-section h3 {{
                color: #333;
                margin-bottom: 20px;
                font-size: 20px;
                border-bottom: 2px solid #e9ecef;
                padding-bottom: 10px;
            }}

            .standard-fields {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 25px;
            }}

            .standard-fields p {{
                margin: 8px 0;
                color: #495057;
            }}

            .standard-fields strong {{
                color: #212529;
            }}

            .question {{
                margin-bottom: 25px;
            }}

            .question label {{
                display: block;
                font-weight: 600;
                color: #495057;
                margin-bottom: 8px;
                font-size: 15px;
            }}

            .question textarea,
            .question input[type="text"] {{
                width: 100%;
                padding: 12px;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
                font-family: inherit;
                transition: border-color 0.2s;
            }}

            .question textarea:focus,
            .question input[type="text"]:focus {{
                outline: none;
                border-color: #667eea;
            }}

            .question small {{
                display: block;
                margin-top: 5px;
                color: #6c757d;
                font-size: 13px;
            }}

            .actions {{
                background: #f8f9fa;
                padding: 25px 30px;
                display: flex;
                gap: 15px;
                justify-content: center;
                border-top: 2px solid #e9ecef;
            }}

            .btn {{
                padding: 14px 40px;
                font-size: 16px;
                font-weight: 600;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            .btn-submit {{
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4);
            }}

            .btn-submit:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(40, 167, 69, 0.5);
            }}

            .btn-skip {{
                background: #6c757d;
                color: white;
                box-shadow: 0 4px 15px rgba(108, 117, 125, 0.3);
            }}

            .btn-skip:hover {{
                background: #5a6268;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(108, 117, 125, 0.4);
            }}

            .ai-badge {{
                background: #667eea;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                display: inline-block;
                margin-left: 10px;
            }}

            .empty-questions {{
                text-align: center;
                padding: 40px;
                color: #6c757d;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Review Job Application</h1>
                <p>Review and edit AI-generated responses before submitting</p>
            </div>

            <div class="job-details">
                <h2>{job.title}</h2>
                <div class="detail-row">
                    <span class="detail-label">Company:</span>
                    <span class="detail-value">{job.company}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Location:</span>
                    <span class="detail-value">{job.location or 'Not specified'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Match Score:</span>
                    <span class="detail-value"><span class="match-score">{job.match_score:.1%}</span></span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">ATS Platform:</span>
                    <span class="detail-value">{job.ats_type.value}</span>
                </div>
                {f'<div class="match-reason">{job.match_reason}</div>' if job.match_reason else ''}
            </div>

            <div class="form-section">
                <h3>Standard Fields (Auto-filled)</h3>
                <div class="standard-fields">
                    <p><strong>Name:</strong> {resume_contact.get('name', 'N/A')}</p>
                    <p><strong>Email:</strong> {resume_contact.get('email', 'N/A')}</p>
                    <p><strong>Phone:</strong> {resume_contact.get('phone', 'N/A')}</p>
                    <p><strong>Resume:</strong> PDF will be uploaded</p>
                </div>

                <h3>Custom Questions <span class="ai-badge">AI Generated</span></h3>
                {questions_html if questions_html else '<div class="empty-questions">No custom questions detected for this position.</div>'}
            </div>

            <div class="actions">
                <button class="btn btn-submit" onclick="submitApplication()">
                     Submit Application
                </button>
                <button class="btn btn-skip" onclick="skipApplication()">
                     Skip This Job
                </button>
            </div>
        </div>

        <script>
            // Store the user's decision
            window.userDecision = null;

            function submitApplication() {{
                // Update form data with edited values
                const updatedData = {{}};
                {_generate_update_script(form_data)}

                window.userDecision = {{
                    approved: true,
                    updatedData: updatedData
                }};

                // Change button to show submission
                const btn = document.querySelector('.btn-submit');
                btn.textContent = ' Submitting...';
                btn.style.background = '#6c757d';
                btn.disabled = true;
            }}

            function skipApplication() {{
                window.userDecision = {{
                    approved: false
                }};

                const btn = document.querySelector('.btn-skip');
                btn.textContent = ' Skipped';
                btn.disabled = true;
            }}
        </script>
    </body>
    </html>
    """
    return html


def _generate_update_script(form_data: Dict) -> str:
    """Generate JavaScript to collect updated form values."""
    script_lines = []
    for field_id in form_data.keys():
        script_lines.append(f"updatedData['{field_id}'] = document.getElementById('{field_id}')?.value || '';")
    return "\n                ".join(script_lines)


def show_review_ui(page: Page, form_data: Dict, job: Job, resume_contact: Dict) -> bool:
    """Show review UI in browser and wait for user decision.

    Args:
        page: Playwright page object (will open new tab)
        form_data: Form data with AI-generated answers
        job: Job object
        resume_contact: Contact information from resume

    Returns:
        True if approved, False if skipped
    """
    logger.info("Opening manual review UI in browser...")

    # Generate HTML
    html_content = generate_review_html(job, form_data, resume_contact)

    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_path = f.name

    try:
        # Open in new page
        context = page.context
        review_page = context.new_page()
        review_page.goto(f"file://{temp_path}")

        logger.info("Waiting for user decision...")

        # Wait for user to make a decision
        while True:
            decision = review_page.evaluate("window.userDecision")
            if decision is not None:
                approved = decision.get('approved', False)

                # Update form_data with edited values if approved
                if approved and 'updatedData' in decision:
                    for field_id, new_value in decision['updatedData'].items():
                        if field_id in form_data:
                            form_data[field_id]['answer'] = new_value

                review_page.close()

                logger.info(f"User decision: {'APPROVED' if approved else 'SKIPPED'}")
                return approved

            page.wait_for_timeout(500)  # Check every 500ms

    finally:
        # Clean up temp file
        try:
            Path(temp_path).unlink()
        except:
            pass
