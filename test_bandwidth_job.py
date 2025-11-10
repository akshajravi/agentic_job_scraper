#!/usr/bin/env python3
"""
Test the Bandwidth job application with user data from JSON.
"""
import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from agent.apply.greenhouse import GreenhouseApplier
from agent.match.user_data_loader import load_user_data
from agent.storage.models import Job, ATSType, JobStatus

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
logger = logging.getLogger(__name__)

def test_bandwidth():
    """Test application to Bandwidth Software Development Intern position."""
    
    # Create a Job object for this specific posting
    job = Job(
        id=9999,  # Temporary ID
        title="Software Development Intern (Identity) - Summer 2026",
        company="Bandwidth",
        location="Raleigh, NC",
        url="https://job-boards.greenhouse.io/bandwidth/jobs/7380793?utm_source=Simplify&ref=Simplify",
        ats_type=ATSType.GREENHOUSE,
        status=JobStatus.NEW,
        description="Software Development Intern for Identity team",
        requirements=""
    )
    
    console.print("\n[bold cyan]Testing Bandwidth Job Application[/bold cyan]")
    console.print(f"Title: {job.title}")
    console.print(f"Company: {job.company}")
    console.print(f"Location: {job.location}")
    console.print(f"URL: {job.url}\n")
    
    # Load user data
    user_data_path = Path("user_data.json")
    if not user_data_path.exists():
        console.print("[red]Error: user_data.json not found[/red]")
        console.print("[yellow]Please create user_data.json with your personal information[/yellow]")
        return
    
    console.print("[cyan]Loading user data...[/cyan]")
    user_data = load_user_data(user_data_path)
    console.print("[green]✓[/green] User data loaded\n")
    
    # Resume PDF path (optional)
    resume_pdf_path = Path("resume.pdf") if Path("resume.pdf").exists() else None
    
    # Initialize applier
    console.print("[cyan]Initializing applier...[/cyan]")
    applier = GreenhouseApplier(
        user_data=user_data,
        resume_pdf_path=resume_pdf_path,
        headless=False  # Keep browser visible to see what's happening
    )
    console.print("[green]✓[/green] Applier ready\n")
    
    # Apply
    console.print("[bold cyan]Starting application...[/bold cyan]\n")
    success, message = applier.apply_to_job(job, manual_review=False)
    
    console.print()
    if success:
        console.print(f"[bold green]✓ SUCCESS![/bold green]\n{message}")
    else:
        console.print(f"[bold red]✗ FAILED[/bold red]\n{message}")

if __name__ == "__main__":
    test_bandwidth()

