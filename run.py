#!/usr/bin/env python3
"""
Main orchestrator for the agentic job scraper and auto-applier.
"""
import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from agent.apply.greenhouse import GreenhouseApplier
from agent.apply.review_ui import show_review_ui
from agent.config import settings
from agent.ingest.github_repos import GitHubJobScraper
from agent.ingest.normalize import JobNormalizer
from agent.match.embed_matcher import match_jobs_for_resume
from agent.match.resume_parser import parse_resume
from agent.notify.email import send_summary_email
from agent.storage.db import get_db, init_db
from agent.storage.models import Job, JobStatus

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


def scrape_jobs() -> int:
    """Scrape jobs from GitHub repositories.

    Returns:
        Number of new jobs added
    """
    console.print(Panel.fit(
        "[bold cyan]Stage 1: Scraping Jobs from GitHub",
        border_style="cyan"
    ))

    scraper = GitHubJobScraper()
    normalizer = JobNormalizer()

    total_new = 0
    total_skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for repo in settings.github_repos:
            task = progress.add_task(f"Scraping {repo}...", total=None)

            try:
                jobs = scraper.scrape_repo(repo)
                new_count, skipped_count = normalizer.normalize_and_store(jobs)

                total_new += new_count
                total_skipped += skipped_count

                progress.update(
                    task,
                    description=f"[green][/green] {repo}: {len(jobs)} jobs ({new_count} new)",
                    completed=True
                )
            except Exception as e:
                progress.update(
                    task,
                    description=f"[red][/red] {repo}: Failed ({str(e)})",
                    completed=True
                )
                logger.error(f"Failed to scrape {repo}: {e}")

    console.print(f"\n[bold green]Results:[/bold green] {total_new} new jobs, {total_skipped} duplicates skipped\n")
    return total_new


def match_jobs(resume_path: str, threshold: float = None, intern_only: bool = False) -> int:
    """Match jobs against resume using AI embeddings.

    Args:
        resume_path: Path to resume PDF
        threshold: Match score threshold (default from settings)
        intern_only: Only match intern positions

    Returns:
        Number of jobs matched
    """
    console.print(Panel.fit(
        "[bold cyan]Stage 2: Matching Jobs to Resume",
        border_style="cyan"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Parse resume
        task = progress.add_task("Parsing resume PDF...", total=None)
        resume_data = parse_resume(resume_path)
        progress.update(task, description="[green][/green] Resume parsed", completed=True)

        # Generate embeddings and match
        task = progress.add_task("Generating embeddings and matching jobs...", total=None)
        matched_count = match_jobs_for_resume(resume_data, threshold, intern_only)
        progress.update(task, description=f"[green][/green] Matched {matched_count} jobs", completed=True)

    # Display top matches
    with get_db() as db:
        top_matches = db.query(Job).filter(
            Job.status == JobStatus.MATCHED
        ).order_by(Job.match_score.desc()).limit(10).all()

        if top_matches:
            table = Table(title="\nTop Matched Jobs", show_header=True, header_style="bold magenta")
            table.add_column("Score", style="cyan", width=8)
            table.add_column("Company", style="green", width=20)
            table.add_column("Title", style="yellow", width=30)
            table.add_column("Location", style="blue", width=15)

            for job in top_matches:
                score_display = f"{job.match_score:.1%}" if job.match_score else "N/A"
                table.add_row(
                    score_display,
                    job.company[:20],
                    job.title[:30],
                    (job.location or "Remote")[:15]
                )

            console.print(table)
            console.print()

    return matched_count


def apply_to_jobs(resume_path: str, manual_review: bool = False, max_applications: int = None) -> tuple:
    """Apply to matched jobs.

    Args:
        resume_path: Path to resume PDF
        manual_review: If True, show review UI before each submission
        max_applications: Maximum number of applications to send

    Returns:
        Tuple of (applied_count, successful_count, results_list)
    """
    console.print(Panel.fit(
        "[bold cyan]Stage 3: Applying to Jobs",
        border_style="cyan"
    ))

    if max_applications is None:
        max_applications = settings.max_applications_per_day

    # Get resume data
    resume_data = parse_resume(resume_path)

    # Get matched jobs
    with get_db() as db:
        matched_jobs = db.query(Job).filter(
            Job.status == JobStatus.MATCHED,
            Job.ats_type == "GREENHOUSE"  # Only Greenhouse for now
        ).order_by(Job.match_score.desc()).limit(max_applications).all()

    if not matched_jobs:
        console.print("[yellow]No matched Greenhouse jobs to apply to[/yellow]\n")
        return 0, 0, []

    console.print(f"Found {len(matched_jobs)} Greenhouse jobs to apply to (limit: {max_applications})\n")

    # Initialize applier
    applier = GreenhouseApplier(
        resume_data=resume_data,
        resume_pdf_path=resume_path,
        headless=not manual_review  # Show browser in manual review mode
    )

    applied_count = 0
    successful_count = 0
    results = []

    for i, job in enumerate(matched_jobs, 1):
        console.print(f"[bold]Application {i}/{len(matched_jobs)}:[/bold] {job.title} at {job.company}")
        console.print(f"Match score: [cyan]{job.match_score:.1%}[/cyan]")
        if job.match_reason:
            console.print(f"Reason: [italic]{job.match_reason[:100]}...[/italic]")

        # Define review callback
        def review_callback(page, form_data, job_obj):
            return show_review_ui(page, form_data, job_obj, resume_data.contact)

        try:
            success, message = applier.apply_to_job(
                job,
                manual_review=manual_review,
                review_callback=review_callback if manual_review else None
            )

            applied_count += 1
            if success:
                successful_count += 1
                console.print(f"[green] Success:[/green] {message}\n")
            else:
                console.print(f"[red] Failed:[/red] {message}\n")

            results.append((job, None, success, message))

        except Exception as e:
            logger.error(f"Error applying to {job.company}: {e}")
            console.print(f"[red] Error:[/red] {str(e)}\n")
            results.append((job, None, False, str(e)))

    return applied_count, successful_count, results


def send_notification(stats: dict, matched_jobs: list = None, applied_results: list = None):
    """Send email notification with summary.

    Args:
        stats: Statistics dictionary
        matched_jobs: List of matched Job objects
        applied_results: List of application results
    """
    console.print(Panel.fit(
        "[bold cyan]Stage 4: Sending Notification",
        border_style="cyan"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Sending email...", total=None)

        success = send_summary_email(stats, matched_jobs, applied_results)

        if success:
            progress.update(task, description="[green][/green] Email sent successfully", completed=True)
        else:
            progress.update(task, description="[yellow]![/yellow] Email not configured or failed", completed=True)

    console.print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agentic Job Scraper and Auto-Applier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with manual review
  python run.py --resume resume.pdf --manual-review

  # Just scrape and match (dry run)
  python run.py --resume resume.pdf --dry-run

  # Scrape only
  python run.py --scrape-only

  # Apply to max 5 jobs
  python run.py --resume resume.pdf --max-applications 5
        """
    )

    parser.add_argument(
        "--resume",
        type=str,
        help="Path to resume PDF file"
    )

    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Run job scraping stage"
    )

    parser.add_argument(
        "--match",
        action="store_true",
        help="Run job matching stage"
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run job application stage"
    )

    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Only scrape jobs, don't match or apply"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and match only, don't apply"
    )

    parser.add_argument(
        "--manual-review",
        action="store_true",
        help="Show review UI before each application"
    )

    parser.add_argument(
        "--max-applications",
        type=int,
        help="Maximum number of applications to send"
    )

    parser.add_argument(
        "--match-threshold",
        type=float,
        help="Minimum match score threshold (0.0 to 1.0)"
    )

    parser.add_argument(
        "--intern-only",
        action="store_true",
        help="Only match and apply to intern positions"
    )

    args = parser.parse_args()

    # Initialize database
    init_db()

    # Determine which stages to run
    run_scrape = args.scrape or args.scrape_only or (not any([args.scrape, args.match, args.apply]))
    run_match = args.match or (not args.scrape_only and (not any([args.scrape, args.match, args.apply]) or args.dry_run))
    run_apply = args.apply or (not args.scrape_only and not args.dry_run and not any([args.scrape, args.match, args.apply]))

    # Validate resume path if matching or applying
    if (run_match or run_apply) and not args.resume:
        console.print("[red]Error: --resume is required for matching and applying[/red]")
        sys.exit(1)

    if args.resume and not Path(args.resume).exists():
        console.print(f"[red]Error: Resume file not found: {args.resume}[/red]")
        sys.exit(1)

    # Print header
    console.print("\n")
    console.print(Panel.fit(
        "[bold magenta]Agentic Job Scraper & Auto-Applier[/bold magenta]\n"
        f"Scrape: {run_scrape} | Match: {run_match} | Apply: {run_apply}",
        border_style="magenta"
    ))
    console.print("\n")

    # Statistics
    stats = {
        'scraped': 0,
        'matched': 0,
        'applied': 0,
        'successful': 0
    }

    matched_jobs = None
    applied_results = None

    try:
        # Stage 1: Scrape
        if run_scrape:
            stats['scraped'] = scrape_jobs()

        # Stage 2: Match
        if run_match:
            stats['matched'] = match_jobs(args.resume, args.match_threshold, args.intern_only)

            # Get matched jobs for notification
            with get_db() as db:
                matched_jobs = db.query(Job).filter(
                    Job.status == JobStatus.MATCHED
                ).order_by(Job.match_score.desc()).limit(20).all()

        # Stage 3: Apply
        if run_apply:
            applied, successful, results = apply_to_jobs(
                args.resume,
                manual_review=args.manual_review,
                max_applications=args.max_applications
            )
            stats['applied'] = applied
            stats['successful'] = successful
            applied_results = results

        # Stage 4: Notify
        if stats['applied'] > 0 or stats['matched'] > 0:
            send_notification(stats, matched_jobs, applied_results)

        # Final summary
        console.print(Panel.fit(
            f"[bold green]Pipeline Complete![/bold green]\n\n"
            f"Scraped: {stats['scraped']} jobs\n"
            f"Matched: {stats['matched']} jobs\n"
            f"Applied: {stats['applied']} jobs\n"
            f"Successful: {stats['successful']} applications",
            border_style="green"
        ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Pipeline failed: {e}[/red]")
        logger.exception("Pipeline error")
        sys.exit(1)


if __name__ == "__main__":
    main()
