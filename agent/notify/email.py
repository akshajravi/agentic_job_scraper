"""
Email notification service for job application updates.
"""
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from agent.config import settings
from agent.storage.models import Application, Job

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends email notifications about job applications."""

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        username: str = None,
        password: str = None,
        from_email: str = None,
        to_email: str = None
    ):
        """Initialize email notifier.

        Args:
            smtp_host: SMTP server host (default from settings)
            smtp_port: SMTP server port (default from settings)
            username: SMTP username (default from settings)
            password: SMTP password (default from settings)
            from_email: Sender email (default from settings)
            to_email: Recipient email (default from settings)
        """
        self.smtp_host = smtp_host or settings.email_host
        self.smtp_port = smtp_port or settings.email_port
        self.username = username or settings.email_user
        self.password = password or settings.email_password
        self.from_email = from_email or settings.email_user
        self.to_email = to_email or settings.email_to

    def _generate_summary_html(
        self,
        stats: Dict,
        matched_jobs: List[Job] = None,
        applied_jobs: List[tuple] = None
    ) -> str:
        """Generate HTML email content for job application summary.

        Args:
            stats: Dictionary with statistics (scraped, matched, applied, etc.)
            matched_jobs: List of matched Job objects
            applied_jobs: List of tuples (Job, Application, success, message)

        Returns:
            HTML string for email body
        """
        # Build matched jobs table
        matched_table = ""
        if matched_jobs:
            matched_table = """
            <h2 style="color: #333; margin-top: 30px;">Top Matched Jobs</h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Company</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Title</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Location</th>
                        <th style="padding: 12px; text-align: center; border: 1px solid #dee2e6;">Match</th>
                    </tr>
                </thead>
                <tbody>
            """
            for job in matched_jobs[:10]:  # Top 10
                match_color = "#28a745" if job.match_score >= 0.8 else "#ffc107" if job.match_score >= 0.7 else "#6c757d"
                matched_table += f"""
                    <tr>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{job.company}</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{job.title}</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{job.location or 'Remote'}</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; text-align: center;">
                            <span style="background: {match_color}; color: white; padding: 4px 10px; border-radius: 12px; font-weight: 600;">
                                {job.match_score:.1%}
                            </span>
                        </td>
                    </tr>
                """
            matched_table += """
                </tbody>
            </table>
            """

        # Build applications table
        applications_table = ""
        if applied_jobs:
            applications_table = """
            <h2 style="color: #333; margin-top: 30px;">Application Results</h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Company</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Title</th>
                        <th style="padding: 12px; text-align: center; border: 1px solid #dee2e6;">Status</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Message</th>
                    </tr>
                </thead>
                <tbody>
            """
            for job, application, success, message in applied_jobs:
                status_badge = " Success" if success else " Failed"
                status_color = "#28a745" if success else "#dc3545"
                applications_table += f"""
                    <tr>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{job.company}</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{job.title}</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; text-align: center;">
                            <span style="background: {status_color}; color: white; padding: 4px 10px; border-radius: 12px; font-weight: 600;">
                                {status_badge}
                            </span>
                        </td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; font-size: 13px; color: #6c757d;">
                            {message[:100]}...
                        </td>
                    </tr>
                """
            applications_table += """
                </tbody>
            </table>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5;">
            <div style="max-width: 800px; margin: 40px auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px;">Job Application Report</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>

                <!-- Stats -->
                <div style="padding: 30px;">
                    <h2 style="color: #333; margin-bottom: 20px;">Summary</h2>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                            <div style="font-size: 32px; font-weight: bold; color: #667eea;">{stats.get('scraped', 0)}</div>
                            <div style="color: #6c757d; margin-top: 5px;">Jobs Scraped</div>
                        </div>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
                            <div style="font-size: 32px; font-weight: bold; color: #28a745;">{stats.get('matched', 0)}</div>
                            <div style="color: #6c757d; margin-top: 5px;">Jobs Matched</div>
                        </div>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #17a2b8;">
                            <div style="font-size: 32px; font-weight: bold; color: #17a2b8;">{stats.get('applied', 0)}</div>
                            <div style="color: #6c757d; margin-top: 5px;">Applications Sent</div>
                        </div>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
                            <div style="font-size: 32px; font-weight: bold; color: #28a745;">{stats.get('successful', 0)}</div>
                            <div style="color: #6c757d; margin-top: 5px;">Successful</div>
                        </div>
                    </div>

                    {matched_table}
                    {applications_table}
                </div>

                <!-- Footer -->
                <div style="background: #f8f9fa; padding: 20px 30px; text-align: center; border-top: 1px solid #dee2e6;">
                    <p style="margin: 0; color: #6c757d; font-size: 14px;">
                        Generated by Agentic Job Scraper
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def send_summary(
        self,
        stats: Dict,
        matched_jobs: List[Job] = None,
        applied_jobs: List[tuple] = None
    ) -> bool:
        """Send email summary of job application run.

        Args:
            stats: Dictionary with statistics
            matched_jobs: List of matched Job objects
            applied_jobs: List of tuples (Job, Application, success, message)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not all([self.smtp_host, self.smtp_port, self.username, self.password, self.to_email]):
            logger.warning("Email credentials not configured - skipping notification")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Job Application Report - {stats.get('applied', 0)} Applications Sent"
            msg['From'] = self.from_email
            msg['To'] = self.to_email

            # Generate HTML body
            html_body = self._generate_summary_html(stats, matched_jobs, applied_jobs)
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Send email
            logger.info(f"Sending email to {self.to_email}...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info("Email sent successfully!")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


def send_summary_email(
    stats: Dict,
    matched_jobs: List[Job] = None,
    applied_jobs: List[tuple] = None
) -> bool:
    """Convenience function to send summary email.

    Args:
        stats: Dictionary with statistics
        matched_jobs: List of matched Job objects
        applied_jobs: List of tuples (Job, Application, success, message)

    Returns:
        True if email sent successfully, False otherwise
    """
    notifier = EmailNotifier()
    return notifier.send_summary(stats, matched_jobs, applied_jobs)
