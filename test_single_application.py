#!/usr/bin/env python3
"""
Test script to apply to a single job.

This script helps test the application system by selecting one job
from the database and running through the entire application process.
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

from agent.apply.greenhouse import GreenhouseApplier
from agent.apply.review_ui import show_review_ui
from agent.config import settings
from agent.match.resume_parser import parse_resume
from agent.storage.db import get_db, init_db
from agent.storage.models import Job, ATSType

# Initialize Rich console
console = Console()

# Configure logging with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
logger = logging.getLogger(__name__)


def main():
    """Test application to a single job."""
    parser = argparse.ArgumentParser(
        description="Test application to a single Greenhouse job"
    )
    parser.add_argument(
        "--manual-review",
        action="store_true",
        help="Enable manual review before submission"
    )
    parser.add_argument(
        "--job-id",
        type=int,
        help="Specific job ID to apply to (optional)"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts"
    )
    args = parser.parse_args()

    # Initialize database
    init_db()

    # Check for resume
    resume_path = Path("resume.pdf")
    if not resume_path.exists():
        console.print("[red]Error: resume.pdf not found in current directory[/red]")
        sys.exit(1)

    # Header
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Single Job Application Test[/bold cyan]\n"
        "Testing the application system with one Greenhouse job",
        border_style="cyan"
    ))
    console.print("\n")

    # Get a single Greenhouse job
    with get_db() as db:
        if args.job_id:
            # Get specific job by ID
            job = db.query(Job).filter(
                Job.id == args.job_id,
                Job.ats_type == ATSType.GREENHOUSE
            ).first()
            if not job:
                console.print(f"[red]Job ID {args.job_id} not found or is not a Greenhouse job[/red]")
                sys.exit(1)
        else:
            # Get first Greenhouse job with match score
            job = db.query(Job).filter(
                Job.ats_type == ATSType.GREENHOUSE,
                Job.match_score.isnot(None)
            ).order_by(Job.match_score.desc()).first()

            if not job:
                console.print("[yellow]No Greenhouse jobs found with match scores[/yellow]")
                console.print("[yellow]Trying to find any Greenhouse job...[/yellow]")
                job = db.query(Job).filter(Job.ats_type == ATSType.GREENHOUSE).first()

            if not job:
                console.print("[red]No Greenhouse jobs found in database[/red]")
                sys.exit(1)

        # Load all job attributes before exiting session (to avoid detached instance error)
        job_id = job.id
        job_title = job.title
        job_company = job.company
        job_location = job.location
        job_match_score = job.match_score
        job_status = job.status.value
        job_url = job.url
        job_description = job.description
        job_requirements = job.requirements
        
        # Display job details
        console.print(Panel(
            f"[bold]Title:[/bold] {job_title}\n"
            f"[bold]Company:[/bold] {job_company}\n"
            f"[bold]Location:[/bold] {job_location or 'Remote/Not specified'}\n"
            f"[bold]Match Score:[/bold] {f'{job_match_score:.1%}' if job_match_score else 'Not scored'}\n"
            f"[bold]Status:[/bold] {job_status}\n"
            f"[bold]URL:[/bold] {job_url}",
            title="[bold green]Selected Job[/bold green]",
            border_style="green"
        ))

    # Ask for confirmation if not using --yes flag (moved outside db context)
    if not args.yes:
        try:
            proceed = console.input("\n[bold yellow]Proceed with application? (y/n): [/bold yellow]")
            if proceed.lower() != 'y':
                console.print("[yellow]Application cancelled[/yellow]")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Application cancelled[/yellow]")
            sys.exit(0)

    manual_review = args.manual_review

    # Parse resume
    console.print("\n[cyan]Parsing resume...[/cyan]")
    resume_db_obj = parse_resume(str(resume_path))
    
    # Convert ResumeData to a format the applier expects
    parsed_data = json.loads(resume_db_obj.structured_data) if resume_db_obj.structured_data else {}
    resume_data = SimpleNamespace(
        contact=parsed_data.get('contact', {}),
        skills=parsed_data.get('skills', []),
        experiences=parsed_data.get('experiences', []),
        education=parsed_data.get('education', {}),
        raw_text=resume_db_obj.raw_text
    )
    console.print("[green]✓[/green] Resume parsed successfully\n")

    # Initialize applier
    console.print("[cyan]Initializing Greenhouse applier...[/cyan]")
    applier = GreenhouseApplier(
        resume_data=resume_data,
        resume_pdf_path=resume_path,
        headless=not manual_review  # Show browser if manual review is enabled
    )
    console.print("[green]✓[/green] Applier initialized\n")

    # Define review callback
    def review_callback(page, form_data, job_obj):
        return show_review_ui(page, form_data, job_obj, resume_data.contact)

    # Apply to job
    console.print(Panel.fit(
        "[bold cyan]Starting Application Process[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    try:
        # Re-fetch the job and make it available for the applier
        with get_db() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            # Load all attributes to avoid lazy loading issues
            _ = (job.id, job.title, job.company, job.url, job.location, 
                 job.description, job.requirements, job.status)
            # Make the object detached but keep loaded attributes
            db.expunge(job)
        
        success, message = applier.apply_to_job(
            job,
            manual_review=manual_review,
            review_callback=review_callback if manual_review else None
        )

        console.print("\n")
        if success:
            console.print(Panel.fit(
                f"[bold green]✓ Application Successful![/bold green]\n\n{message}",
                border_style="green"
            ))
        else:
            console.print(Panel.fit(
                f"[bold red]✗ Application Failed[/bold red]\n\n{message}",
                border_style="red"
            ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Application error")
        console.print(Panel.fit(
            f"[bold red]✗ Error During Application[/bold red]\n\n{str(e)}",
            border_style="red"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()

